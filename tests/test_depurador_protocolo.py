"""El protocolo del depurador contra los textos exactos de formato.cpp/consola.cpp.

Estas líneas son lo más fácil de equivocar (un espacio, una mayúscula, el
ancho del hexadecimal, confundir el valor de antes con el de después), así que
se fijan aquí antes de escribir nada que las use.
"""

import pytest

from asm import assemble
from asm.examples import read_source
from depurador import protocolo
from sim.cpu import CPU
from sim.memory import Memory


def cpu_con(fuente):
    memoria = Memory()
    memoria.load_bytes(assemble(fuente).binary)
    return CPU(memoria)


def trazas_de(fuente):
    cpu = cpu_con(fuente)
    trazas = []
    while not cpu.halted:
        resultado = cpu.step()
        if resultado.completed:
            trazas.append((resultado.trace, cpu.halted))
    return trazas


# ── linea_clave_valor ──────────────────────────────────────────────────────

def test_la_linea_clave_valor_tiene_el_formato_de_formato_cpp():
    trazas = trazas_de("LDI A,#0x05\nHLT\n")
    linea = protocolo.linea_clave_valor(*trazas[0])
    assert linea == "#ciclo=1 pc=0x02 ir=0x30 op=LDI A a=0x05 b=0x00 z=0 c=0 halted=0"


def test_la_linea_clave_valor_es_ascii_puro():
    for traza, detenido in trazas_de(read_source("programas/referencia.asm")):
        protocolo.linea_clave_valor(traza, detenido).encode("ascii")


def test_la_linea_clave_valor_usa_hexadecimal_de_dos_digitos_en_mayuscula():
    trazas = trazas_de("LDI A,#0xAB\nHLT\n")
    linea = protocolo.linea_clave_valor(*trazas[0])
    assert "a=0xAB" in linea
    assert "a=0xab" not in linea


def test_la_linea_clave_valor_reporta_pc_a_y_b_de_despues():
    # pc/a/b son los valores POSTERIORES a la instrucción (pcDespues,
    # aDespues, bDespues en formato.cpp), no los de antes.
    trazas = trazas_de("LDI A,#0x02\nLDI B,#0x03\nADD\nHLT\n")
    suma = protocolo.linea_clave_valor(*trazas[2])
    assert "a=0x05" in suma          # 2+3, no el 0x02 de antes
    assert "b=0x03" in suma


def test_la_linea_clave_valor_agrega_salida_solo_en_out():
    trazas = trazas_de("LDI A,#0x0C\nOUT\nHLT\n")
    assert "salida=" not in protocolo.linea_clave_valor(*trazas[0])
    assert protocolo.linea_clave_valor(*trazas[1]).endswith(" salida=12")


def test_la_linea_clave_valor_marca_halted_al_final():
    trazas = trazas_de(read_source("programas/referencia.asm"))
    lineas = [protocolo.linea_clave_valor(t, d) for t, d in trazas]
    assert "halted=1" in lineas[-1]
    assert all("halted=0" in linea for linea in lineas[:-1])


def test_la_linea_clave_valor_lleva_todas_las_claves():
    trazas = trazas_de("NOP\nHLT\n")
    linea = protocolo.linea_clave_valor(*trazas[0])
    assert linea.startswith("#")
    for clave in ("ciclo", "pc", "ir", "op", "a", "b", "z", "c", "halted"):
        assert f"{clave}=" in linea


# ── linea_estado ───────────────────────────────────────────────────────────

def test_linea_estado_tiene_el_formato_de_lineaestado():
    assert (protocolo.linea_estado(0, 0, 0, 0, 0, 0, False)
            == "#pc=0x00 ir=0x00 a=0x00 b=0x00 z=0 c=0 halted=0")


def test_linea_estado_no_lleva_ciclo_ni_op():
    linea = protocolo.linea_estado(0x1A, 0xC0, 0x0C, 0x03, 1, 0, True)
    assert linea == "#pc=0x1A ir=0xC0 a=0x0C b=0x03 z=1 c=0 halted=1"
    assert "ciclo=" not in linea
    assert "op=" not in linea


def test_linea_estado_humana_usa_dos_espacios_entre_campos():
    assert (protocolo.linea_estado_humana(0x00, 0x00, 0x00, 0x00, 0, 0, False)
            == "PC=0x00  IR=0x00  A=0x00  B=0x00  Z=0  C=0  listo")


