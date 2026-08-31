"""De punta a punta: socket crudo -> ServidorFalso -> programa de referencia -> 12.

Este es el hito que demuestra que toda la pila sin GUI funciona junta. Se usa
un cliente de socket pelado (ni pyserial ni `transporte`) a propósito: si algo
falla, falla el protocolo, no una abstracción del depurador.

El programa canónico de A.7 multiplica 4x3 por sumas repetidas y su OUT vale
12. Es el mismo criterio de aceptación que usan sim/, asm/ y el firmware.
"""

import socket
import time

import pytest

from depurador import cargador, protocolo
from depurador.servidor_falso import ServidorFalso

LIMITE = 20.0


@pytest.fixture
def servidor():
    with ServidorFalso(puerto=0, retardo=0) as instancia:
        yield instancia


class ClienteCrudo:
    """Socket pelado con reensamblado de bloques. Nada del depurador salvo
    `protocolo`, que es justo lo que se quiere ejercitar."""

    def __init__(self, puerto):
        self.socket = socket.create_connection(("127.0.0.1", puerto), timeout=5)
        self.socket.settimeout(1.0)
        self.pendiente = b""
        self.ensamblador = protocolo.EnsambladorDeBloques()
        self.mensajes = []

    def cerrar(self):
        self.socket.close()

    def enviar(self, texto):
        self.socket.sendall((texto + "\n").encode("utf-8"))

    def _bombear(self):
        try:
            datos = self.socket.recv(4096)
        except socket.timeout:
            return False
        if not datos:
            raise AssertionError("el servidor cerró la conexión")
        self.pendiente += datos
        while b"\n" in self.pendiente:
            cruda, _, self.pendiente = self.pendiente.partition(b"\n")
            linea = cruda.decode("utf-8").rstrip("\r")
            self.mensajes.extend(self.ensamblador.agregar(linea))
        return True

    def esperar(self, predicado, limite=LIMITE):
        """Bombea hasta que `predicado(mensajes)` sea cierto."""
        fin = time.time() + limite
        while time.time() < fin:
            if predicado(self.mensajes):
                return self.mensajes
            self._bombear()
        raise AssertionError(
            "se agotó el tiempo; recibido:\n"
            + "\n".join(m.texto for m in self.mensajes))

    def esperar_respuesta_final(self):
        """Espera un OK/ERR — la confirmación por línea que evita perder
        comandos por el buffer de 64 bytes del Arduino (consola.h)."""
        marca = len(self.mensajes)
        self.esperar(lambda mensajes: any(
            protocolo.es_respuesta_final(m.texto)
            for m in mensajes[marca:] if not m.es_bloque))
        for mensaje in self.mensajes[marca:]:
            if protocolo.es_respuesta_final(mensaje.texto):
                return mensaje.texto
        raise AssertionError("no hubo respuesta final")

    @property
    def lineas(self):
        return [m.texto for m in self.mensajes if not m.es_bloque]

    @property
    def bloques(self):
        return [m.texto for m in self.mensajes if m.es_bloque]


@pytest.fixture
def cliente(servidor):
    conexion = ClienteCrudo(servidor.puerto)
    try:
        conexion.esperar(lambda mensajes: any(
            m.texto.startswith("#pc=") for m in mensajes))
        yield conexion
    finally:
        conexion.cerrar()


def cargar_referencia(cliente):
    """Manda el .load línea por línea esperando el OK de cada una."""
    for linea in cargador.leer_lineas("programas/referencia.load"):
        cliente.enviar(linea)
        respuesta = cliente.esperar_respuesta_final()
        assert respuesta.startswith("OK "), f"{linea} -> {respuesta}"


def valores_de_salida(cliente):
    salidas = []
    for linea in cliente.lineas:
        datos = protocolo.parsear_linea_clave_valor(linea)
        if datos and "salida" in datos:
            salidas.append(datos["salida"])
    return salidas


# ── El hito ────────────────────────────────────────────────────────────────

def test_el_programa_de_referencia_saca_12_de_punta_a_punta(cliente):
    cargar_referencia(cliente)

    cliente.enviar("RUN")
    cliente.esperar(lambda mensajes: any(
        m.texto == "--- HLT ---" for m in mensajes))

    assert valores_de_salida(cliente) == [12]


def test_el_banner_llega_antes_que_nada(cliente):
    assert cliente.lineas[1] == "Microprocesador de 8 bits - unidad de control lista"
    assert cliente.lineas[-1] == "#pc=0x00 ir=0x00 a=0x00 b=0x00 z=0 c=0 halted=0"


def test_cada_linea_del_load_se_confirma_una_a_una(cliente):
    lineas = cargador.leer_lineas("programas/referencia.load")
    confirmaciones = []
    for linea in lineas:
        cliente.enviar(linea)
        confirmaciones.append(cliente.esperar_respuesta_final())

    assert len(confirmaciones) == len(lineas)
    assert all(c.startswith("OK dir=") for c in confirmaciones)


