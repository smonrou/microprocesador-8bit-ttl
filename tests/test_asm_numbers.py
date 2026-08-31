"""B.2: aceptar decimal (12), hexadecimal (0xFF o $FF) y binario (0b1010)."""

import pytest

from asm.errors import InvalidLiteralError, OperandRangeError
from asm.numbers import (
    check_range,
    looks_like_label,
    looks_like_number,
    parse_and_check,
    parse_number,
)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("0", 0),
        ("12", 12),
        ("255", 255),
        ("+7", 7),
        ("0xFF", 255),
        ("0XFF", 255),
        ("0xff", 255),
        ("0x0C", 12),
        ("$FF", 255),
        ("$ff", 255),
        ("$C8", 200),
        ("0b1010", 10),
        ("0B1010", 10),
        ("0b11111111", 255),
    ],
)
def test_parse_valid_literals(text, expected):
    assert parse_number(text, line_number=1) == expected


@pytest.mark.parametrize(
    "text",
    ["0x", "$", "0b", "0b102", "12a", "--5", "", "0xG1", "1_0", "0o17", "#5", "12.5"],
)
def test_parse_invalid_literals(text):
    with pytest.raises(InvalidLiteralError):
        parse_number(text, line_number=3)


def test_invalid_literal_carries_line_number():
    with pytest.raises(InvalidLiteralError) as exc:
        parse_number("0xZZ", line_number=42)
    assert exc.value.line_number == 42


@pytest.mark.parametrize("value", [0, 1, 128, 255])
def test_range_accepts_valid(value):
    assert check_range(value, line_number=1) == value


@pytest.mark.parametrize("value", [-1, -256, 256, 300, 1000])
def test_range_rejects_out_of_bounds(value):
    with pytest.raises(OperandRangeError):
        check_range(value, line_number=5)


def test_negative_decimal_reports_range_not_syntax():
    # Se parsea bien, falla en el rango: el spec pide "operando fuera de
    # rango (>255 o negativo)", no un error de sintaxis.
    assert parse_number("-1", line_number=1) == -1
    with pytest.raises(OperandRangeError):
        parse_and_check("-1", line_number=1)


def test_256_reports_range():
    with pytest.raises(OperandRangeError):
        parse_and_check("256", line_number=1)


@pytest.mark.parametrize("text", ["12", "0xFF", "$FF", "0b1010", "-1"])
def test_looks_like_number_true(text):
    assert looks_like_number(text)


@pytest.mark.parametrize("text", ["LOOP", "_start", "a1", "0x"])
def test_looks_like_number_false(text):
    assert not looks_like_number(text)


@pytest.mark.parametrize("text", ["LOOP", "loop", "_start", "A1", "CUATRO"])
def test_looks_like_label_true(text):
    assert looks_like_label(text)


@pytest.mark.parametrize("text", ["12", "0xFF", "1abc", "-x", ""])
def test_looks_like_label_false(text):
    assert not looks_like_label(text)
