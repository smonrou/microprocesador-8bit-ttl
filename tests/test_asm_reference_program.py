"""Criterio de aceptación de B.2: ensamblar el programa de A.7 y que su
salida, ejecutada en el simulador de B.1, dé 12."""

import pytest

from asm import assemble
from asm.examples import read_reference_labels_source, read_reference_source
from sim.cpu import CPU
from sim.memory import Memory
from sim.programs import (
    CONST_4_ADDRESS,
    COUNTER_ADDRESS,
    EXPECTED_OUTPUT,
    LOOP_ADDRESS,
    REFERENCE_PROGRAM,
    RESULT_ADDRESS,
    build_reference_memory,
)


@pytest.fixture
def result():
    return assemble(read_reference_source())


def test_bytes_match_hand_assembled(result):
    # Validación cruzada en ambos sentidos: prueba que el ensamblador
    # acierta Y re-prueba que los bytes a mano de B.1 estaban bien. Si algún
    # día discrepan, uno de los dos está mal y el test lo dice antes que el
    # hardware.
    assert list(result.binary[: len(REFERENCE_PROGRAM)]) == REFERENCE_PROGRAM


def test_full_image_matches_reference_memory(result):
    # Bytes de programa + el 4 en 0xCC + relleno de ceros, en una línea.
    # B.1 escribía 0xCC a mano porque no había ensamblador; aquí lo pone
    # `.DB 4` — que es el punto entero de la directiva (decisión B.0).
    assert list(result.binary) == build_reference_memory().dump()


def test_loop_label_resolves_to_0x08(result):
    assert result.symbols["LOOP"] == LOOP_ADDRESS


def test_data_constant_lands_at_204(result):
    assert result.binary[CONST_4_ADDRESS] == 4


def test_binary_is_256_bytes(result):
    assert len(result.binary) == 256


def test_end_to_end_outputs_12(result):
    # EL criterio de aceptación. Sin memory.write(0xCC, 4) manual: el
    # binario debe bastarse solo.
    memory = Memory()
    memory.load_bytes(result.binary)
    cpu = CPU(memory)
    cpu.run()

    assert cpu.output == [EXPECTED_OUTPUT]
    assert cpu.halted is True


def test_end_to_end_final_memory(result):
    memory = Memory()
    memory.load_bytes(result.binary)
    cpu = CPU(memory)
    cpu.run()

    assert cpu.memory.read(RESULT_ADDRESS) == 12
    assert cpu.memory.read(COUNTER_ADDRESS) == 0


def test_ambas_versiones_dan_bytes_identicos():
    # Las etiquetas de datos son azúcar sintáctico puro: mismo binario.
    fiel = assemble(read_reference_source())
    etiquetas = assemble(read_reference_labels_source())
    assert fiel.binary == etiquetas.binary


def test_version_con_etiquetas_tambien_da_12():
    result = assemble(read_reference_labels_source())
    memory = Memory()
    memory.load_bytes(result.binary)
    cpu = CPU(memory)
    cpu.run()
    assert cpu.output == [EXPECTED_OUTPUT]


def test_version_con_etiquetas_resuelve_direcciones_de_datos():
    result = assemble(read_reference_labels_source())
    assert result.symbols["RESULTADO"] == RESULT_ADDRESS
    assert result.symbols["CONTADOR"] == COUNTER_ADDRESS
    assert result.symbols["CUATRO"] == CONST_4_ADDRESS


def test_reference_assembles_without_warnings(result):
    assert result.warnings == ()
