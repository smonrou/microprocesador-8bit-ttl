import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Tuple

from .isa import InstructionSpec

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
IMMEDIATE_PREFIX = "#"     # sintaxis vieja, se rechaza con una pista


class LineKind(Enum):
    EMPTY = auto()        # vacía, comentario o solo etiqueta
    INSTRUCTION = auto()
    DIRECTIVE = auto()    # .ORG o .DB


class OperandForm(Enum):
    NUMBER = auto()           # 200
    LABEL = auto()            # LOOP
    MEMORY_NUMBER = auto()    # [200]
    MEMORY_LABEL = auto()     # [DATO]
    REGISTER = auto()         # A, B


VALUE_FORMS = (OperandForm.NUMBER, OperandForm.LABEL)
MEMORY_FORMS = (OperandForm.MEMORY_NUMBER, OperandForm.MEMORY_LABEL)
LABEL_FORMS = (OperandForm.LABEL, OperandForm.MEMORY_LABEL)           # se resuelven en la pasada 2


@dataclass(frozen=True)
class Operand:
    form: OperandForm
    text: str                  # tal cual se escribió
    value: Optional[int] = None
    name: Optional[str] = None     # etiqueta o registro, en mayúsculas


@dataclass(frozen=True)
class ParsedLine:
    line_number: int
    text: str
    kind: LineKind
    label: Optional[str] = None
    spec: Optional[InstructionSpec] = None
    directive: Optional[str] = None
    # en instrucciones los registros no van, ya están en el opcode
    operands: Tuple[Operand, ...] = ()

    @property
    def size(self) -> int:
        if self.kind == LineKind.INSTRUCTION:
            return self.spec.length
        if self.kind == LineKind.DIRECTIVE and self.directive == ".DB":
            return len(self.operands)
        return 0  # EMPTY y .ORG


# lo que va entre corchetes es un solo token, aunque tenga espacios
TOKEN_RE = re.compile(r"\[[^\]]*\]|,|[^\s,]+")


def strip_comment(line: str) -> str:
    index = line.find(COMMENT_CHAR)
    return line if index < 0 else line[:index]


def tokenize(line: str) -> List[str]:
    """"MOV A , [ 200 ]" -> ["MOV", "A", ",", "[ 200 ]"]"""
    return TOKEN_RE.findall(strip_comment(line))


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

    # "[A]" parece etiqueta pero sería indirecto por registro, que no existe
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
    return [token for token in tokens if token != ","]


def _slot_accepts(slot: str, operand: Operand) -> bool:
    if slot == SLOT_MEMORY:
        return operand.form in MEMORY_FORMS
    if slot in (SLOT_IMMEDIATE, SLOT_ADDRESS):
        return operand.form in VALUE_FORMS
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
    """Devuelve el spec cuyo patrón encaja con los operandos."""
    for spec in forms:
        if _matches(spec, operands):
            return spec

    # ninguna encajó, se arma el mensaje de error
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

    # cantidad correcta pero tipo no: "MOV B,A", "JNZ [LOOP]"
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
    # .ORG no admite etiquetas, el puntero se necesita en la pasada 1
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
    # los registros ya van en el opcode
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
    collector = ErrorCollector()
    parsed_lines: List[ParsedLine] = []

    for index, raw_line in enumerate(source_text.splitlines(), start=1):
        try:
            parsed_lines.append(parse_line(raw_line, index))
        except AssemblerError as error:
            collector.add(error)

    collector.raise_if_any()
    return parsed_lines
