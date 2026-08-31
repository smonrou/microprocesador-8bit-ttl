"""El servidor falso contra los textos exactos de consola.cpp, comando a comando.

Todo lo que este servidor responde tiene que ser indistinguible de lo que
responderá el Arduino Mega cuando llegue: si aquí se cuela un texto parafraseado,
el depurador funcionará contra la simulación y fallará contra el hardware.
"""

import socket
import time

import pytest

from asm import assemble
from asm.examples import read_source
from depurador import cargador
from depurador.servidor_falso import ConsolaFalsa, ServidorFalso


# ── Ayudas ─────────────────────────────────────────────────────────────────

def consola():
    """Una consola sin retardo: los tests no esperan 200 ms por instrucción."""
    return ConsolaFalsa(retardo=0)


def responder(orden, con=None):
    """Manda una línea y devuelve la respuesta como lista de líneas."""
    caja = con if con is not None else consola()
    return caja.recibir(orden + "\n").replace("\r\n", "\n").rstrip("\n").split("\n")


@pytest.fixture
def servidor():
    with ServidorFalso(puerto=0, retardo=0) as instancia:
        yield instancia


class Cliente:
    """Cliente TCP mínimo: manda líneas y lee hasta ver un texto esperado."""

    def __init__(self, puerto):
        self.socket = socket.create_connection(("127.0.0.1", puerto), timeout=5)
        self.socket.settimeout(5)
        self.pendiente = ""

    def cerrar(self):
        self.socket.close()

    def enviar(self, texto):
        self.socket.sendall((texto + "\n").encode("utf-8"))

    def leer_hasta(self, marca, limite=10.0):
        limite_de_tiempo = time.time() + limite
        while marca not in self.pendiente:
            if time.time() > limite_de_tiempo:
                raise AssertionError(
                    f"no llegó {marca!r}; recibido:\n{self.pendiente}")
            datos = self.socket.recv(4096)
            if not datos:
                raise AssertionError(f"el servidor cerró; recibido:\n{self.pendiente}")
            self.pendiente += datos.decode("utf-8")
        texto, self.pendiente = self.pendiente, ""
        return texto.replace("\r\n", "\n")


# ── Banner de arranque (consola::iniciar) ──────────────────────────────────

def test_el_banner_es_el_de_consola_iniciar():
    lineas = consola().banner().replace("\r\n", "\n").split("\n")
    assert lineas[0] == ""
    assert lineas[1] == "Microprocesador de 8 bits - unidad de control lista"
    assert lineas[2] == "ALU: 2x SN74LS181  Registros: 2x 74LS273  Mux: 2x 74LS157"
    assert lineas[3] == "Escribe HELP para ver los comandos."
    assert lineas[4] == "PC=0x00  IR=0x00  A=0x00  B=0x00  Z=0  C=0  listo"
    assert lineas[5] == "#pc=0x00 ir=0x00 a=0x00 b=0x00 z=0 c=0 halted=0"


# ── LOAD ───────────────────────────────────────────────────────────────────

def test_load_responde_ok_con_direccion_y_valor():
    assert responder("LOAD 0xC8 0x04") == ["OK dir=0xC8 val=0x04"]


def test_load_escribe_de_verdad_en_la_memoria():
    caja = consola()
    responder("LOAD 0x10 0x5A", caja)
    assert caja.cpu.memory.read(0x10) == 0x5A


def test_load_acepta_decimal_igual_que_strtol():
    caja = consola()
    assert responder("LOAD 200 4", caja) == ["OK dir=0xC8 val=0x04"]
    assert caja.cpu.memory.read(200) == 4


def test_load_sin_argumentos_pide_los_argumentos():
    assert responder("LOAD") == ["ERR LOAD requiere <dir> <byte>"]


def test_load_con_un_solo_argumento_pide_los_argumentos():
    assert responder("LOAD 0x10") == ["ERR LOAD requiere <dir> <byte>"]


def test_load_con_basura_pide_los_argumentos():
    assert responder("LOAD hola 4") == ["ERR LOAD requiere <dir> <byte>"]
    assert responder("LOAD 0x10 chau") == ["ERR LOAD requiere <dir> <byte>"]


