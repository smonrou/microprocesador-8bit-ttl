"""Microstep counts per instruction shape (session decision, see plan doc),
CpuHaltedError after HLT, and RUN/STEP equivalence."""

import pytest

from sim.cpu import CPU
from sim.exceptions import CpuHaltedError
from sim.memory import Memory


def steps_to_complete_first_instruction(program_bytes) -> int:
    memory = Memory()
    memory.load_bytes(program_bytes)
    cpu = CPU(memory)
    count = 0
    while True:
        result = cpu.step()
        count += 1
        if result.completed:
            return count


@pytest.mark.parametrize(
    "program_bytes,expected_steps",
    [
        ([0x60, 0xC0], 5),          # ADD: FETCH/DECODE/EXECUTE/WAIT/WRITE
        ([0x70, 0xC0], 5),          # SUB
        ([0x80, 0xC0], 5),          # AND
        ([0x00, 0xC0], 3),          # NOP: FETCH/DECODE/EXECUTE
        ([0xC0], 3),                # HLT
        ([0xB0, 0xC0], 3),          # OUT
        ([0x30, 0x07, 0xC0], 4),    # LDI A,#7: FETCH/DECODE/FETCH2/EXECUTE
        ([0x50, 0xC0, 0xC0], 4),    # STA 0xC0
        ([0xD0, 0x02, 0xC0], 4),    # JMP 0x02
    ],
)
def test_microstep_count_per_instruction_shape(program_bytes, expected_steps):
    assert steps_to_complete_first_instruction(program_bytes) == expected_steps


def test_halted_error_on_step_after_hlt():
    memory = Memory()
    memory.load_bytes([0xC0])
    cpu = CPU(memory)
    while not cpu.halted:
        cpu.step()
    with pytest.raises(CpuHaltedError):
        cpu.step()


def test_run_and_manual_step_agree_on_final_state():
    from sim.programs import build_reference_memory

    cpu_run = CPU(build_reference_memory())
    cpu_run.run()

    cpu_step = CPU(build_reference_memory())
    while not cpu_step.halted:
        cpu_step.step()

    assert cpu_run.a == cpu_step.a
    assert cpu_run.b == cpu_step.b
    assert cpu_run.z == cpu_step.z
    assert cpu_run.c == cpu_step.c
    assert cpu_run.pc == cpu_step.pc
    assert cpu_run.output == cpu_step.output
    assert cpu_run.memory.dump() == cpu_step.memory.dump()
