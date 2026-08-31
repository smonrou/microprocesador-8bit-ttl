"""One test per row of the B.1 ALU acceptance table (contexto_proyecto.md)."""

import pytest

from sim import alu


def test_simple_add():
    result, z, c = alu.add(3, 2)
    assert (result, z) == (5, 0)


def test_add_overflow():
    result, z, c = alu.add(255, 1)
    assert (result, z, c) == (0, 1, 1)


def test_sub_positive():
    result, z, c = alu.sub(5, 3)
    assert (result, z, c) == (2, 0, 1)  # A>=B: no borrow -> C=1


def test_sub_negative():
    result, z, c = alu.sub(3, 5)
    assert (result, z, c) == (254, 0, 0)  # A<B: borrow -> C=0, -2 en complemento a 2


def test_sub_to_zero():
    result, z, c = alu.sub(5, 5)
    assert (result, z, c) == (0, 1, 1)


def test_and():
    result, z, c = alu.bit_and(0xCC, 0xAA)
    assert (result, z, c) == (0x88, 0, 0)


def test_or():
    result, z, c = alu.bit_or(0xCC, 0xAA)
    assert (result, z, c) == (0xEE, 0, 0)


def test_xor():
    result, z, c = alu.bit_xor(0xCC, 0xAA)
    assert (result, z, c) == (0x66, 0, 0)


def test_not_via_xor():
    result, z, c = alu.bit_xor(0x0F, 0xFF)
    assert result == 0xF0