def test_load_fuera_de_rango_no_enmascara_en_silencio():
    # Memory.write hace `& 0xFF` sin avisar: si el servidor se apoyara en eso,
    # LOAD 0x10 256 escribiría un 0 y diría OK. El firmware da error.
    caja = consola()
    assert responder("LOAD 0x10 256", caja) == ["ERR valor fuera de rango (0-255)"]
    assert responder("LOAD 300 4", caja) == ["ERR valor fuera de rango (0-255)"]
    assert responder("LOAD 0x10 -1", caja) == ["ERR valor fuera de rango (0-255)"]
    assert caja.cpu.memory.read(0x10) == 0


def test_load_en_minusculas_funciona():
    assert responder("load 0xC8 0x04") == ["OK dir=0xC8 val=0x04"]


# ── LOADB ──────────────────────────────────────────────────────────────────

def test_loadb_responde_ok_con_direccion_y_cuenta():
    assert responder("LOADB 0x00 0x30 0x00 0x50") == ["OK dir=0x00 n=3"]


def test_loadb_escribe_el_bloque_consecutivo():
    caja = consola()
    responder("LOADB 0x10 0x11 0x22 0x33", caja)
    assert [caja.cpu.memory.read(d) for d in (0x10, 0x11, 0x12)] == [0x11, 0x22, 0x33]


def test_loadb_sin_direccion_pide_los_argumentos():
    assert responder("LOADB") == ["ERR LOADB requiere <dir> <hex> [hex...]"]
    assert responder("LOADB xx 0x01") == ["ERR LOADB requiere <dir> <hex> [hex...]"]
    assert responder("LOADB 300 0x01") == ["ERR LOADB requiere <dir> <hex> [hex...]"]


def test_loadb_sin_bytes_lo_dice():
    assert responder("LOADB 0x10") == ["ERR LOADB sin bytes"]


def test_loadb_con_un_byte_invalido_lo_repite_tal_cual():
    assert responder("LOADB 0x00 0x30 zz") == ["ERR byte invalido: zz"]
    assert responder("LOADB 0x00 0x30 256") == ["ERR byte invalido: 256"]


def test_loadb_escribe_lo_que_alcanzo_a_escribir_antes_del_error():
    # El firmware escribe byte a byte y aborta al llegar al inválido: lo ya
    # escrito se queda. Se replica.
    caja = consola()
    responder("LOADB 0x00 0x11 0x22 zz 0x44", caja)
    assert [caja.cpu.memory.read(d) for d in (0x00, 0x01, 0x02)] == [0x11, 0x22, 0x00]


def test_loadb_que_se_pasa_del_final_de_la_memoria():
    assert responder("LOADB 0xFF 0x01 0x02") == ["ERR el bloque excede la memoria"]


def test_loadb_hasta_el_ultimo_byte_de_la_memoria_es_valido():
    assert responder("LOADB 0xFF 0x01") == ["OK dir=0xFF n=1"]


# ── RESET / BORRAR ─────────────────────────────────────────────────────────

def test_reset_responde_ok_y_el_estado():
    lineas = responder("RESET")
    assert lineas[0] == "OK reset"
    assert lineas[1] == "PC=0x00  IR=0x00  A=0x00  B=0x00  Z=0  C=0  listo"
    assert lineas[2] == "#pc=0x00 ir=0x00 a=0x00 b=0x00 z=0 c=0 halted=0"


def test_reset_conserva_la_memoria():
    # RESET reinicia la ejecución, no borra el programa (nucleo.h::reiniciar).
    caja = consola()
    responder("LOAD 0xC8 0x04", caja)
    responder("RESET", caja)
    assert caja.cpu.memory.read(0xC8) == 0x04


