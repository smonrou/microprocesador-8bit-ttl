"""Las 6 categorías de error exigidas por B.2, más las que introduce .ORG.
Todo error debe traer número de línea."""

import pytest

from asm import assemble
from asm.errors import (
    AssemblyFailed,
    DuplicateLabelError,
    MemoryOverflowError,
    OperandCountError,
    OperandFormError,
    OperandRangeError,
    OverlapError,
    ProgramZoneError,
    UndefinedLabelError,
    UnknownMnemonicError,
)


def assemble_expecting_error(source):
    with pytest.raises(AssemblyFailed) as exc:
        assemble(source)
    return exc.value.errors


# ── 1. Nemónico desconocido ───────────────────────────────────────────────

def test_unknown_mnemonic():
    errors = assemble_expecting_error("LDX 5\nHLT\n")
    assert isinstance(errors[0], UnknownMnemonicError)
    assert errors[0].line_number == 1


def test_bare_ldi_reports_helpful_hint():
    errors = assemble_expecting_error("LDI 5\nHLT\n")
    assert isinstance(errors[0], UnknownMnemonicError)
    assert "LDI A" in errors[0].message and "LDI B" in errors[0].message


# ── 2. Etiqueta no definida ───────────────────────────────────────────────

def test_undefined_label():
    errors = assemble_expecting_error("JNZ NOEXISTE\nHLT\n")
    assert isinstance(errors[0], UndefinedLabelError)
    assert errors[0].line_number == 1


# ── 3. Etiqueta duplicada ─────────────────────────────────────────────────

def test_duplicate_label():
    errors = assemble_expecting_error("LOOP: NOP\nLOOP: NOP\nHLT\n")
    assert isinstance(errors[0], DuplicateLabelError)
    assert errors[0].line_number == 2


def test_duplicate_label_is_case_insensitive():
    # Las etiquetas se normalizan a mayúsculas, igual que los nemónicos.
    errors = assemble_expecting_error("loop: NOP\nLOOP: NOP\nHLT\n")
    assert isinstance(errors[0], DuplicateLabelError)


# ── 4. Operando fuera de rango ────────────────────────────────────────────

@pytest.mark.parametrize(
    "source", ["LDA 256\n", "LDA -1\n", "LDI A,#0x100\n", ".ORG 300\n", ".DB 999\n"]
)
def test_operand_out_of_range(source):
    errors = assemble_expecting_error(source)
    assert isinstance(errors[0], OperandRangeError)
    assert errors[0].line_number == 1


# ── 5. Conteo/forma de operandos ──────────────────────────────────────────

@pytest.mark.parametrize("source", ["LDA\nHLT\n", "JMP\nHLT\n", "LDI A\nHLT\n"])
def test_two_byte_instruction_without_operand(source):
    errors = assemble_expecting_error(source)
    assert isinstance(errors[0], OperandCountError)
    assert errors[0].line_number == 1


@pytest.mark.parametrize("source", ["ADD 5\nHLT\n", "HLT 0\n", "NOP 1\nHLT\n"])
def test_one_byte_instruction_with_operand(source):
    errors = assemble_expecting_error(source)
    assert isinstance(errors[0], OperandCountError)


def test_direct_mode_rejects_hash():
    errors = assemble_expecting_error("LDA #5\nHLT\n")
    assert isinstance(errors[0], OperandFormError)


def test_immediate_mode_requires_hash():
    # Confusión clásica inmediato-vs-directo: LDI A,5 debe fallar.
    errors = assemble_expecting_error("LDI A,5\nHLT\n")
    assert isinstance(errors[0], OperandFormError)


def test_too_many_operands():
    errors = assemble_expecting_error("LDA 200, 201\nHLT\n")
    assert isinstance(errors[0], OperandCountError)


# ── 6. Zona de programa ───────────────────────────────────────────────────

def test_instruction_beyond_program_zone():
    # A.6: instrucciones solo en 0x00-0xBF. .ORG 0xBF + 2 bytes se pasa.
    errors = assemble_expecting_error(".ORG 0xBF\nLDA 200\n")
    assert isinstance(errors[0], ProgramZoneError)
    assert errors[0].line_number == 2


def test_instruction_exactly_at_zone_edge_is_ok():
    # 0xBE-0xBF cabe justo: no debe fallar.
    result = assemble(".ORG 0xBE\nLDA 200\n")
    assert result.binary[0xBE] == 0x10


def test_db_in_data_zone_is_not_a_zone_error():
    # A.6: la separación es convención; .DB puede vivir donde sea.
    result = assemble(".ORG 0xCC\n.DB 4\n")
    assert result.binary[0xCC] == 4


def test_memory_overflow():
    errors = assemble_expecting_error(".ORG 0xFF\n.DB 1, 2\n")
    assert isinstance(errors[0], MemoryOverflowError)


# ── 7. Solape (peligro que introduce .ORG) ────────────────────────────────

def test_overlap_detected():
    errors = assemble_expecting_error(".ORG 0x00\nNOP\n.ORG 0x00\nNOP\n")
    assert isinstance(errors[0], OverlapError)


def test_backwards_org_without_overlap_is_legal():
    result = assemble(".ORG 0x10\nNOP\n.ORG 0x00\nNOP\n")
    assert result.binary[0x00] == 0x00 and result.binary[0x10] == 0x00


# ── Acumulación de errores ────────────────────────────────────────────────

def test_multiple_errors_reported_together():
    source = "HLT\nLDX 1\nNOP\nLDY 2\nNOP\nNOP\nLDZ 3\n"
    errors = assemble_expecting_error(source)
    assert len(errors) == 3
    assert [error.line_number for error in errors] == [2, 4, 7]


def test_errors_sorted_by_line_number():
    errors = assemble_expecting_error("NOP\nNOP\nLDZ 3\nLDX 1\n")
    numbers = [error.line_number for error in errors]
    assert numbers == sorted(numbers)


# ── Mensajes ──────────────────────────────────────────────────────────────

def test_error_message_includes_line_number_and_source():
    errors = assemble_expecting_error("NOP\nLDX 5\nHLT\n")
    text = str(errors[0])
    assert "línea 2" in text
    assert "LDX 5" in text


def test_label_colliding_with_mnemonic_rejected():
    errors = assemble_expecting_error("ADD: NOP\nHLT\n")
    assert errors[0].line_number == 1


def test_label_on_org_rejected():
    errors = assemble_expecting_error("INICIO: .ORG 0x10\nHLT\n")
    assert errors[0].line_number == 1
