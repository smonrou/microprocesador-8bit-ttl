"""Source line -> ParsedLine.

Handles comment stripping, label extraction, mnemonic resolution (longest
match first, so the two-word "LDI A" / "LDI B" work), operand parsing, and
validation that the operand FORM matches the instruction's Mode.

ParsedLine.text keeps the raw source line untouched — the listing echoes it
verbatim rather than re-rendering it.
"""

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Tuple

from sim.isa import InstructionSpec, Mode

from .errors import (
    AssemblerError,
    ErrorCollector,
    InvalidLiteralError,
    OperandCountError,
    OperandFormError,
    UnknownMnemonicError,
)
from .mnemonics import (
    MAX_MNEMONIC_WORDS,
    completion_hint,
    is_directive,
    is_mnemonic,
    lookup,
)
from .numbers import looks_like_label, looks_like_number, parse_and_check

COMMENT_CHAR = ";"
LABEL_SUFFIX = ":"


class LineKind(Enum):
    EMPTY = auto()        # blank, comment-only, or label-only
    INSTRUCTION = auto()
    DIRECTIVE = auto()


class OperandForm(Enum):
    NUMBER = auto()
    LABEL = auto()
    IMMEDIATE_NUMBER = auto()
    IMMEDIATE_LABEL = auto()


IMMEDIATE_FORMS = (OperandForm.IMMEDIATE_NUMBER, OperandForm.IMMEDIATE_LABEL)
LABEL_FORMS = (OperandForm.LABEL, OperandForm.IMMEDIATE_LABEL)


@dataclass(frozen=True)
class Operand:
    form: OperandForm
    text: str                  # as written, for error messages
    value: Optional[int] = None    # set for the NUMBER forms
    name: Optional[str] = None     # normalized label, set for the LABEL forms


@dataclass(frozen=True)
class ParsedLine:
    line_number: int           # 1-based
    text: str                  # raw source line, untouched
    kind: LineKind
    label: Optional[str] = None
    spec: Optional[InstructionSpec] = None
    directive: Optional[str] = None
    operands: Tuple[Operand, ...] = ()

    @property
    def size(self) -> int:
        """Bytes this line emits. Pass 1 needs only this."""
        if self.kind == LineKind.INSTRUCTION:
            return self.spec.length
        if self.kind == LineKind.DIRECTIVE and self.directive == ".DB":
            return len(self.operands)
        return 0  # EMPTY, and .ORG (moves the pointer, emits nothing)


# ── Tokenizing ────────────────────────────────────────────────────────────

TOKEN_RE = re.compile(r",|[^\s,]+")


def strip_comment(line: str) -> str:
    index = line.find(COMMENT_CHAR)
    return line if index < 0 else line[:index]


def tokenize(line: str) -> List[str]:
    """Split into tokens, with commas as standalone tokens so every spacing
    variant collapses to one form:
        "LDI A,#12"    -> ["LDI", "A", ",", "#12"]
        "LDI A , #12"  -> ["LDI", "A", ",", "#12"]
    """
    return TOKEN_RE.findall(strip_comment(line))


# ── Operand parsing ───────────────────────────────────────────────────────

def parse_operand(token: str, line_number: int, line_text: str) -> Operand:
    immediate = token.startswith("#")
    body = token[1:] if immediate else token

    if not body:
        raise InvalidLiteralError(
            f"operando vacío tras '#'", line_number, line_text
        )

    if looks_like_number(body):
        value = parse_and_check(body, line_number, line_text)
        form = OperandForm.IMMEDIATE_NUMBER if immediate else OperandForm.NUMBER
        return Operand(form=form, text=token, value=value)

    if looks_like_label(body):
        form = OperandForm.IMMEDIATE_LABEL if immediate else OperandForm.LABEL
        return Operand(form=form, text=token, name=body.upper())

    raise InvalidLiteralError(
        f"operando mal formado: '{token}'", line_number, line_text
    )


def _split_operand_tokens(tokens: List[str]) -> List[str]:
    """Drop the comma separators, keeping the operand tokens in order."""
    return [token for token in tokens if token != ","]


# ── Form <-> Mode validation ──────────────────────────────────────────────

