"""Pure ALU functions — mirror the SN74LS181 truth table (contexto_proyecto.md A.3/A.5).

Each function takes two 8-bit ints and returns (result: int, z: int, c: int).
No CPU/memory state here — kept isolated so it can be tested standalone and
cross-checked later against the real hardware's behavior.
"""

from typing import Tuple

MASK8 = 0xFF


def _flags_from_raw(raw: int) -> Tuple[int, int]:
    result = raw & MASK8
    z = 1 if result == 0 else 0
    c = 1 if raw > MASK8 else 0
    return result, z, c


def add(a: int, b: int) -> Tuple[int, int, int]:
    raw = a + b
    result, z, c = _flags_from_raw(raw)
    return result, z, c


def sub(a: int, b: int) -> Tuple[int, int, int]:
    # Hardware computes A + (NOT B) + 1 (two's complement). C=1 means no
    # borrow occurred (A >= B unsigned), C=0 means a borrow occurred.
    raw = a + ((~b) & MASK8) + 1
    result, z, c = _flags_from_raw(raw)
    return result, z, c


def bit_and(a: int, b: int) -> Tuple[int, int, int]:
    result = a & b & MASK8
    z = 1 if result == 0 else 0
    return result, z, 0


def bit_or(a: int, b: int) -> Tuple[int, int, int]:
    result = (a | b) & MASK8
    z = 1 if result == 0 else 0
    return result, z, 0


def bit_xor(a: int, b: int) -> Tuple[int, int, int]:
    result = (a ^ b) & MASK8
    z = 1 if result == 0 else 0
    return result, z, 0


ALU_FUNCTIONS = {
    "ADD": add,
    "SUB": sub,
    "AND": bit_and,
    "OR": bit_or,
    "XOR": bit_xor,
}
