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

COMMENT_CHAR = ";"         # todo lo que sigue a ';' es comentario
LABEL_SUFFIX = ":"         # "LOOP:" define la etiqueta LOOP
IMMEDIATE_PREFIX = "#"     # sintaxis antigua, ahora se rechaza con una pista


class LineKind(Enum):
    """Qué tipo de línea es."""
    EMPTY = auto()        # vacía, solo comentario, o solo etiqueta
    INSTRUCTION = auto()  # MOV, ADD, JNZ, ...
    DIRECTIVE = auto()    # .ORG o .DB


class OperandForm(Enum):
    """La forma en que se escribió un operando."""
    NUMBER = auto()           # 200        (sin corchetes: inmediato, destino de salto, .DB)
    LABEL = auto()            # LOOP
    MEMORY_NUMBER = auto()    # [200]      (dirección directa)
    MEMORY_LABEL = auto()     # [DATO]
    REGISTER = auto()         # A, B


# Agrupaciones de formas que se usan para comparar con los slots del patrón.
VALUE_FORMS = (OperandForm.NUMBER, OperandForm.LABEL)                 # valor "desnudo"
MEMORY_FORMS = (OperandForm.MEMORY_NUMBER, OperandForm.MEMORY_LABEL)  # entre corchetes
LABEL_FORMS = (OperandForm.LABEL, OperandForm.MEMORY_LABEL)           # hay que resolver en la pasada 2


@dataclass(frozen=True)
class Operand:
    """Un operando ya analizado. frozen=True: inmutable una vez creado."""
    form: OperandForm
    text: str                  # tal como se escribió, para los mensajes de error
    value: Optional[int] = None    # se llena en las formas NUMBER
    name: Optional[str] = None     # nombre de etiqueta o registro, en mayúsculas


@dataclass(frozen=True)
class ParsedLine:
    """Resultado de analizar una línea del fuente."""
    line_number: int           # empieza en 1
    text: str                  # línea original, sin tocar
    kind: LineKind
    label: Optional[str] = None             # etiqueta definida en esta línea, si hay
    spec: Optional[InstructionSpec] = None  # instrucción elegida (solo INSTRUCTION)
    directive: Optional[str] = None         # ".ORG" o ".DB" (solo DIRECTIVE)
    # En instrucciones: solo el operando que se convierte en el segundo byte
    # (los registros de MOV ya van codificados en el opcode y aquí se quitan).
    operands: Tuple[Operand, ...] = ()

    @property
    def size(self) -> int:
        """Cuántos bytes emite esta línea. Es lo único que necesita la pasada 1."""
        if self.kind == LineKind.INSTRUCTION:
            return self.spec.length            # 1 o 2, según la tabla de la ISA
        if self.kind == LineKind.DIRECTIVE and self.directive == ".DB":
            return len(self.operands)          # un byte por valor
        return 0  # EMPTY, y .ORG (mueve el puntero, no emite nada)


# ── Separación en tokens ──────────────────────────────────────────────────

# Una dirección entre corchetes es un solo token aunque tenga espacios
TOKEN_RE = re.compile(r"\[[^\]]*\]|,|[^\s,]+")


def strip_comment(line: str) -> str:
    """Quita desde el primer ';' hasta el final de la línea."""
    index = line.find(COMMENT_CHAR)
    return line if index < 0 else line[:index]


def tokenize(line: str) -> List[str]:
    """Divide en tokens, con las comas como tokens sueltos, para que todas
    las variantes de espaciado queden iguales:
        "MOV A,[200]"     -> ["MOV", "A", ",", "[200]"]
        "MOV A , [ 200 ]" -> ["MOV", "A", ",", "[ 200 ]"]
    """
    return TOKEN_RE.findall(strip_comment(line))


# Análisis de operandos

