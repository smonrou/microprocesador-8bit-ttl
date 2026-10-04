"""Source line -> ParsedLine.

Handles comment stripping, label extraction, mnemonic resolution, operand
parsing, and choosing the opcode from the operand SHAPES (x86 style since
2026-09-28: "MOV A,[200]", "MOV A,5" and "MOV [200],A" share the word MOV
and differ only in their operands).

ParsedLine.text keeps the raw source line untouched — the listing echoes it
verbatim rather than re-rendering it.
"""

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Tuple

from sim.isa import InstructionSpec

from .errors import (
    AssemblerError,
    ErrorCollector,
    InvalidLiteralError,
    OperandCountError,
    OperandFormError,
    UnknownMnemonicError,
)
from .mnemonics import (
    REGISTERS,
    SLOT_ADDRESS,
    SLOT_IMMEDIATE,
    SLOT_MEMORY,
    base_of,
    is_directive,
    is_mnemonic,
    lookup,
    operand_pattern,
    valid_forms_text,
)
from .numbers import looks_like_label, looks_like_number, parse_and_check

COMMENT_CHAR = ";"
LABEL_SUFFIX = ":"
IMMEDIATE_PREFIX = "#"     # old syntax, now rejected with a hint


class LineKind(Enum):
    EMPTY = auto()        # blank, comment-only, or label-only
    INSTRUCTION = auto()
    DIRECTIVE = auto()


class OperandForm(Enum):
    NUMBER = auto()           # 200        (bare: immediate, jump target, .DB)
    LABEL = auto()            # LOOP
    MEMORY_NUMBER = auto()    # [200]      (direct address)
    MEMORY_LABEL = auto()     # [DATO]
    REGISTER = auto()         # A, B


VALUE_FORMS = (OperandForm.NUMBER, OperandForm.LABEL)
MEMORY_FORMS = (OperandForm.MEMORY_NUMBER, OperandForm.MEMORY_LABEL)
LABEL_FORMS = (OperandForm.LABEL, OperandForm.MEMORY_LABEL)


@dataclass(frozen=True)
class Operand:
    form: OperandForm
    text: str                  # as written, for error messages
    value: Optional[int] = None    # set for the NUMBER forms
    name: Optional[str] = None     # normalized label or register name


@dataclass(frozen=True)
class ParsedLine:
    line_number: int           # 1-based
    text: str                  # raw source line, untouched
    kind: LineKind
    label: Optional[str] = None
    spec: Optional[InstructionSpec] = None
    directive: Optional[str] = None
    # For instructions: only the operand that becomes the second byte (the
    # register operands of MOV are encoded in the opcode and dropped here).
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

# A bracketed address is one token even with spaces inside ("[ 200 ]").
TOKEN_RE = re.compile(r"\[[^\]]*\]|,|[^\s,]+")


def strip_comment(line: str) -> str:
    index = line.find(COMMENT_CHAR)
    return line if index < 0 else line[:index]


def tokenize(line: str) -> List[str]:
    """Split into tokens, with commas as standalone tokens so every spacing
    variant collapses to one form:
        "MOV A,[200]"     -> ["MOV", "A", ",", "[200]"]
        "MOV A , [ 200 ]" -> ["MOV", "A", ",", "[ 200 ]"]
    """
    return TOKEN_RE.findall(strip_comment(line))


# ── Operand parsing ───────────────────────────────────────────────────────

def parse_operand(token: str, line_number: int, line_text: str) -> Operand:
    if token.startswith(IMMEDIATE_PREFIX):
        body = token[1:]
        raise OperandFormError(
            f"'#' ya no se usa (sintaxis x86): el inmediato se escribe tal cual "
            f"('{body}') y una dirección entre corchetes ('[{body}]')",
            line_number,
            line_text,
        )

    if token.upper() in REGISTERS:
        return Operand(form=OperandForm.REGISTER, text=token, name=token.upper())

    memory = token.startswith("[") and token.endswith("]") and len(token) >= 2
    body = token[1:-1].strip() if memory else token

    if memory and not body:
        raise InvalidLiteralError("dirección vacía entre '[ ]'", line_number, line_text)

    if looks_like_number(body):
        value = parse_and_check(body, line_number, line_text)
        form = OperandForm.MEMORY_NUMBER if memory else OperandForm.NUMBER
        return Operand(form=form, text=token, value=value)

    if looks_like_label(body):
        if memory and body.upper() in REGISTERS:
            raise OperandFormError(
                f"direccionamiento indirecto por registro no existe: '{token}'",
                line_number,
                line_text,
            )
        form = OperandForm.MEMORY_LABEL if memory else OperandForm.LABEL
        return Operand(form=form, text=token, name=body.upper())

    raise InvalidLiteralError(
        f"operando mal formado: '{token}'", line_number, line_text
    )


