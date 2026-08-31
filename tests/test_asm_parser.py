"""Sintaxis de B.2: comentarios, etiquetas, mayúsculas indiferentes,
LDI A vs LDI B, variantes de espaciado."""

import pytest

from asm.parser import (
    LineKind,
    OperandForm,
    parse_line,
    parse_source,
    strip_comment,
    tokenize,
)


def parse_one(text):
    return parse_line(text, line_number=1)


# ── Comentarios y líneas vacías ───────────────────────────────────────────

@pytest.mark.parametrize(
    "line,expected",
    [
        ("LDA 200 ; carga", "LDA 200 "),
        ("; solo comentario", ""),
        ("LDA 200", "LDA 200"),
        (";", ""),
    ],
)
def test_strip_comment(line, expected):
    assert strip_comment(line) == expected


@pytest.mark.parametrize("line", ["", "   ", "; comentario", "\t", "   ; con sangría"])
def test_empty_lines(line):
    assert parse_one(line).kind == LineKind.EMPTY


def test_label_alone_is_empty_but_keeps_label():
    parsed = parse_one("LOOP:")
    assert parsed.kind == LineKind.EMPTY
    assert parsed.label == "LOOP"
    assert parsed.size == 0


# ── Mnemónicos ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("text", ["lda 200", "LDA 200", "LdA 200", "\tLDA\t200"])
def test_mnemonics_case_and_whitespace_insensitive(text):
    parsed = parse_one(text)
    assert parsed.kind == LineKind.INSTRUCTION
    assert parsed.spec.mnemonic == "LDA"
    assert parsed.operands[0].value == 200


@pytest.mark.parametrize(
    "text,expected_opcode",
    [
        ("LDI A,#12", 0x3),
        ("LDI B,#12", 0x4),
        ("ldi a,#12", 0x3),
        ("ldi b,#12", 0x4),
    ],
)
def test_ldi_a_vs_ldi_b(text, expected_opcode):
    assert parse_one(text).spec.opcode == expected_opcode


@pytest.mark.parametrize(
    "text", ["LDI A,#12", "LDI A , #12", "LDI A #12", "LDI  A,  #12", "ldi a ,#12"]
)
def test_comma_spacing_variants_collapse(text):
    parsed = parse_one(text)
    assert parsed.spec.opcode == 0x3
    assert parsed.operands[0].value == 12
    assert parsed.operands[0].form == OperandForm.IMMEDIATE_NUMBER


def test_tokenize_makes_commas_standalone():
    assert tokenize("LDI A,#12") == ["LDI", "A", ",", "#12"]
    assert tokenize("LDI A , #12") == ["LDI", "A", ",", "#12"]


# ── Etiquetas ─────────────────────────────────────────────────────────────

def test_label_with_instruction():
    parsed = parse_one("LOOP: LDA 200")
    assert parsed.label == "LOOP"
    assert parsed.spec.mnemonic == "LDA"


def test_labels_are_normalized_to_uppercase():
    assert parse_one("loop: LDA 200").label == "LOOP"


def test_label_on_db():
    parsed = parse_one("CUATRO: .DB 4")
    assert parsed.label == "CUATRO"
    assert parsed.directive == ".DB"
    assert parsed.size == 1


# ── Operandos ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "text,form",
    [
        ("LDA 200", OperandForm.NUMBER),
        ("LDA CUATRO", OperandForm.LABEL),
        ("LDI A,#12", OperandForm.IMMEDIATE_NUMBER),
        ("LDI A,#CUATRO", OperandForm.IMMEDIATE_LABEL),
    ],
)
def test_operand_forms(text, form):
    assert parse_one(text).operands[0].form == form


@pytest.mark.parametrize(
    "text,value", [("LDA 200", 200), ("LDA 0xC8", 200), ("LDA $C8", 200)]
)
def test_operand_bases(text, value):
    assert parse_one(text).operands[0].value == value


def test_label_operand_normalized_to_uppercase():
    assert parse_one("JNZ loop").operands[0].name == "LOOP"


# ── Tamaños (lo único que necesita la pasada 1) ───────────────────────────

@pytest.mark.parametrize(
    "text,size",
    [
        ("NOP", 1),
        ("ADD", 1),
        ("HLT", 1),
        ("OUT", 1),
        ("LDA 200", 2),
        ("LDI A,#3", 2),
        ("JNZ LOOP", 2),
        (".ORG 204", 0),
        (".DB 4", 1),
        (".DB 1,2,3", 3),
        ("; comentario", 0),
    ],
)
def test_line_sizes(text, size):
    assert parse_one(text).size == size


# ── Directivas ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("text", [".ORG 204", ".org 204", ".ORG 0xCC", ".ORG $CC"])
def test_org_case_insensitive_and_all_bases(text):
    parsed = parse_one(text)
    assert parsed.directive == ".ORG"
    assert parsed.operands[0].value == 204


def test_db_multiple_values():
    parsed = parse_one(".DB 1, 2, 0xFF")
    assert [op.value for op in parsed.operands] == [1, 2, 255]


# ── Fuente completa ───────────────────────────────────────────────────────

def test_parse_source_keeps_raw_text_and_line_numbers():
    source = "; cabecera\nLOOP: LDA 200   ; con comentario\n      HLT\n"
    lines = parse_source(source)
    assert [line.line_number for line in lines] == [1, 2, 3]
    assert lines[1].text == "LOOP: LDA 200   ; con comentario"


def test_crlf_line_endings_parse_identically():
    # Riesgo real en Windows: el fuente puede venir con \r\n.
    lf = parse_source("LDA 200\nHLT\n")
    crlf = parse_source("LDA 200\r\nHLT\r\n")
    assert [line.spec.mnemonic for line in lf] == [line.spec.mnemonic for line in crlf]
    assert [line.size for line in lf] == [line.size for line in crlf]
