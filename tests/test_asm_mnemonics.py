"""Guardián de la fuente única de verdad del ISA.

Si alguien alguna vez codifica una segunda tabla de opcodes dentro de asm/,
estos tests fallan ruidosamente. "Parte A es inmutable" (regla D.1).
"""

import pytest

from asm.mnemonics import (
    DIRECTIVES,
    MAX_MNEMONIC_WORDS,
    MNEMONIC_TABLE,
    completion_hint,
    is_directive,
    is_mnemonic,
    lookup,
)
from sim.isa import OPCODE_TABLE


def test_table_derives_exactly_from_opcode_table():
    expected = {spec.mnemonic.upper() for spec in OPCODE_TABLE.values()}
    assert set(MNEMONIC_TABLE) == expected


def test_sixteen_mnemonics():
    assert len(MNEMONIC_TABLE) == 16


def test_ldi_a_and_ldi_b_are_distinct_opcodes():
    # A.5: LDI A = 0011, LDI B = 0100. Confusión frecuente.
    assert MNEMONIC_TABLE["LDI A"].opcode == 0x3
    assert MNEMONIC_TABLE["LDI B"].opcode == 0x4


def test_max_mnemonic_words_is_derived_not_hardcoded():
    assert MAX_MNEMONIC_WORDS == max(
        len(spec.mnemonic.split()) for spec in OPCODE_TABLE.values()
    )


@pytest.mark.parametrize("text", ["lda", "LDA", "LdA", "ldi a", "LDI A", "LdI b"])
def test_lookup_is_case_insensitive(text):
    assert lookup(text) is not None


def test_lookup_unknown_returns_none():
    assert lookup("LDX") is None


def test_bare_ldi_is_not_a_mnemonic():
    # Solo existen "LDI A" y "LDI B"; "LDI" pelado debe caer en desconocido.
    assert lookup("LDI") is None
    assert not is_mnemonic("LDI")


def test_completion_hint_for_bare_ldi():
    hint = completion_hint("LDI")
    assert hint is not None
    assert "LDI A" in hint and "LDI B" in hint


def test_completion_hint_none_for_real_mnemonic():
    assert completion_hint("ADD") is None


@pytest.mark.parametrize("text", [".ORG", ".org", ".DB", ".db"])
def test_directives_recognized_case_insensitively(text):
    assert is_directive(text)


def test_directives_are_not_mnemonics():
    for directive in DIRECTIVES:
        assert not is_mnemonic(directive)


def test_every_spec_length_is_1_or_2():
    for spec in MNEMONIC_TABLE.values():
        assert spec.length in (1, 2)