def test_reset_pone_el_pc_las_banderas_y_los_registros_a_cero():
    caja = consola()
    responder("LOADB 0x00 0x30 0x07 0xC0", caja)   # LDI A,#7 ; HLT
    responder("VEL 0", caja)
    responder("RUN", caja)
    assert caja.cpu.a == 7 and caja.cpu.halted
    responder("RESET", caja)
    assert (caja.cpu.pc, caja.cpu.a, caja.cpu.b, caja.cpu.z, caja.cpu.c) == (0,) * 5
    assert not caja.cpu.halted


def test_borrar_responde_ok_y_nada_mas():
    assert responder("BORRAR") == ["OK memoria borrada"]


def test_borrar_deja_la_memoria_en_ceros_y_reinicia():
    caja = consola()
    responder("LOAD 0xC8 0x04", caja)
    responder("BORRAR", caja)
    assert caja.cpu.memory.read(0xC8) == 0
    assert all(byte == 0 for byte in caja.cpu.memory.cells)
    assert caja.cpu.pc == 0 and not caja.cpu.halted


# ── STATE ──────────────────────────────────────────────────────────────────

def test_state_da_las_dos_lineas():
    assert responder("STATE") == [
        "PC=0x00  IR=0x00  A=0x00  B=0x00  Z=0  C=0  listo",
        "#pc=0x00 ir=0x00 a=0x00 b=0x00 z=0 c=0 halted=0",
    ]


def test_state_dice_detenido_tras_un_hlt():
    caja = consola()
    responder("LOADB 0x00 0xC0", caja)     # HLT
    responder("VEL 0", caja)
    responder("RUN", caja)
    lineas = responder("STATE", caja)
    assert lineas[0].endswith("DETENIDO")
    assert "halted=1" in lineas[1]


def test_state_muestra_los_registros_reales():
    caja = consola()
    responder("LOADB 0x00 0x30 0x04 0x40 0x03 0xC0", caja)   # LDI A,#4; LDI B,#3; HLT
    responder("VEL 0", caja)
    responder("RUN", caja)
    lineas = responder("STATE", caja)
    assert "A=0x04" in lineas[0] and "B=0x03" in lineas[0]
    assert "a=0x04 b=0x03" in lineas[1]


# ── STEP ───────────────────────────────────────────────────────────────────

def test_step_avanza_un_microciclo_y_lo_nombra():
    caja = consola()
    responder("LOADB 0x00 0x30 0x07 0xC0", caja)     # LDI A,#7 ; HLT
    assert responder("STEP", caja) == ["paso: FETCH", "#paso=FETCH"]
    assert responder("STEP", caja) == ["paso: DECODE", "#paso=DECODE"]
    assert responder("STEP", caja) == ["paso: FETCH2", "#paso=FETCH2"]


def test_step_imprime_el_bloque_al_completar_la_instruccion():
    caja = consola()
    responder("LOADB 0x00 0x30 0x07 0xC0", caja)
    for _ in range(3):
        responder("STEP", caja)
    lineas = responder("STEP", caja)                  # el EXECUTE que la cierra

    assert lineas[0] == "paso: EXECUTE"
    assert lineas[1] == "─── Ciclo 1 ───"
    assert lineas[2] == "FETCH   PC=0x00  →  IR=0x30 (LDI A)"
    assert lineas[-2] == "PC → 0x02"
    assert lineas[-1] == ("#ciclo=1 pc=0x02 ir=0x30 op=LDI A a=0x07 b=0x00 "
                          "z=0 c=0 halted=0")


def test_step_recorre_los_cinco_microciclos_de_una_operacion_de_alu():
    caja = consola()
    # LDI A,#4 ; LDI B,#3 ; ADD ; HLT
    responder("LOADB 0x00 0x30 0x04 0x40 0x03 0x60 0xC0", caja)
    for _ in range(8):                                # las dos cargas: 4 pasos c/u
        responder("STEP", caja)

    pasos = [responder("STEP", caja)[0] for _ in range(5)]
    assert pasos == ["paso: FETCH", "paso: DECODE", "paso: EXECUTE",
                     "paso: WAIT", "paso: WRITE"]