def validate_instruction_operands(
    spec: InstructionSpec,
    operands: Tuple[Operand, ...],
    line_number: int,
    line_text: str,
) -> None:
    """The only mapping asm/ adds on top of sim.isa: which operand shapes a
    given addressing Mode accepts."""
    if spec.mode in (Mode.NONE, Mode.IMPLICIT):
        if operands:
            raise OperandCountError(
                f"instrucción de 1 byte con operando: '{spec.mnemonic}' no lleva operandos",
                line_number,
                line_text,
            )
        return

    # DIRECT and IMMEDIATE both take exactly one operand.
    if not operands:
        raise OperandCountError(
            f"instrucción de 2 bytes sin operando: '{spec.mnemonic}' requiere uno",
            line_number,
            line_text,
        )
    if len(operands) > 1:
        raise OperandCountError(
            f"'{spec.mnemonic}' admite un solo operando, se dieron {len(operands)}",
            line_number,
            line_text,
        )

    operand = operands[0]
    if spec.mode == Mode.IMMEDIATE and operand.form not in IMMEDIATE_FORMS:
        raise OperandFormError(
            f"el modo inmediato requiere '#': escriba '{spec.mnemonic},#{operand.text}'",
            line_number,
            line_text,
        )
    if spec.mode == Mode.DIRECT and operand.form in IMMEDIATE_FORMS:
        raise OperandFormError(
            f"el modo directo no admite '#': '{spec.mnemonic}' espera una dirección",
            line_number,
            line_text,
        )


def validate_directive_operands(
    directive: str,
    operands: Tuple[Operand, ...],
    line_number: int,
    line_text: str,
) -> None:
    if directive == ".ORG":
        if len(operands) != 1:
            raise OperandCountError(
                f"'.ORG' requiere exactamente una dirección", line_number, line_text
            )
        if operands[0].form != OperandForm.NUMBER:
            raise OperandFormError(
                "'.ORG' requiere un literal numérico (no etiquetas ni '#')",
                line_number,
                line_text,
            )
        return

    if directive == ".DB":
        if not operands:
            raise OperandCountError(
                "'.DB' requiere al menos un valor", line_number, line_text
            )
        for operand in operands:
            if operand.form in IMMEDIATE_FORMS:
                raise OperandFormError(
                    f"'.DB' no admite '#': '{operand.text}'", line_number, line_text
                )


# ── Line parsing ──────────────────────────────────────────────────────────

def parse_line(raw_line: str, line_number: int) -> ParsedLine:
    tokens = tokenize(raw_line)

    label = None
    if tokens and tokens[0].endswith(LABEL_SUFFIX) and len(tokens[0]) > 1:
        label_text = tokens[0][:-1]
        if not looks_like_label(label_text):
            raise AssemblerError(
                f"etiqueta mal formada: '{label_text}'", line_number, raw_line
            )
        if is_mnemonic(label_text):
            raise AssemblerError(
                f"la etiqueta '{label_text}' colisiona con un nemónico",
                line_number,
                raw_line,
            )
        label = label_text.upper()
        tokens = tokens[1:]

    if not tokens:
        return ParsedLine(
            line_number=line_number, text=raw_line, kind=LineKind.EMPTY, label=label
        )

    # Directive?
    if is_directive(tokens[0]):
        directive = tokens[0].upper()
        if directive == ".ORG" and label is not None:
            raise AssemblerError(
                "no se admite etiqueta en una línea '.ORG' (ambigua: ¿antes o "
                "después del salto de puntero?)",
                line_number,
                raw_line,
            )
        operand_tokens = _split_operand_tokens(tokens[1:])
        operands = tuple(
            parse_operand(token, line_number, raw_line) for token in operand_tokens
        )
        validate_directive_operands(directive, operands, line_number, raw_line)
        return ParsedLine(
            line_number=line_number,
            text=raw_line,
            kind=LineKind.DIRECTIVE,
            label=label,
            directive=directive,
            operands=operands,
        )

    # Mnemonic: longest match first, so "LDI A" wins over a bare "LDI".
    spec = None
    consumed = 0
    non_comma = _split_operand_tokens(tokens)
    for word_count in range(min(MAX_MNEMONIC_WORDS, len(non_comma)), 0, -1):
        candidate = " ".join(non_comma[:word_count])
        found = lookup(candidate)
        if found is not None:
            spec = found
            consumed = word_count
            break

    if spec is None:
        hint = completion_hint(tokens[0])
        message = hint if hint else f"nemónico desconocido: '{tokens[0]}'"
        raise UnknownMnemonicError(message, line_number, raw_line)

    operand_tokens = non_comma[consumed:]
    operands = tuple(
        parse_operand(token, line_number, raw_line) for token in operand_tokens
    )
    validate_instruction_operands(spec, operands, line_number, raw_line)

    return ParsedLine(
        line_number=line_number,
        text=raw_line,
        kind=LineKind.INSTRUCTION,
        label=label,
        spec=spec,
        operands=operands,
    )


def parse_source(source_text: str) -> List[ParsedLine]:
    """Parse every line, collecting all errors before raising (phase 1 of
    three; see ErrorCollector docstring)."""
    collector = ErrorCollector()
    parsed_lines: List[ParsedLine] = []

    for index, raw_line in enumerate(source_text.splitlines(), start=1):
        try:
            parsed_lines.append(parse_line(raw_line, index))
        except AssemblerError as error:
            collector.add(error)

    collector.raise_if_any()
    return parsed_lines