def test_el_run_emite_un_bloque_legible_por_instruccion(cliente):
    cargar_referencia(cliente)
    cliente.enviar("RUN")
    cliente.esperar(lambda mensajes: any(m.texto == "--- HLT ---" for m in mensajes))

    claves = [l for l in cliente.lineas if l.startswith("#ciclo=")]
    assert len(cliente.bloques) == len(claves)
    assert all(b.startswith("─── Ciclo ") for b in cliente.bloques)
    assert all(b.endswith("PC → 0x") or "PC → 0x" in b for b in cliente.bloques)


def test_el_ultimo_bloque_del_run_es_el_hlt(cliente):
    cargar_referencia(cliente)
    cliente.enviar("RUN")
    # Esperar la línea de estado final (tras "--- HLT ---"), no solo el
    # marcador: en una sola pasada de recv() pueden llegar por separado y
    # el marcador por sí solo no garantiza que la línea #pc= ya esté aquí.
    cliente.esperar(lambda mensajes: any(
        m.texto.startswith("#pc=") and "halted=1" in m.texto for m in mensajes))

    assert "EXECUTE HLT" in cliente.bloques[-1]
    assert cliente.lineas[-1].startswith("#pc=")
    assert "halted=1" in cliente.lineas[-1]


def test_el_bloque_de_la_suma_muestra_las_lineas_de_control_de_la_alu(cliente):
    cargar_referencia(cliente)
    cliente.enviar("RUN")
    cliente.esperar(lambda mensajes: any(m.texto == "--- HLT ---" for m in mensajes))

    controles = [protocolo.extraer_control_alu(b) for b in cliente.bloques]
    controles = [c for c in controles if c is not None]

    # El programa hace tres ADD y tres SUB. ADD: M=0 S=1001 Cn=1.
    # SUB: M=0 S=0110 Cn=0 — mismo selector que XOR, lo distingue el M.
    assert {"M": 0, "S": "1001", "Cn": 1} in controles
    assert {"M": 0, "S": "0110", "Cn": 0} in controles
    assert len(controles) == 6


def test_paso_a_paso_hasta_el_final_tambien_llega_a_12(cliente):
    """El mismo programa en modo microciclo: es el modo de demostración."""
    cargar_referencia(cliente)

    for _ in range(400):
        cliente.enviar("STEP")
        cliente.esperar(lambda mensajes, n=len(cliente.mensajes):
                        len(mensajes) > n)
        if any("halted=1" in l for l in cliente.lineas):
            break
    else:
        pytest.fail("el programa no terminó en 400 microciclos")

    assert valores_de_salida(cliente) == [12]
    pasos = [l[len("paso: "):] for l in cliente.lineas if l.startswith("paso: ")]
    assert set(pasos) <= set(protocolo.NOMBRES_DE_PASO)
    assert "WAIT" in pasos and "WRITE" in pasos and "FETCH2" in pasos


def test_la_memoria_queda_con_el_resultado(cliente):
    cargar_referencia(cliente)
    cliente.enviar("RUN")
    cliente.esperar(lambda mensajes: any(m.texto == "--- HLT ---" for m in mensajes))

    cliente.enviar("DUMP 0xC8 0xC9")
    cliente.esperar(lambda mensajes: any(
        m.texto.startswith("0xC8:") for m in mensajes))

    fila = [l for l in cliente.lineas if l.startswith("0xC8:")][-1]
    assert fila == "0xC8: 0C 00 "        # resultado=12, contador=0


def test_tras_el_hlt_run_pide_reset_y_reset_deja_repetir(cliente):
    cargar_referencia(cliente)
    cliente.enviar("RUN")
    cliente.esperar(lambda mensajes: any(m.texto == "--- HLT ---" for m in mensajes))

    cliente.enviar("RUN")
    assert cliente.esperar_respuesta_final() == "ERR la CPU esta detenida; usa RESET"

    cliente.enviar("RESET")
    assert cliente.esperar_respuesta_final() == "OK reset"

    # RESET conserva la memoria: el programa vuelve a correr sin recargarlo.
    marca = len(cliente.mensajes)
    cliente.enviar("RUN")
    cliente.esperar(lambda mensajes: any(
        m.texto == "--- HLT ---" for m in mensajes[marca:]))
    assert valores_de_salida(cliente) == [12, 12]


def test_borrar_deja_la_placa_en_blanco(cliente):
    cargar_referencia(cliente)
    cliente.enviar("BORRAR")
    assert cliente.esperar_respuesta_final() == "OK memoria borrada"

    cliente.enviar("DUMP 0x00 0x0F")
    cliente.esperar(lambda mensajes: any(
        m.texto.startswith("0x00:") for m in mensajes))
    fila = [l for l in cliente.lineas if l.startswith("0x00:")][-1]
    assert fila == "0x00: " + "00 " * 16
