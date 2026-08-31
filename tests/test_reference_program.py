"""Criterio de aceptación principal de B.1: el programa de A.7 (multiplicación
4x3 por sumas repetidas) debe dar OUT=12 y terminar en HLT."""

from sim.cpu import CPU
from sim.programs import (
    COUNTER_ADDRESS,
    EXPECTED_OUTPUT,
    RESULT_ADDRESS,
    build_reference_memory,
)


def test_reference_program_outputs_12_and_halts():
    cpu = CPU(build_reference_memory())
    cpu.run()

    assert cpu.halted is True
    assert cpu.output == [EXPECTED_OUTPUT]


def test_reference_program_final_memory_state():
    cpu = CPU(build_reference_memory())
    cpu.run()

    assert cpu.memory.read(RESULT_ADDRESS) == 12
    assert cpu.memory.read(COUNTER_ADDRESS) == 0


def test_reference_program_terminates_within_reasonable_cycles():
    # 11 instrucciones x 3 vueltas de LOOP + preámbulo/cola — no debe
    # acercarse al límite por defecto de 10000.
    cpu = CPU(build_reference_memory())
    cpu.run(max_cycles=200)
    assert cpu.halted is True