def test_step_con_la_cpu_detenida_manda_a_resetear():
    caja = consola()
    responder("LOADB 0x00 0xC0", caja)
    responder("VEL 0", caja)
    responder("RUN", caja)
    # CPU.step() LANZA si ya está detenida: el servidor tiene que comprobarlo
    # antes, igual que comandoStep comprueba detenido().
    assert responder("STEP", caja) == ["ERR la CPU esta detenida; usa RESET"]


def test_step_avisa_si_la_cpu_no_pudo_avanzar():
    # Espeja `if (!paso.valido)` de comandoStep. Es inalcanzable por el camino
    # normal (arriba ya se comprobó halted), pero el texto existe en el
    # firmware y aquí no se inventa otro.
    from sim.exceptions import CpuHaltedError

    caja = consola()

    def negarse():
        raise CpuHaltedError(0)

    caja.cpu.step = negarse
    assert responder("STEP", caja) == ["ERR no se pudo avanzar"]


def test_run_corta_limpio_si_la_cpu_no_pudo_avanzar():
    # Espeja `if (!paso.valido) break;` de comandoRun: sale del bucle y cierra
    # con --- HLT --- y el estado.
    from sim.exceptions import CpuHaltedError

    caja = consola()

    def negarse():
        raise CpuHaltedError(0)

    caja.cpu.step = negarse
    lineas = responder("RUN", caja)
    assert lineas[0] == "--- RUN ---"
    assert lineas[1] == "--- HLT ---"


def test_tras_resetear_se_puede_volver_a_hacer_step():
    caja = consola()
    responder("LOADB 0x00 0xC0", caja)
    responder("VEL 0", caja)
    responder("RUN", caja)
    responder("RESET", caja)
    assert responder("STEP", caja)[0] == "paso: FETCH"


# ── RUN ────────────────────────────────────────────────────────────────────

def test_run_abre_y_cierra_con_sus_marcas():
    caja = consola()
    responder("LOADB 0x00 0xC0", caja)                # HLT
    responder("VEL 0", caja)
    lineas = responder("RUN", caja)
    assert lineas[0] == "--- RUN ---"
    assert "--- HLT ---" in lineas
    assert lineas[-1].startswith("#pc=")


def test_run_con_la_cpu_detenida_manda_a_resetear():
    caja = consola()
    responder("LOADB 0x00 0xC0", caja)
    responder("VEL 0", caja)
    responder("RUN", caja)
    assert responder("RUN", caja) == ["ERR la CPU esta detenida; usa RESET"]


def test_run_ejecuta_el_programa_de_referencia_y_saca_12():
    caja = consola()
    responder("VEL 0", caja)
    for linea in cargador.leer_lineas("programas/referencia.load"):
        assert responder(linea, caja) == [f"OK dir=0x{int(linea.split()[1], 0):02X} "
                                          f"n={len(linea.split()) - 2}"]
    lineas = responder("RUN", caja)

    salidas = [l for l in lineas if " salida=" in l]
    assert len(salidas) == 1
    assert salidas[0].endswith(" salida=12")
    assert caja.cpu.output == [12]


def test_run_emite_un_bloque_y_una_linea_clave_por_instruccion():
    caja = consola()
    responder("VEL 0", caja)
    for linea in cargador.leer_lineas("programas/referencia.load"):
        responder(linea, caja)
    lineas = responder("RUN", caja)

    bloques = [l for l in lineas if l.startswith("─── Ciclo")]
    claves = [l for l in lineas if l.startswith("#ciclo=")]
    assert len(bloques) == len(claves) == caja.cpu.instruction_count


def test_run_detecta_un_bucle_infinito():
    caja = consola()
    responder("LOADB 0x00 0xD0 0x00", caja)           # JMP 0x00
    responder("VEL 0", caja)
    lineas = responder("RUN", caja)
    assert lineas[-1] == "ERR limite de instrucciones; posible bucle infinito"
    assert "--- HLT ---" not in lineas


def test_run_respeta_el_retardo_de_vel():
    dormidas = []
    caja = ConsolaFalsa(retardo=0, dormir=dormidas.append)
    responder("LOADB 0x00 0x30 0x01 0xC0", caja)      # LDI A,#1 ; HLT
    responder("VEL 250", caja)
    responder("RUN", caja)
    assert dormidas == [0.25, 0.25]                    # una por instrucción


