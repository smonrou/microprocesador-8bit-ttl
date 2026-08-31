"""Lockstep: el núcleo del firmware contra el simulador B.1.

El mismo binario se ejecuta en las dos implementaciones y se comparan
instrucción por instrucción. Cuando algo diverge, el mensaje dice en cuál y
con qué valores — no "el resultado final no coincide".

Es la única verificación posible mientras el Arduino Mega no llegue.
"""

import pytest

from asm import assemble
from asm.examples import read_source
from sim.cpu import CPU
from sim.memory import Memory

PROGRAMAS = [
    "programas/referencia.asm",
    "programas/referencia_etiquetas.asm",
    "programas/demo_alu.asm",
    "programas/demo_multiplicacion.asm",
]


def estados_del_simulador(binario):
    """Recorre sim/cpu.py y devuelve el estado tras cada instrucción."""
    memoria = Memory()
    memoria.load_bytes(binario)
    cpu = CPU(memoria)

    estados = []
    while not cpu.halted:
        resultado = cpu.step()
        if not resultado.completed:
            continue
        traza = resultado.trace
        estados.append({
            "n": traza.cycle_number,
            "pc_antes": traza.pc_before,
            "ir": traza.ir,
            "op": traza.mnemonic,
            "a": cpu.a,
            "b": cpu.b,
            "z": cpu.z,
            "c": cpu.c,
            "pc": cpu.pc,
        })
    return estados, cpu


def comparar(firmware, simulador, etiqueta):
    """Compara paso a paso y falla en la primera divergencia."""
    for indice, esperado in enumerate(simulador):
        assert indice < len(firmware), (
            f"{etiqueta}: el firmware se detuvo en la instrucción "
            f"{len(firmware)}, el simulador siguió hasta {len(simulador)}"
        )
        obtenido = firmware[indice]

        for clave in ("n", "pc_antes", "ir", "a", "b", "z", "c", "pc"):
            valor_firmware = int(obtenido[clave], 0)
            if valor_firmware != esperado[clave]:
                pytest.fail(
                    f"{etiqueta}: divergencia en la instrucción "
                    f"{esperado['n']} ({esperado['op']}, "
                    f"PC=0x{esperado['pc_antes']:02X}): "
                    f"{clave} vale 0x{valor_firmware:02X} en el firmware y "
                    f"0x{esperado[clave]:02X} en el simulador"
                )

        assert obtenido["op"] == esperado["op"], (
            f"{etiqueta}: instrucción {esperado['n']}: el firmware decodificó "
            f"'{obtenido['op']}' y el simulador '{esperado['op']}'"
        )

    assert len(firmware) == len(simulador), (
        f"{etiqueta}: el firmware ejecutó {len(firmware)} instrucciones y "
        f"el simulador {len(simulador)}"
    )


@pytest.mark.parametrize("ruta", PROGRAMAS)
def test_lockstep_contra_el_simulador(ejecutar_arnes, ruta):
    binario = assemble(read_source(ruta)).binary
    resultado = ejecutar_arnes(binario)
    esperados, _ = estados_del_simulador(binario)

    comparar(resultado["instrucciones"], esperados, ruta)


@pytest.mark.parametrize("ruta", PROGRAMAS)
def test_misma_salida_de_out(ejecutar_arnes, ruta):
    binario = assemble(read_source(ruta)).binary
    resultado = ejecutar_arnes(binario)
    _, cpu = estados_del_simulador(binario)

    assert resultado["salidas"] == cpu.output


@pytest.mark.parametrize("ruta", PROGRAMAS)
def test_misma_memoria_final(ejecutar_arnes, ruta):
    binario = assemble(read_source(ruta)).binary
    resultado = ejecutar_arnes(binario)
    _, cpu = estados_del_simulador(binario)

    assert resultado["memoria"] == cpu.memory.dump()


def test_programa_de_referencia_da_doce(ejecutar_arnes):
    # El criterio de aceptación canónico (A.7), ahora sobre el firmware.
    binario = assemble(read_source("programas/referencia.asm")).binary
    resultado = ejecutar_arnes(binario)

    assert resultado["salidas"] == [12]
    assert resultado["detenido"] is True


def test_demo_alu_ejercita_las_seis_funciones(ejecutar_arnes):
    binario = assemble(read_source("programas/demo_alu.asm")).binary
    resultado = ejecutar_arnes(binario)

    assert resultado["salidas"] == [8, 2, 136, 238, 102, 240]


# ── Casos sintéticos por opcode ──────────────────────────────────────────

def ensamblar(fuente):
    return assemble(fuente).binary


