"""Same acceptance-table cases as test_alu.py, but end-to-end through CPU +
Memory via real fetch/decode/execute, not calling alu.py directly."""

import pytest

from sim.cpu import CPU
from sim.memory import Memory

LDI_A = 0x30
LDI_B = 0x40
HLT = 0xC0

ADD = 0x60
SUB = 0x70
AND = 0x80
OR = 0x90
XOR = 0xA0


def run_alu_program(a_val: int, b_val: int, op_byte: int) -> CPU:
    memory = Memory()
    memory.load_bytes([LDI_A, a_val, LDI_B, b_val, op_byte, HLT])
    cpu = CPU(memory)
    cpu.run()
    return cpu


def test_simple_add():
    cpu = run_alu_program(3, 2, ADD)
    assert cpu.a == 5 and cpu.z == 0


def test_add_overflow():
    cpu = run_alu_program(255, 1, ADD)
    assert (cpu.a, cpu.z, cpu.c) == (0, 1, 1)


def test_sub_positive():
    cpu = run_alu_program(5, 3, SUB)
    assert (cpu.a, cpu.z) == (2, 0)


def test_sub_negative():
    cpu = run_alu_program(3, 5, SUB)
    assert (cpu.a, cpu.z) == (254, 0)


def test_sub_to_zero():
    cpu = run_alu_program(5, 5, SUB)
    assert (cpu.a, cpu.z) == (0, 1)


def test_and():
    cpu = run_alu_program(0xCC, 0xAA, AND)
    assert cpu.a == 0x88


def test_or():
    cpu = run_alu_program(0xCC, 0xAA, OR)
    assert cpu.a == 0xEE


def test_xor():
    cpu = run_alu_program(0xCC, 0xAA, XOR)
    assert cpu.a == 0x66


def test_not_via_xor():
    cpu = run_alu_program(0x0F, 0xFF, XOR)
    assert cpu.a == 0xF0


def test_halted_after_hlt():
    cpu = run_alu_program(1, 1, ADD)
    assert cpu.halted is True