def test_run_no_duerme_con_vel_cero():
    dormidas = []
    caja = ConsolaFalsa(retardo=200, dormir=dormidas.append)
    responder("LOADB 0x00 0xC0", caja)
    responder("VEL 0", caja)
    responder("RUN", caja)
    assert dormidas == []


# ── DUMP ───────────────────────────────────────────────────────────────────

def test_dump_sin_argumentos_vuelca_los_256_bytes():
    lineas = responder("DUMP")
    assert len(lineas) == 16
    assert lineas[0].startswith("0x00: ")
    assert lineas[-1].startswith("0xF0: ")


def test_una_fila_de_dump_trae_16_bytes_y_espacio_final():
    caja = consola()
    responder("LOADB 0x00 0x11 0x22", caja)
    fila = responder("DUMP 0x00 0x0F", caja)[0]
    # Arduino imprime un espacio DETRÁS de cada byte: la fila acaba en espacio.
    assert fila == "0x00: 11 22 00 00 00 00 00 00 00 00 00 00 00 00 00 00 "


def test_dump_con_un_rango_corto():
    caja = consola()
    responder("LOADB 0xC8 0x0C", caja)
    assert responder("DUMP 0xC8 0xC9", caja) == ["0xC8: 0C 00 "]


def test_dump_solo_con_inicio_llega_hasta_el_final():
    lineas = responder("DUMP 0xF0")
    assert lineas == ["0xF0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 "]


def test_dump_con_argumentos_invalidos():
    assert responder("DUMP zz") == ["ERR DUMP requiere <ini> [fin]"]
    assert responder("DUMP 0x00 zz") == ["ERR DUMP requiere <ini> [fin]"]
    assert responder("DUMP 300") == ["ERR DUMP requiere <ini> [fin]"]


def test_dump_al_reves_lo_dice():
    assert responder("DUMP 0x20 0x10") == ["ERR el final va antes del inicio"]


# ── VEL ────────────────────────────────────────────────────────────────────

def test_vel_confirma_el_valor():
    assert responder("VEL 300") == ["OK vel=300"]
    assert responder("VEL 0") == ["OK vel=0"]
    assert responder("VEL 5000") == ["OK vel=5000"]


def test_vel_fuera_de_rango():
    assert responder("VEL 5001") == ["ERR VEL requiere <ms> entre 0 y 5000"]
    assert responder("VEL -1") == ["ERR VEL requiere <ms> entre 0 y 5000"]
    assert responder("VEL") == ["ERR VEL requiere <ms> entre 0 y 5000"]
    assert responder("VEL rapido") == ["ERR VEL requiere <ms> entre 0 y 5000"]


def test_vel_cambia_el_retardo_de_verdad():
    caja = consola()
    responder("VEL 1234", caja)
    assert caja.retardo == 1234


# ── HELP y comando desconocido ─────────────────────────────────────────────

def test_help_lista_los_nueve_comandos():
    lineas = responder("HELP")
    assert lineas == [
        "LOAD <dir> <byte>     escribe un byte",
        "LOADB <dir> <hex...>  carga un bloque",
        "RUN                   ejecuta hasta HLT",
        "STEP                  avanza un microciclo",
        "RESET                 PC=0, banderas a 0 (conserva memoria)",
        "BORRAR                borra toda la memoria",
        "DUMP <ini> [fin]      vuelca memoria",
        "STATE                 estado actual",
        "VEL <ms>              retardo entre instrucciones en RUN",
    ]


def test_un_comando_desconocido_se_repite_en_mayusculas():
    assert responder("hola") == ["ERR comando desconocido: HOLA"]
    assert responder("PARAR ya") == ["ERR comando desconocido: PARAR"]


# ── El buffer de línea (consola::atender) ──────────────────────────────────

def test_una_linea_vacia_no_produce_nada():
    caja = consola()
    assert caja.recibir("\n") == ""
    assert caja.recibir("   \n") == ""