def test_linea_estado_humana_dice_detenido_en_mayusculas():
    linea = protocolo.linea_estado_humana(0x1A, 0xC0, 0x0C, 0x03, 1, 0, True)
    assert linea == "PC=0x1A  IR=0xC0  A=0x0C  B=0x03  Z=1  C=0  DETENIDO"


# ── parsear_numero (strtol con base 0) ─────────────────────────────────────

@pytest.mark.parametrize("texto,esperado", [
    ("0", 0),
    ("12", 12),
    ("255", 255),
    ("0x00", 0),
    ("0xFF", 255),
    ("0xff", 255),
    ("0Xc8", 0xC8),
    ("-1", -1),
    ("+7", 7),
    ("300", 300),          # el rango se valida aparte, no aquí
    ("010", 8),            # base 0: el cero inicial es octal, como strtol
])
def test_parsear_numero_acepta_lo_que_acepta_strtol(texto, esperado):
    assert protocolo.parsear_numero(texto) == esperado


@pytest.mark.parametrize("texto", [
    None, "", "abc", "0x", "12x", "0x1G", "1 2", "09", "--3", "0b101",
])
def test_parsear_numero_rechaza_lo_que_rechaza_strtol(texto):
    assert protocolo.parsear_numero(texto) is None


@pytest.mark.parametrize("valor,esperado", [
    (0, True), (255, True), (-1, False), (256, False), (128, True),
])
def test_en_rango_replica_enrango(valor, esperado):
    assert protocolo.en_rango(valor) is esperado


# ── EnsambladorDeBloques ───────────────────────────────────────────────────

def test_una_linea_suelta_sale_tal_cual():
    ensamblador = protocolo.EnsambladorDeBloques()
    assert ensamblador.agregar("OK reset") == [protocolo.Mensaje("linea", "OK reset")]


def test_el_bloque_multilinea_se_reensambla_completo():
    ensamblador = protocolo.EnsambladorDeBloques()
    bloque = (
        "─── Ciclo 1 ───\n"
        "FETCH   PC=0x00  →  IR=0x30 (LDI A)\n"
        "DECODE  Opcode 0011 | 2 bytes | modo inmediato\n"
        "EXECUTE #0x00 → A\n"
        "RESULT  A=0x00\n"
        "PC → 0x02"
    )
    mensajes = []
    for linea in bloque.split("\n"):
        mensajes.extend(ensamblador.agregar(linea))

    assert len(mensajes) == 1
    assert mensajes[0].es_bloque
    assert mensajes[0].texto == bloque


def test_el_bloque_no_emite_nada_hasta_ver_la_marca_final():
    ensamblador = protocolo.EnsambladorDeBloques()
    assert ensamblador.agregar("─── Ciclo 3 ───") == []
    assert ensamblador.agregar("FETCH   PC=0x08  →  IR=0x10 (LDA)") == []
    assert ensamblador.dentro_de_bloque
    assert len(ensamblador.agregar("PC → 0x0A")) == 1
    assert not ensamblador.dentro_de_bloque


def test_la_linea_clave_valor_que_sigue_al_bloque_sale_aparte():
    ensamblador = protocolo.EnsambladorDeBloques()
    for linea in ["─── Ciclo 1 ───", "RESULT  —", "PC → 0x01"]:
        mensajes = ensamblador.agregar(linea)
    siguientes = ensamblador.agregar("#ciclo=1 pc=0x01 ir=0x00 op=NOP a=0x00 "
                                     "b=0x00 z=0 c=0 halted=0")
    assert len(mensajes) == 1 and mensajes[0].es_bloque
    assert len(siguientes) == 1 and siguientes[0].tipo == "linea"


def test_el_ensamblador_ignora_el_retorno_de_carro_del_serial():
    ensamblador = protocolo.EnsambladorDeBloques()
    assert ensamblador.agregar("OK reset\r\n")[0].texto == "OK reset"


def test_vaciar_cierra_un_bloque_a_medias():
    ensamblador = protocolo.EnsambladorDeBloques()
    ensamblador.agregar("─── Ciclo 9 ───")
    mensajes = ensamblador.vaciar()
    assert mensajes[0].texto == "─── Ciclo 9 ───"
    assert ensamblador.vaciar() == []