def parse_operand(token: str, line_number: int, line_text: str) -> Operand:
    """Clasifica un token en una de las formas de OperandForm.

    Orden de las comprobaciones:
      1. '#' delante -> error (sintaxis antigua) con la forma correcta.
      2. Es A o B    -> REGISTER.
      3. Si va entre corchetes, se trabaja con lo de dentro.
      4. Número      -> NUMBER / MEMORY_NUMBER (ya comprobado 0..255).
      5. Etiqueta    -> LABEL / MEMORY_LABEL (se resuelve en la pasada 2).
      6. Nada de lo anterior -> operando mal formado.
    """
    # 1. El '#' de la sintaxis vieja: se explica cómo escribirlo ahora.
    if token.startswith(IMMEDIATE_PREFIX):
        body = token[1:]
        raise OperandFormError(
            f"'#' ya no se usa (sintaxis x86): el inmediato se escribe tal cual "
            f"('{body}') y una dirección entre corchetes ('[{body}]')",
            line_number,
            line_text,
        )

    # Registro.
    if token.upper() in REGISTERS:
        return Operand(form=OperandForm.REGISTER, text=token, name=token.upper())

    # Si tiene corchetes entonces es acceso a memoria; body = el interior.
    memory = token.startswith("[") and token.endswith("]") and len(token) >= 2
    body = token[1:-1].strip() if memory else token

    if memory and not body:
        raise InvalidLiteralError("dirección vacía entre '[ ]'", line_number, line_text)

    # Número (en cualquier base admitida).
    if looks_like_number(body):
        value = parse_and_check(body, line_number, line_text)
        form = OperandForm.MEMORY_NUMBER if memory else OperandForm.NUMBER
        return Operand(form=form, text=token, value=value)

    # Etiqueta. "[A]" tiene forma de etiqueta pero sería direccionamiento indirecto por registro, que esta ISA no tiene.
    if looks_like_label(body):
        if memory and body.upper() in REGISTERS:
            raise OperandFormError(
                f"direccionamiento indirecto por registro no existe: '{token}'",
                line_number,
                line_text,
            )
        form = OperandForm.MEMORY_LABEL if memory else OperandForm.LABEL
        return Operand(form=form, text=token, name=body.upper())

    # Ni número ni etiqueta.
    raise InvalidLiteralError(
        f"operando mal formado: '{token}'", line_number, line_text
    )


def _split_operand_tokens(tokens: List[str]) -> List[str]:
    """Quita las comas separadoras y deja los operandos en orden."""
    return [token for token in tokens if token != ","]


# ── Forma de los operandos -> opcode ──────────────────────────────────────

def _slot_accepts(slot: str, operand: Operand) -> bool:
    """¿Este operando encaja en este slot del patrón?"""
    if slot == SLOT_MEMORY:
        # "[DIR]" acepta [200] o [DATO].
        return operand.form in MEMORY_FORMS
    if slot in (SLOT_IMMEDIATE, SLOT_ADDRESS):
        # "INM" y "DIR" aceptan un valor sin corchetes: 5, 200 o LOOP.
        return operand.form in VALUE_FORMS
    # Cualquier otro slot es el nombre literal de un registro ("A", "B"):
    # tiene que ser ESE registro.
    return operand.form == OperandForm.REGISTER and operand.name == slot


