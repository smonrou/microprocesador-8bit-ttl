"""Numeric literal parsing — B.2 requires decimal, hex (0xFF and $FF) and
binary (0b1010).

Explicit regex per base, deliberately NOT int(text, 0): that would silently
accept octal (0o17) and underscores (1_0), neither of which is in the spec,
and its error text is useless for reporting.
"""

import re
from typing import Optional

from .errors import InvalidLiteralError, OperandRangeError

MIN_VALUE = 0
MAX_VALUE = 255

DECIMAL_RE = re.compile(r"^[+-]?[0-9]+$")
HEX_0X_RE = re.compile(r"^0[xX][0-9A-Fa-f]+$")
HEX_DOLLAR_RE = re.compile(r"^\$[0-9A-Fa-f]+$")
BINARY_RE = re.compile(r"^0[bB][01]+$")

LABEL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def looks_like_number(text: str) -> bool:
    return bool(
        DECIMAL_RE.match(text)
        or HEX_0X_RE.match(text)
        or HEX_DOLLAR_RE.match(text)
        or BINARY_RE.match(text)
    )


def looks_like_label(text: str) -> bool:
    return bool(LABEL_RE.match(text))


def parse_number(text: str, line_number: int, line_text: str = "") -> int:
    """Parse a literal in any supported base. Raises InvalidLiteralError.

    Signed decimals parse successfully here and fail later in the range
    check, so `-1` reports "operando fuera de rango" (the wording B.2 asks
    for) rather than a syntax error.
    """
    if DECIMAL_RE.match(text):
        return int(text, 10)
    if HEX_0X_RE.match(text):
        return int(text[2:], 16)
    if HEX_DOLLAR_RE.match(text):
        return int(text[1:], 16)
    if BINARY_RE.match(text):
        return int(text[2:], 2)
    raise InvalidLiteralError(
        f"literal numérico mal formado: '{text}'", line_number, line_text
    )


def check_range(
    value: int, line_number: int, line_text: str = "", what: str = "operando"
) -> int:
    if value < MIN_VALUE or value > MAX_VALUE:
        raise OperandRangeError(
            f"{what} fuera de rango: {value} (válido {MIN_VALUE}–{MAX_VALUE})",
            line_number,
            line_text,
        )
    return value


def parse_and_check(
    text: str, line_number: int, line_text: str = "", what: str = "operando"
) -> int:
    return check_range(parse_number(text, line_number, line_text), line_number, line_text, what)
