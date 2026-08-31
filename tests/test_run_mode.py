"""Infinite-loop detection: run() must raise, never hang."""

import pytest

from sim.cpu import CPU
from sim.exceptions import CycleLimitExceeded
from sim.memory import Memory


def test_cycle_limit_exceeded_on_infinite_loop():
    memory = Memory()
    memory.load_bytes([0xD0, 0x00])  # JMP 0x00 — jumps to itself, forever
    cpu = CPU(memory)
    with pytest.raises(CycleLimitExceeded):
        cpu.run(max_cycles=50)


def test_cycle_limit_exceeded_reports_instruction_count():
    memory = Memory()
    memory.load_bytes([0xD0, 0x00])
    cpu = CPU(memory)
    with pytest.raises(CycleLimitExceeded) as exc_info:
        cpu.run(max_cycles=50)
    assert exc_info.value.instruction_count > 50