def _matches(spec: InstructionSpec, operands: Tuple[Operand, ...]) -> bool:
    """¿Los operandos escritos encajan, uno por uno, con el patrón del spec?"""
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
    """Devuelve el único spec cuyo patrón encaja con los operandos escritos.

    Es lo único que asm/ añade por encima de sim.isa: qué forma de operando
    llena cada slot del patrón. Los patrones mismos salen de la tabla
    congelada (asm.mnemonics.operand_pattern).

    Ej.: base="MOV", operandos (REGISTER A, MEMORY_NUMBER 200) -> recorre las
    5 formas de MOV y solo "MOV A,[dir]" encaja.
    """
    # Caso normal: se prueban las formas en orden y se devuelve la primera
    # que encaja (nunca encajan dos, porque los patrones son distintos).
    for spec in forms:
        if _matches(spec, operands):
            return spec

    # Ninguna encajó: de aquí en adelante solo se arma el mensaje de error
    # más útil posible.

    # Error de CANTIDAD: se dieron más o menos operandos de los que acepta
    # cualquiera de las formas.
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

    # Error de FORMA: la cantidad es correcta pero el tipo no (p. ej.
    # "MOV B,A" o "JNZ [LOOP]").
    if len(forms) > 1:
        written = f"{base} " + ",".join(operand.text for operand in operands)
        message = f"no existe '{written}'; formas válidas: {valid_forms_text(base)}"
    elif operand_pattern(forms[0]) == (SLOT_ADDRESS,):
        # Saltos: el error típico es ponerle corchetes al destino.
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
    """Comprueba los operandos de .ORG y .DB. No devuelve nada: si algo está
    mal, lanza el error correspondiente."""
    # .ORG: exactamente un número literal. No se permite etiqueta porque el
    # puntero tiene que conocerse ya en la pasada 1.
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

    # .DB: uno o más valores, cada uno número o etiqueta (una etiqueta en
    # .DB guarda su dirección como dato).
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


# ── Análisis de una línea ─────────────────────────────────────────────────

def parse_line(raw_line: str, line_number: int) -> ParsedLine:
    """Analiza una línea completa. Pasos: tokens -> etiqueta (opcional) ->
    directiva o instrucción -> operandos."""
    tokens = tokenize(raw_line)

    # Etiqueta: el primer token termina en ':' ("LOOP:").
    label = None
    if tokens and tokens[0].endswith(LABEL_SUFFIX) and len(tokens[0]) > 1:
        label_text = tokens[0][:-1]   # sin los dos puntos
        if not looks_like_label(label_text):
            raise AssemblerError(
                f"etiqueta mal formada: '{label_text}'", line_number, raw_line
            )
        # No puede llamarse como una instrucción ni como un registro, porque
        # luego sería ambiguo al usarla como operando.
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
        label = label_text.upper()   # las etiquetas no distinguen mayúsculas
        tokens = tokens[1:]

    # Nada más en la línea (vacía, comentario o solo etiqueta).
    if not tokens:
        return ParsedLine(
            line_number=line_number, text=raw_line, kind=LineKind.EMPTY, label=label
        )

    # ¿Directiva?
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

    # Si no es directiva, tiene que ser instrucción: se buscan sus formas.
    forms = lookup(tokens[0])
    if not forms:
        raise UnknownMnemonicError(
            f"nemónico desconocido: '{tokens[0]}'", line_number, raw_line
        )

    base = base_of(forms[0])
    # Operandos tal como se escribieron (incluidos los registros).
    written = tuple(
        parse_operand(token, line_number, raw_line)
        for token in _split_operand_tokens(tokens[1:])
    )
    # La forma de esos operandos decide el opcode.
    spec = select_form(base, forms, written, line_number, raw_line)
    # Los registros ya van en el opcode; solo el valor/dirección pasa a ser
    # el byte 2. Ej.: "MOV A,[200]" -> se guarda solo [200].
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
    """Analiza todas las líneas y junta todos los errores antes de lanzarlos
    (fase 1 de tres; ver el docstring de ErrorCollector)."""
    collector = ErrorCollector()
    parsed_lines: List[ParsedLine] = []

    # enumerate(..., start=1): los números de línea empiezan en 1, como en
    # el editor.
    for index, raw_line in enumerate(source_text.splitlines(), start=1):
        try:
            parsed_lines.append(parse_line(raw_line, index))
        except AssemblerError as error:
            # Se anota el error y se sigue con la siguiente línea.
            collector.add(error)

    collector.raise_if_any()
    return parsed_lines
