"""Directivas .ORG y .DB (decisión B.0), etiquetas como dirección de dato,
y forma del binario de salida."""

import pytest

from asm import assemble
from sim.memory import SIZE


def test_binary_is_always_256_bytes():
    assert len(assemble("HLT\n").binary) == SIZE


def test_binary_is_zero_outside_emitted_spans():
    result = assemble("NOP\nHLT\n")
    assert result.binary[0] == 0x00 and result.binary[1] == 0xC0
    assert all(byte == 0 for byte in result.binary[2:])


# ── .ORG ──────────────────────────────────────────────────────────────────

def test_org_moves_pointer_and_emits_nothing():
    result = assemble(".ORG 0x10\nHLT\n")
    assert result.binary[0x10] == 0xC0
    assert result.spans == ((0x10, 0x10),)


def test_org_accepts_all_number_bases():
    for source in [".ORG 204", ".ORG 0xCC", ".ORG $CC"]:
        result = assemble(source + "\n.DB 7\n")
        assert result.binary[204] == 7


def test_org_can_place_code_then_data():
    result = assemble(".ORG 0x00\nHLT\n.ORG 0xC0\n.DB 9\n")
    assert result.binary[0x00] == 0xC0
    assert result.binary[0xC0] == 9


# ── .DB ───────────────────────────────────────────────────────────────────

def test_db_single_value():
    result = assemble(".ORG 0xC0\n.DB 42\n")
    assert result.binary[0xC0] == 42


def test_db_multiple_values():
    result = assemble(".ORG 0xC0\n.DB 1, 2, 3\n")
    assert list(result.binary[0xC0:0xC3]) == [1, 2, 3]


def test_db_accepts_all_number_bases():
    result = assemble(".ORG 0xC0\n.DB 12, 0xFF, $0A, 0b1010\n")
    assert list(result.binary[0xC0:0xC4]) == [12, 255, 10, 10]


# ── Etiquetas como dirección de dato (decisión de esta sesión) ────────────

def test_label_as_data_address():
    source = ".ORG 0x00\nLDB CUATRO\nHLT\n.ORG 204\nCUATRO: .DB 4\n"
    result = assemble(source)
    assert result.symbols["CUATRO"] == 0xCC
    assert result.binary[1] == 0xCC   # el operando de LDB resuelve a 204
    assert result.binary[0xCC] == 4


def test_label_works_for_both_jumps_and_data():
    source = (
        "LOOP: LDA DATO\n"
        "      JNZ LOOP\n"
        "      HLT\n"
        ".ORG 0xC8\n"
        "DATO: .DB 7\n"
    )
    result = assemble(source)
    assert result.symbols == {"LOOP": 0x00, "DATO": 0xC8}
    assert result.binary[1] == 0xC8    # operando de LDA
    assert result.binary[3] == 0x00    # destino de JNZ


def test_immediate_label_resolves_to_address():
    source = "LDI A,#DATO\nHLT\n.ORG 0xC8\nDATO: .DB 7\n"
    result = assemble(source)
    assert result.binary[1] == 0xC8


def test_forward_reference_resolves():
    # Es la razón de ser de las dos pasadas: usar una etiqueta antes de
    # definirla.
    result = assemble("JMP FIN\nNOP\nFIN: HLT\n")
    assert result.binary[1] == 0x03


# ── Advertencias ──────────────────────────────────────────────────────────

def test_warning_when_db_lands_in_program_zone():
    result = assemble("HLT\n.ORG 0x50\n.DB 1\n")
    assert any("zona de programa" in warning for warning in result.warnings)


def test_no_warning_when_db_in_data_zone():
    result = assemble("HLT\n.ORG 0xC0\n.DB 1\n")
    assert not any("zona de programa" in warning for warning in result.warnings)


def test_warning_when_nothing_emitted_at_zero():
    result = assemble(".ORG 0x10\nHLT\n")
    assert any("0x00" in warning for warning in result.warnings)


def test_no_warning_for_normal_program():
    result = assemble("NOP\nHLT\n")
    assert result.warnings == ()


# ── Spans ─────────────────────────────────────────────────────────────────

def test_spans_group_contiguous_addresses():
    result = assemble("NOP\nHLT\n.ORG 0xC8\n.DB 1, 2\n")
    assert result.spans == ((0x00, 0x01), (0xC8, 0xC9))