def _split_operand_tokens(tokens: List[str]) -> List[str]:
    """Drop the comma separators, keeping the operand tokens in order."""
    return [token for token in tokens if token != ","]


# ── Operand shapes -> opcode ──────────────────────────────────────────────

def _slot_accepts(slot: str, operand: Operand) -> bool:
    if slot == SLOT_MEMORY:
        return operand.form in MEMORY_FORMS
    if slot in (SLOT_IMMEDIATE, SLOT_ADDRESS):
        return operand.form in VALUE_FORMS
    # Any other slot is a literal register name ("A", "B").
    return operand.form == OperandForm.REGISTER and operand.name == slot


def _matches(spec: InstructionSpec, operands: Tuple[Operand, ...]) -> bool:
    pattern = operand_pattern(spec)
    return len(pattern) == len(operands) and all(
        _slot_accepts(slot, operand) for slot, operand in zip(pattern, operands)
    )


def select_form(
    base: str,
    forms: Tuple[InstructionSpec, ...],
    operands: Tuple[Operand, ...],
    line_number: int,
    line_text: str,
) -> InstructionSpec:
    """The one spec whose operand pattern the source operands fit.

    This is the only mapping asm/ adds on top of sim.isa: which operand
    shapes fill which pattern slot. The patterns themselves come from the
    frozen table (asm.mnemonics.operand_pattern).
    """
    for spec in forms:
        if _matches(spec, operands):
            return spec

    counts = sorted({len(operand_pattern(spec)) for spec in forms})
    if len(operands) not in counts:
        if counts == [0]:
            message = f"instrucción de 1 byte con operando: '{base}' no lleva operandos"
        elif not operands:
            message = f"instrucción de 2 bytes sin operando: '{base}' requiere {counts[0]}"
        else:
            message = (
                f"'{base}' admite {counts[0]} operando(s), se dieron {len(operands)}"
            )
        if len(forms) > 1:
            message += f"; formas válidas: {valid_forms_text(base)}"
        raise OperandCountError(message, line_number, line_text)

    if len(forms) > 1:
        written = f"{base} " + ",".join(operand.text for operand in operands)
        message = f"no existe '{written}'; formas válidas: {valid_forms_text(base)}"
    elif operand_pattern(forms[0]) == (SLOT_ADDRESS,):
        message = (
            f"'{base}' espera una dirección sin corchetes ni registro "
            f"(p. ej. '{base} LOOP')"
        )
    else:
        message = f"operandos no válidos para '{forms[0].mnemonic}'"
    raise OperandFormError(message, line_number, line_text)


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
                "'.ORG' requiere un literal numérico (sin etiquetas, corchetes ni registros)",
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
            if operand.form not in VALUE_FORMS:
                raise OperandFormError(
                    f"'.DB' solo admite números o etiquetas: '{operand.text}'",
                    line_number,
                    line_text,
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
        if label_text.upper() in REGISTERS:
            raise AssemblerError(
                f"la etiqueta '{label_text}' colisiona con un registro",
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

    forms = lookup(tokens[0])
    if not forms:
        raise UnknownMnemonicError(
            f"nemónico desconocido: '{tokens[0]}'", line_number, raw_line
        )

    base = base_of(forms[0])
    written = tuple(
        parse_operand(token, line_number, raw_line)
        for token in _split_operand_tokens(tokens[1:])
    )
    spec = select_form(base, forms, written, line_number, raw_line)
    # Registers live in the opcode; only the value/address becomes byte 2.
    operands = tuple(op for op in written if op.form != OperandForm.REGISTER)

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
