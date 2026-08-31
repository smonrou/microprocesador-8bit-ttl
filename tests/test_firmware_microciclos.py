"""Los microciclos del firmware contra los de sim/cpu.py.

La paridad importa: el simulador es la referencia con la que se depurará el
hardware, así que STEP debe avanzar exactamente igual en los dos.
"""

import pytest

from asm import assemble
from sim.cpu import CPU
from sim.isa import OPCODE_TABLE, STEPS_2BYTE, STEPS_ALU, STEPS_CONTROL
from sim.memory import Memory

# Una instrucción de cada forma, con el número de microciclos que le toca.
CASOS = [
    ("ADD", "ADD\nHLT\n", list(STEPS_ALU)),
    ("SUB", "SUB\nHLT\n", list(STEPS_ALU)),
    ("AND", "AND\nHLT\n", list(STEPS_ALU)),
    ("OR", "OR\nHLT\n", list(STEPS_ALU)),
    ("XOR", "XOR\nHLT\n", list(STEPS_ALU)),
    ("NOP", "NOP\nHLT\n", list(STEPS_CONTROL)),
    ("OUT", "OUT\nHLT\n", list(STEPS_CONTROL)),
    ("HLT", "HLT\n", list(STEPS_CONTROL)),
    ("LDA", "LDA 0xC0\nHLT\n", list(STEPS_2BYTE)),
    ("LDB", "LDB 0xC0\nHLT\n", list(STEPS_2BYTE)),
    ("LDI A", "LDI A,#7\nHLT\n", list(STEPS_2BYTE)),
    ("LDI B", "LDI B,#7\nHLT\n", list(STEPS_2BYTE)),
    ("STA", "STA 0xC0\nHLT\n", list(STEPS_2BYTE)),
    ("JMP", "JMP DEST\nDEST: HLT\n", list(STEPS_2BYTE)),
    ("JZ", "JZ DEST\nDEST: HLT\n", list(STEPS_2BYTE)),
    ("JNZ", "JNZ DEST\nDEST: HLT\n", list(STEPS_2BYTE)),
]


@pytest.mark.parametrize("nombre,fuente,pasos", CASOS,
                         ids=[caso[0] for caso in CASOS])
def test_pasos_de_la_primera_instruccion(ejecutar_arnes, nombre, fuente, pasos):
    resultado = ejecutar_arnes(assemble(fuente).binary, "--microciclos")
    assert resultado["pasos"][: len(pasos)] == pasos


@pytest.mark.parametrize("nombre,fuente,pasos", CASOS,
                         ids=[caso[0] for caso in CASOS])
def test_el_simulador_da_los_mismos_pasos(nombre, fuente, pasos):
    # El mismo aserto sobre B.1: si alguno cambia, los dos tests divergen.
    memoria = Memory()
    memoria.load_bytes(assemble(fuente).binary)
    cpu = CPU(memoria)

    obtenidos = []
    while True:
        resultado = cpu.step()
        obtenidos.append(resultado.label)
        if resultado.completed:
            break

    assert obtenidos == pasos


def test_el_total_de_microciclos_coincide_con_el_simulador(ejecutar_arnes):
    from asm.examples import read_source

    binario = assemble(read_source("programas/referencia.asm")).binary
    resultado = ejecutar_arnes(binario, "--microciclos")

    memoria = Memory()
    memoria.load_bytes(binario)
    cpu = CPU(memoria)
    total = 0
    while not cpu.halted:
        cpu.step()
        total += 1

    assert resultado["microciclos"] == total


@pytest.mark.parametrize("spec", list(OPCODE_TABLE.values()),
                         ids=lambda s: s.mnemonic)
def test_cada_opcode_declara_los_pasos_de_su_forma(spec):
    # Coherencia interna de la tabla del simulador, que isa.cpp copia.
    esperado = {
        "ALU": len(STEPS_ALU),
        "CONTROL": len(STEPS_CONTROL),
        "2BYTES": len(STEPS_2BYTE),
    }
    if spec.length == 2:
        assert len(spec.microstep_labels) == esperado["2BYTES"]
    elif spec.affects_flags:
        assert len(spec.microstep_labels) == esperado["ALU"]
    else:
        assert len(spec.microstep_labels) == esperado["CONTROL"]
