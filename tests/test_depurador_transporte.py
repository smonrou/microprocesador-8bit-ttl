"""TransporteSocket contra un ServidorFalso de verdad.

Socket puro: no hace falta pyserial ni hardware para probar todo el camino
comando -> respuesta -> cola de líneas.
"""

import queue
import threading
import time

import pytest

from depurador import protocolo, transporte
from depurador.servidor_falso import ServidorFalso


@pytest.fixture
def servidor():
    with ServidorFalso(puerto=0, retardo=0) as instancia:
        yield instancia


@pytest.fixture
def canal(servidor):
    with transporte.TransporteSocket("127.0.0.1", servidor.puerto) as abierto:
        yield abierto


def esperar_linea(canal, contiene, limite=5.0):
    """Espera a que llegue una línea que contenga `contiene` y devuelve todo
    lo recibido hasta ella."""
    recibidas = []
    fin = time.time() + limite
    while time.time() < fin:
        try:
            linea = canal.lineas.get(timeout=0.2)
        except queue.Empty:
            continue
        if linea is transporte.CENTINELA_DESCONEXION:
            raise AssertionError(f"se cortó la conexión; recibido: {recibidas}")
        recibidas.append(linea)
        if contiene in linea:
            return recibidas
    raise AssertionError(f"no llegó {contiene!r}; recibido: {recibidas}")


# ── Ciclo de vida ──────────────────────────────────────────────────────────

def test_al_abrir_queda_conectado(canal):
    assert canal.conectado


def test_al_cerrar_deja_de_estar_conectado(servidor):
    canal = transporte.TransporteSocket("127.0.0.1", servidor.puerto).abrir()
    canal.cerrar()
    assert not canal.conectado


def test_abrir_dos_veces_no_levanta_dos_hilos(canal):
    antes = threading.active_count()
    canal.abrir()
    assert threading.active_count() == antes


def test_cerrar_dos_veces_no_revienta(servidor):
    canal = transporte.TransporteSocket("127.0.0.1", servidor.puerto).abrir()
    canal.cerrar()
    canal.cerrar()


def test_enviar_sin_abrir_es_un_error(servidor):
    canal = transporte.TransporteSocket("127.0.0.1", servidor.puerto)
    with pytest.raises(RuntimeError):
        canal.enviar_linea("STATE")


def test_conectarse_a_un_puerto_muerto_falla_al_abrir():
    canal = transporte.TransporteSocket("127.0.0.1", 1, espera=1.0)
    with pytest.raises(OSError):
        canal.abrir()
    assert not canal.conectado


def test_la_descripcion_dice_donde_esta_conectado(servidor):
    canal = transporte.TransporteSocket("127.0.0.1", servidor.puerto)
    assert canal.descripcion() == f"TCP 127.0.0.1:{servidor.puerto}"


# ── Recepción ──────────────────────────────────────────────────────────────

def test_el_banner_llega_a_la_cola(canal):
    recibidas = esperar_linea(canal, "#pc=")
    assert "Microprocesador de 8 bits - unidad de control lista" in recibidas


def test_las_lineas_llegan_sin_crlf(canal):
    for linea in esperar_linea(canal, "#pc="):
        assert not linea.endswith("\r")
        assert "\n" not in linea


def test_un_comando_recibe_su_respuesta(canal):
    esperar_linea(canal, "#pc=")
    canal.enviar_linea("LOAD 0xC8 0x04")
    assert "OK dir=0xC8 val=0x04" in esperar_linea(canal, "OK dir=")


def test_el_bloque_llega_partido_en_lineas_y_se_reensambla(canal):
    esperar_linea(canal, "#pc=")
    canal.enviar_linea("LOADB 0x00 0x30 0x07 0xC0")
    esperar_linea(canal, "OK dir=")
    for _ in range(4):
        canal.enviar_linea("STEP")
    recibidas = esperar_linea(canal, "#ciclo=")

    ensamblador = protocolo.EnsambladorDeBloques()
    mensajes = []
    for linea in recibidas:
        mensajes.extend(ensamblador.agregar(linea))

    bloques = [m for m in mensajes if m.es_bloque]
    assert len(bloques) == 1
    assert bloques[0].texto.startswith("─── Ciclo 1 ───")
    assert bloques[0].texto.endswith("PC → 0x02")
    assert "FETCH   PC=0x00  →  IR=0x30 (LDI A)" in bloques[0].texto


