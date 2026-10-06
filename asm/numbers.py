"""Lectura de literales numéricos. B.2 exige decimal, hexadecimal (0xFF y
$FF) y binario (0b1010).

Se usa una expresión regular explícita por cada base, y a propósito NO
int(text, 0): esa función aceptaría en silencio octal (0o17) y guiones bajos
(1_0), que no están en el spec, y su mensaje de error no sirve para
reportarle nada útil al usuario.

Todo valor debe caber en un byte: 0..255.
"""

import re
from typing import Optional

from .errors import InvalidLiteralError, OperandRangeError

# Rango de un byte sin signo.
MIN_VALUE = 0
MAX_VALUE = 255

# Una regex por formato. ^ y $ obligan a que coincida el texto completo.
DECIMAL_RE = re.compile(r"^[+-]?[0-9]+$")        # 12, +12, -1 (el signo se acepta aquí y se rechaza en el rango)
HEX_0X_RE = re.compile(r"^0[xX][0-9A-Fa-f]+$")   # 0xC8, 0Xff
HEX_DOLLAR_RE = re.compile(r"^\$[0-9A-Fa-f]+$")  # $C8
BINARY_RE = re.compile(r"^0[bB][01]+$")          # 0b1010

# Etiqueta: empieza con letra o '_', sigue con letras, dígitos o '_'.
# Ejemplos válidos: LOOP, dato_1, _fin. Inválidos: 1LOOP, fin-2.
LABEL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def looks_like_number(text: str) -> bool:
    """¿El texto tiene forma de número en alguna de las bases admitidas?"""
    return bool(
        DECIMAL_RE.match(text)
        or HEX_0X_RE.match(text)
        or HEX_DOLLAR_RE.match(text)
        or BINARY_RE.match(text)
    )


def looks_like_label(text: str) -> bool:
    """¿El texto tiene forma de nombre de etiqueta?"""
    return bool(LABEL_RE.match(text))


def parse_number(text: str, line_number: int, line_text: str = "") -> int:
    """Convierte un literal en cualquier base admitida a int. Lanza
    InvalidLiteralError si no tiene ninguna forma válida.

    Los decimales con signo se leen bien aquí y fallan después en el control
    de rango, para que `-1` se reporte como "operando fuera de rango" (lo que
    pide B.2) y no como un error de sintaxis.
    """
    if DECIMAL_RE.match(text):
        return int(text, 10)
    if HEX_0X_RE.match(text):
        return int(text[2:], 16)   # se quita el prefijo "0x"
    if HEX_DOLLAR_RE.match(text):
        return int(text[1:], 16)   # se quita el prefijo "$"
    if BINARY_RE.match(text):
        return int(text[2:], 2)    # se quita el prefijo "0b"
    raise InvalidLiteralError(
        f"literal numérico mal formado: '{text}'", line_number, line_text
    )


def check_range(
    value: int, line_number: int, line_text: str = "", what: str = "operando"
) -> int:
    """Devuelve el valor si cabe en un byte (0..255); si no, lanza
    OperandRangeError. `what` solo cambia la palabra del mensaje."""
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
    """Atajo: leer el literal y comprobar su rango en un solo paso."""
    return check_range(parse_number(text, line_number, line_text), line_number, line_text, what)