def test_el_ensamblador_reconstruye_lo_que_produce_format_cycle():
    from sim.trace import format_cycle

    ensamblador = protocolo.EnsambladorDeBloques()
    recibidos = []
    for traza, _ in trazas_de(read_source("programas/referencia.asm")):
        for linea in format_cycle(traza).split("\n"):
            recibidos.extend(ensamblador.agregar(linea))

    esperados = [format_cycle(t) for t, _ in
                 trazas_de(read_source("programas/referencia.asm"))]
    assert [m.texto for m in recibidos] == esperados
    assert all(m.es_bloque for m in recibidos)


# ── parsear_linea_clave_valor ──────────────────────────────────────────────

def test_parsear_linea_clave_valor_devuelve_enteros():
    datos = protocolo.parsear_linea_clave_valor(
        "#ciclo=4 pc=0x0A ir=0x60 op=ADD a=0x04 b=0x03 z=0 c=0 halted=0")
    assert datos == {
        "ciclo": 4, "pc": 0x0A, "ir": 0x60, "op": "ADD",
        "a": 4, "b": 3, "z": 0, "c": 0, "halted": 0,
    }


def test_parsear_linea_clave_valor_respeta_el_espacio_de_ldi_a():
    # "LDI A" lleva un espacio DENTRO del valor: partir por espacios sin más
    # rompería el resto de las claves.
    datos = protocolo.parsear_linea_clave_valor(
        "#ciclo=1 pc=0x02 ir=0x30 op=LDI A a=0x05 b=0x00 z=0 c=0 halted=0")
    assert datos["op"] == "LDI A"
    assert datos["a"] == 5
    assert datos["halted"] == 0


def test_parsear_linea_clave_valor_lee_la_salida():
    datos = protocolo.parsear_linea_clave_valor(
        "#ciclo=9 pc=0x1B ir=0xB0 op=OUT a=0x0C b=0x00 z=0 c=0 halted=0 salida=12")
    assert datos["salida"] == 12


def test_parsear_linea_clave_valor_lee_la_linea_de_estado():
    datos = protocolo.parsear_linea_clave_valor(
        "#pc=0x00 ir=0x00 a=0x00 b=0x00 z=0 c=0 halted=0")
    assert "ciclo" not in datos
    assert datos["pc"] == 0 and datos["halted"] == 0


def test_parsear_linea_clave_valor_lee_el_microciclo():
    assert protocolo.parsear_linea_clave_valor("#paso=EXECUTE") == {"paso": "EXECUTE"}


def test_parsear_linea_clave_valor_ignora_lo_que_no_empieza_con_almohadilla():
    assert protocolo.parsear_linea_clave_valor("OK reset") is None


def test_se_puede_ir_y_volver_entre_formato_y_parseo():
    for traza, detenido in trazas_de(read_source("programas/referencia.asm")):
        datos = protocolo.parsear_linea_clave_valor(
            protocolo.linea_clave_valor(traza, detenido))
        a, b = protocolo.valores_reportados(traza)
        assert datos["pc"] == traza.pc_after
        assert datos["ir"] == traza.ir
        assert datos["a"] == a and datos["b"] == b
        assert datos["op"] == traza.mnemonic
        assert datos["halted"] == (1 if detenido else 0)


# ── La rareza de los ceros del firmware (nucleo.cpp: traza_ = Traza()) ─────

def test_los_saltos_reportan_a_y_b_en_cero_como_el_firmware():
    # nucleo.cpp reinicia la Traza en cada instrucción y CAT_SALTO_* no toca
    # aDespues/bDespues: el Arduino real manda 0x00 aunque A valga otra cosa.
    trazas = trazas_de("LDI A,#0x07\nJMP FIN\nFIN: HLT\n")
    salto = protocolo.linea_clave_valor(*trazas[1])
    assert "op=JMP" in salto
    assert "a=0x00 b=0x00" in salto


def test_una_carga_solo_reporta_el_registro_destino():
    trazas = trazas_de("LDI A,#0x07\nLDI B,#0x03\nHLT\n")
    assert "a=0x07 b=0x00" in protocolo.linea_clave_valor(*trazas[0])
    # El LDI B deja A en 0x07, pero el firmware solo rellena bDespues.
    assert "a=0x00 b=0x03" in protocolo.linea_clave_valor(*trazas[1])


def test_una_operacion_de_alu_reporta_los_dos_registros():
    trazas = trazas_de("LDI A,#0x04\nLDI B,#0x03\nADD\nHLT\n")
    assert "a=0x07 b=0x03" in protocolo.linea_clave_valor(*trazas[2])