def test_el_retorno_de_carro_se_ignora():
    assert responder("STATE\r"[:-1]) == responder("STATE")
    caja = consola()
    assert "OK reset" in caja.recibir("RESET\r\n")


def test_varios_comandos_en_un_solo_envio():
    caja = consola()
    respuesta = caja.recibir("LOAD 0x00 0x11\nLOAD 0x01 0x22\n")
    assert respuesta.count("OK dir=") == 2


def test_un_comando_partido_en_dos_envios():
    caja = consola()
    assert caja.recibir("LOAD 0x00 ") == ""      # todavía no hay '\n'
    assert caja.recibir("0x11\n") == "OK dir=0x00 val=0x11\r\n"


def test_una_linea_demasiado_larga_se_descarta():
    caja = consola()
    respuesta = caja.recibir("LOAD " + "0" * 200 + "\n")
    assert "ERR linea demasiado larga" in respuesta


# ── El servidor TCP ────────────────────────────────────────────────────────

def test_el_servidor_toma_un_puerto_efimero(servidor):
    assert servidor.puerto > 0


def test_el_servidor_manda_el_banner_al_conectar(servidor):
    cliente = Cliente(servidor.puerto)
    try:
        banner = cliente.leer_hasta("#pc=")
        assert "Microprocesador de 8 bits - unidad de control lista" in banner
        assert "#pc=0x00 ir=0x00 a=0x00 b=0x00 z=0 c=0 halted=0" in banner
    finally:
        cliente.cerrar()


def test_el_servidor_responde_comandos_por_el_socket(servidor):
    cliente = Cliente(servidor.puerto)
    try:
        cliente.leer_hasta("#pc=")
        cliente.enviar("LOAD 0xC8 0x04")
        assert "OK dir=0xC8 val=0x04" in cliente.leer_hasta("OK dir=")
        cliente.enviar("HELP")
        assert "RUN                   ejecuta hasta HLT" in cliente.leer_hasta("VEL <ms>")
    finally:
        cliente.cerrar()


def test_el_servidor_usa_crlf_como_el_println_de_arduino(servidor):
    cliente = Cliente(servidor.puerto)
    try:
        while "#pc=" not in cliente.pendiente:
            cliente.pendiente += cliente.socket.recv(4096).decode("utf-8")
        assert "\r\n" in cliente.pendiente
    finally:
        cliente.cerrar()


def test_el_servidor_manda_el_bloque_en_un_solo_println(servidor):
    # El bloque de A.9 va con '\n' internos y UN solo '\r\n' al final: quien lee
    # por líneas tiene que reensamblarlo.
    cliente = Cliente(servidor.puerto)
    try:
        cliente.leer_hasta("#pc=")
        cliente.enviar("LOADB 0x00 0xC0")
        cliente.leer_hasta("OK dir=")
        cliente.enviar("STEP")
        cliente.enviar("STEP")
        cliente.enviar("STEP")
        while "#ciclo=" not in cliente.pendiente:
            cliente.pendiente += cliente.socket.recv(4096).decode("utf-8")
        texto = cliente.pendiente                     # crudo, sin normalizar
        bloque = texto[texto.index("─── Ciclo"):texto.index("#ciclo=")]
        assert bloque.count("\r\n") == 1
        assert bloque.count("\n") > 1
    finally:
        cliente.cerrar()


def test_cada_conexion_arranca_con_la_placa_limpia(servidor):
    primero = Cliente(servidor.puerto)
    try:
        primero.leer_hasta("#pc=")
        primero.enviar("LOAD 0xC8 0x04")
        primero.leer_hasta("OK dir=")
    finally:
        primero.cerrar()

    segundo = Cliente(servidor.puerto)
    try:
        segundo.leer_hasta("#pc=")
        segundo.enviar("DUMP 0xC8 0xC8")
        assert "0xC8: 00 " in segundo.leer_hasta("0xC8:")
    finally:
        segundo.cerrar()


def test_el_servidor_se_puede_detener_dos_veces(servidor):
    servidor.detener()
    servidor.detener()