CASOS_ALU = [
    ("suma simple", "LDI A,#3\nLDI B,#2\nADD\nOUT\nHLT\n", [5]),
    ("desborde de suma", "LDI A,#255\nLDI B,#1\nADD\nOUT\nHLT\n", [0]),
    ("resta positiva", "LDI A,#5\nLDI B,#3\nSUB\nOUT\nHLT\n", [2]),
    ("resta negativa", "LDI A,#3\nLDI B,#5\nSUB\nOUT\nHLT\n", [254]),
    ("resta a cero", "LDI A,#5\nLDI B,#5\nSUB\nOUT\nHLT\n", [0]),
    ("and", "LDI A,#0xCC\nLDI B,#0xAA\nAND\nOUT\nHLT\n", [0x88]),
    ("or", "LDI A,#0xCC\nLDI B,#0xAA\nOR\nOUT\nHLT\n", [0xEE]),
    ("xor", "LDI A,#0xCC\nLDI B,#0xAA\nXOR\nOUT\nHLT\n", [0x66]),
    ("not via xor", "LDI A,#0x0F\nLDI B,#0xFF\nXOR\nOUT\nHLT\n", [0xF0]),
]


@pytest.mark.parametrize("nombre,fuente,esperado", CASOS_ALU,
                         ids=[caso[0] for caso in CASOS_ALU])
def test_casos_de_alu(ejecutar_arnes, nombre, fuente, esperado):
    binario = ensamblar(fuente)
    resultado = ejecutar_arnes(binario)
    assert resultado["salidas"] == esperado


@pytest.mark.parametrize("nombre,fuente,esperado", CASOS_ALU,
                         ids=[caso[0] for caso in CASOS_ALU])
def test_casos_de_alu_en_lockstep(ejecutar_arnes, nombre, fuente, esperado):
    binario = ensamblar(fuente)
    resultado = ejecutar_arnes(binario)
    esperados, _ = estados_del_simulador(binario)
    comparar(resultado["instrucciones"], esperados, nombre)


# ── Regla crítica de banderas ────────────────────────────────────────────

def test_sta_no_borra_z_asi_que_jz_salta(ejecutar_arnes):
    # A.5: solo las 5 operaciones de ALU tocan Z y C. Si STA la borrara, el
    # salto no ocurriría y OUT mostraría 0x99 en vez de 0x42.
    fuente = (
        "      LDI A,#5\n"
        "      LDI B,#5\n"
        "      SUB\n"            # Z=1
        "      STA 0xC0\n"       # no debe tocar Z
        "      JZ DESTINO\n"
        "      LDI A,#0x99\n"
        "      OUT\n"
        "      HLT\n"
        "DESTINO: LDI A,#0x42\n"
        "      OUT\n"
        "      HLT\n"
    )
    resultado = ejecutar_arnes(ensamblar(fuente))
    assert resultado["salidas"] == [0x42]


@pytest.mark.parametrize("instruccion", [
    "NOP", "LDA 0xC0", "LDB 0xC0", "LDI A,#7", "LDI B,#7",
    "STA 0xC0", "OUT", "JMP SIGUE", "JZ SIGUE", "JNZ SIGUE",
])
def test_ninguna_instruccion_no_alu_toca_las_banderas(ejecutar_arnes, instruccion):
    # Se deja Z=1 C=1 con una resta a cero y se comprueba que sobreviven.
    fuente = (
        f"      LDI A,#5\n"
        f"      LDI B,#5\n"
        f"      SUB\n"
        f"      {instruccion}\n"
        f"SIGUE: HLT\n"
    )
    binario = ensamblar(fuente)
    resultado = ejecutar_arnes(binario)
    esperados, _ = estados_del_simulador(binario)
    comparar(resultado["instrucciones"], esperados, instruccion)

    ultima = resultado["instrucciones"][-1]
    assert int(ultima["z"], 0) == 1, f"{instruccion} modificó Z"
    assert int(ultima["c"], 0) == 1, f"{instruccion} modificó C"


# ── Control de flujo ─────────────────────────────────────────────────────

def test_salto_incondicional(ejecutar_arnes):
    fuente = "JMP FIN\nLDI A,#0x99\nOUT\nFIN: LDI A,#7\nOUT\nHLT\n"
    assert ejecutar_arnes(ensamblar(fuente))["salidas"] == [7]


def test_bucle_termina_por_bandera_z(ejecutar_arnes):
    fuente = (
        "      LDI A,#3\n"
        "BUCLE: LDI B,#1\n"
        "      SUB\n"
        "      JNZ BUCLE\n"
        "      OUT\n"
        "      HLT\n"
    )
    resultado = ejecutar_arnes(ensamblar(fuente))
    assert resultado["salidas"] == [0]
    assert resultado["detenido"] is True


def test_limite_de_instrucciones_corta_un_bucle_infinito(ejecutar_arnes):
    resultado = ejecutar_arnes(ensamblar("BUCLE: JMP BUCLE\n"), "--limite", "50")
    assert resultado["limite"] is True
    assert resultado["detenido"] is False