def test_sta_y_out_reportan_el_a_que_usaron():
    trazas = trazas_de("LDI A,#0x0C\nSTA 0xC0\nOUT\nHLT\n")
    assert "a=0x0C b=0x00" in protocolo.linea_clave_valor(*trazas[1])   # STA
    assert "a=0x0C b=0x00" in protocolo.linea_clave_valor(*trazas[2])   # OUT


@pytest.mark.parametrize("op,esperado", [
    ("ADD", (True, True)),
    ("SUB", (True, True)),
    ("LDA", (True, False)),
    ("LDB", (False, True)),
    ("LDI A", (True, False)),
    ("LDI B", (False, True)),
    ("STA", (True, False)),
    ("OUT", (True, False)),
    ("JMP", (False, False)),
    ("JNZ", (False, False)),
    ("NOP", (False, False)),
    ("HLT", (False, False)),
    ("???", (False, False)),
])
def test_registros_significativos(op, esperado):
    assert protocolo.registros_significativos(op) == esperado


# ── extraer_control_alu / numero_de_ciclo ──────────────────────────────────

def test_extraer_control_alu_saca_m_s_y_cn():
    bloque = (
        "─── Ciclo 5 ───\n"
        "FETCH   PC=0x0C  →  IR=0x60 (ADD)\n"
        "DECODE  Opcode 0110 | 1 byte | modo implícito\n"
        "EXECUTE A=0x04 + B=0x03\n"
        "        ALU: M=0 S=1001 Cn=1\n"
        "RESULT  A=0x07   Z=0  C=0\n"
        "PC → 0x0D"
    )
    assert protocolo.extraer_control_alu(bloque) == {"M": 0, "S": "1001", "Cn": 1}


def test_extraer_control_alu_devuelve_none_sin_operacion_de_alu():
    bloque = ("─── Ciclo 1 ───\n"
              "EXECUTE Muestra A\n"
              "RESULT  A=0x0C\n"
              "PC → 0x1B")
    assert protocolo.extraer_control_alu(bloque) is None


def test_extraer_control_alu_funciona_sobre_bloques_reales():
    from sim.trace import format_cycle

    vistos = []
    for traza, _ in trazas_de("LDI A,#0x04\nLDI B,#0x03\nSUB\nHLT\n"):
        control = protocolo.extraer_control_alu(format_cycle(traza))
        if control is not None:
            vistos.append(control)
    # SUB en el 74LS181: M=0 (aritmético) y S=0110 — lo que lo distingue de XOR
    # es justamente el M, no el selector.
    assert vistos == [{"M": 0, "S": "0110", "Cn": 0}]


def test_numero_de_ciclo():
    assert protocolo.numero_de_ciclo("─── Ciclo 12 ───\nPC → 0x00") == 12
    assert protocolo.numero_de_ciclo("OK reset") is None


def test_parsear_fila_dump():
    assert protocolo.parsear_fila_dump("0xC8: 0C 00 ") == (0xC8, [0x0C, 0x00])


def test_parsear_fila_dump_de_una_fila_entera():
    fila = "0x00: 30 00 50 C8 30 03 50 C9 10 C8 20 CC 60 50 C8 10 "
    direccion, bytes_leidos = protocolo.parsear_fila_dump(fila)
    assert direccion == 0x00
    assert len(bytes_leidos) == 16
    assert bytes_leidos[:4] == [0x30, 0x00, 0x50, 0xC8]


def test_parsear_fila_dump_tolera_la_falta_del_espacio_final():
    assert protocolo.parsear_fila_dump("0x10: FF") == (0x10, [0xFF])


@pytest.mark.parametrize("linea", [
    "OK reset",
    "#ciclo=1 pc=0x02",
    "--- RUN ---",
    "0xC8 0C 00",          # sin los dos puntos
    "0xC8: ",              # sin bytes
    "0xC8: 0C0 00",        # un token que no es un byte
    "0x1FF: 00 ",          # dirección fuera de rango
])
def test_parsear_fila_dump_rechaza_lo_que_no_es_una_fila(linea):
    assert protocolo.parsear_fila_dump(linea) is None


@pytest.mark.parametrize("linea,esperado", [
    ("OK reset", True),
    ("ERR valor fuera de rango (0-255)", True),
    ("#ciclo=1 pc=0x02", False),
    ("--- RUN ---", False),
])
def test_es_respuesta_final(linea, esperado):
    assert protocolo.es_respuesta_final(linea) is esperado