def test_los_acentos_del_bloque_sobreviven_al_transporte(canal):
    esperar_linea(canal, "#pc=")
    canal.enviar_linea("LOADB 0x00 0xC0")
    esperar_linea(canal, "OK dir=")
    for _ in range(3):
        canal.enviar_linea("STEP")
    recibidas = esperar_linea(canal, "#ciclo=")
    assert any("sin operando" in linea for linea in recibidas)
    assert any(linea.startswith("─── Ciclo") for linea in recibidas)


def test_drenar_saca_lo_que_haya_sin_bloquear(canal):
    esperar_linea(canal, "#pc=")
    canal.enviar_linea("STATE")
    time.sleep(0.3)
    recibidas = canal.drenar()
    assert any(linea.startswith("#pc=") for linea in recibidas)
    assert canal.drenar() == []          # ya no queda nada: no se bloquea


def test_drenar_respeta_el_maximo_del_lote(canal):
    esperar_linea(canal, "#pc=")
    canal.enviar_linea("DUMP")
    time.sleep(0.3)
    assert len(canal.drenar(maximo=3)) == 3


def test_un_run_completo_llega_entero(canal):
    from depurador import cargador

    esperar_linea(canal, "#pc=")
    for linea in cargador.leer_lineas("programas/referencia.load"):
        canal.enviar_linea(linea)
        esperar_linea(canal, "OK dir=")

    canal.enviar_linea("VEL 0")
    esperar_linea(canal, "OK vel=")
    canal.enviar_linea("RUN")
    recibidas = esperar_linea(canal, "--- HLT ---", limite=15.0)

    salidas = [l for l in recibidas if " salida=" in l]
    assert len(salidas) == 1 and salidas[0].endswith(" salida=12")


def test_al_cerrar_el_servidor_llega_el_centinela(servidor):
    canal = transporte.TransporteSocket("127.0.0.1", servidor.puerto).abrir()
    try:
        esperar_linea(canal, "#pc=")
        servidor.detener()
        fin = time.time() + 5.0
        while time.time() < fin:
            try:
                if canal.lineas.get(timeout=0.2) is transporte.CENTINELA_DESCONEXION:
                    return
            except queue.Empty:
                continue
        pytest.fail("no llegó el centinela de desconexión")
    finally:
        canal.cerrar()


# ── El camino de hardware real (sin hardware) ──────────────────────────────

def test_listar_puertos_serie_nunca_revienta():
    # Sin pyserial instalado tiene que devolver [] en vez de explotar: el flujo
    # con el servidor falso no necesita pyserial y la GUI debe arrancar igual.
    puertos = transporte.listar_puertos_serie()
    assert isinstance(puertos, list)
    assert all(isinstance(puerto, str) for puerto in puertos)


def test_hay_pyserial_devuelve_un_booleano():
    assert transporte.hay_pyserial() in (True, False)


def test_listar_puertos_devuelve_vacio_si_falta_pyserial(monkeypatch):
    import builtins

    original = builtins.__import__

    def sin_pyserial(nombre, *resto):
        if nombre.startswith("serial"):
            raise ImportError("no hay pyserial")
        return original(nombre, *resto)

    monkeypatch.setattr(builtins, "__import__", sin_pyserial)
    assert transporte.listar_puertos_serie() == []
    assert transporte.hay_pyserial() is False


def test_transporte_serial_avisa_si_falta_pyserial(monkeypatch):
    import builtins

    original = builtins.__import__

    def sin_pyserial(nombre, *resto):
        if nombre.startswith("serial"):
            raise ImportError("no hay pyserial")
        return original(nombre, *resto)

    monkeypatch.setattr(builtins, "__import__", sin_pyserial)
    canal = transporte.TransporteSerial("COM3")
    with pytest.raises(RuntimeError) as error:
        canal.abrir()
    assert "pyserial" in str(error.value)


def test_importar_transporte_no_arrastra_pyserial():
    # El import de pyserial es perezoso: está dentro de _conectar y de
    # listar_puertos_serie, no arriba del archivo.
    import inspect
    fuente = inspect.getsource(transporte)
    cabecera = fuente[:fuente.index("class Transporte")]
    assert "import serial" not in cabecera


def test_transporte_serial_usa_los_baudios_del_firmware():
    canal = transporte.TransporteSerial("COM3")
    assert canal.baudios == 115200          # microprocesador.ino: Serial.begin(115200)
    assert canal.descripcion() == "Serie COM3 @ 115200"
