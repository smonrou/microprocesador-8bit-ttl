from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .isa import Mode, MEMORY_SIZE

from .errors import (
    AssemblerError,
    ErrorCollector,
    DuplicateLabelError,
    MemoryOverflowError,
    OperandRangeError,
    OverlapError,
    ProgramZoneError,
    UndefinedLabelError,
)
from .parser import LABEL_FORMS, LineKind, Operand, ParsedLine, parse_source

# mapa de memoria (A.6)
PROGRAM_ZONE_END = 0xBF
DATA_ZONE_START = 0xC0
START_ADDRESS = 0x00


@dataclass(frozen=True)
class LayoutItem:
    parsed: ParsedLine
    address: Optional[int]   # None si no ocupa bytes
    size: int


@dataclass(frozen=True)
class ListingRow:
    address: Optional[int]
    data: Tuple[int, ...]
    line_number: int
    source: str


@dataclass(frozen=True)
class AssemblyResult:
    binary: bytes
    symbols: Dict[str, int]
    rows: Tuple[ListingRow, ...]
    listing: str = ""
    load_script: str = ""                # LOAD, un byte por línea
    load_script_bloques: str = ""        # LOADB, varios bytes por línea
    warnings: Tuple[str, ...] = ()
    spans: Tuple[Tuple[int, int], ...] = ()  # tramos escritos (inicio, fin)


# Pasada 1: direcciones y tabla de símbolos

def first_pass(parsed_lines: List[ParsedLine]):
    """Devuelve (layout, symbols). Una etiqueta vale lo que el puntero en su línea."""
    collector = ErrorCollector()
    layout: List[LayoutItem] = []
    symbols: Dict[str, int] = {}
    defined_at: Dict[str, int] = {}   # para el mensaje de duplicada
    pointer = START_ADDRESS

    for parsed in parsed_lines:
        if parsed.kind == LineKind.DIRECTIVE and parsed.directive == ".ORG":
            pointer = parsed.operands[0].value
            layout.append(LayoutItem(parsed=parsed, address=None, size=0))
            continue

        if parsed.label is not None:
            if parsed.label in symbols:
                collector.add(
                    DuplicateLabelError(
                        f"etiqueta duplicada: '{parsed.label}' ya definida en la "
                        f"línea {defined_at[parsed.label]}",
                        parsed.line_number,
                        parsed.text,
                    )
                )
            else:
                symbols[parsed.label] = pointer
                defined_at[parsed.label] = parsed.line_number

        size = parsed.size
        if size == 0:
            layout.append(LayoutItem(parsed=parsed, address=None, size=0))
            continue

        # los .DB pueden ir en la zona de datos, las instrucciones no
        end = pointer + size - 1
        if end >= MEMORY_SIZE:
            collector.add(
                MemoryOverflowError(
                    f"la sentencia excede la memoria de 256 bytes "
                    f"(ocuparía hasta 0x{end:X})",
                    parsed.line_number,
                    parsed.text,
                )
            )
        elif parsed.kind == LineKind.INSTRUCTION and end > PROGRAM_ZONE_END:
            collector.add(
                ProgramZoneError(
                    f"la instrucción excede la zona de programa "
                    f"(0x00–0x{PROGRAM_ZONE_END:02X}); ocuparía hasta 0x{end:02X}",
                    parsed.line_number,
                    parsed.text,
                )
            )

        layout.append(LayoutItem(parsed=parsed, address=pointer, size=size))
        pointer = end + 1

    collector.raise_if_any()
    return layout, symbols


# Pasada 2: resolver y emitir

def _resolve(operand: Operand, symbols: Dict[str, int], parsed: ParsedLine) -> int:
    if operand.form in LABEL_FORMS:
        if operand.name not in symbols:
            raise UndefinedLabelError(
                f"etiqueta no definida: '{operand.name}'",
                parsed.line_number,
                parsed.text,
            )
        value = symbols[operand.name]
    else:
        value = operand.value

    if value < 0 or value > 0xFF:
        raise OperandRangeError(
            f"operando fuera de rango: {value}", parsed.line_number, parsed.text
        )
    return value


def second_pass(layout: List[LayoutItem], symbols: Dict[str, int]):
    collector = ErrorCollector()
    image = bytearray(MEMORY_SIZE)     # 0x00 = NOP
    written: Dict[int, int] = {}       # dirección -> línea
    data_in_program_zone: List[int] = []
    rows: List[ListingRow] = []

    for item in layout:
        parsed = item.parsed

        if item.size == 0 or item.address is None:
            rows.append(
                ListingRow(
                    address=None,
                    data=(),
                    line_number=parsed.line_number,
                    source=parsed.text,
                )
            )
            continue

        try:
            if parsed.kind == LineKind.INSTRUCTION:
                # opcode en el nibble alto (A.4)
                data = [parsed.spec.opcode << 4]
                if parsed.spec.length == 2:
                    data.append(_resolve(parsed.operands[0], symbols, parsed))
            else:  # .DB
                data = [
                    _resolve(operand, symbols, parsed) for operand in parsed.operands
                ]
        except AssemblerError as error:
            collector.add(error)
            rows.append(
                ListingRow(
                    address=item.address,
                    data=(),
                    line_number=parsed.line_number,
                    source=parsed.text,
                )
            )
            continue

        for offset, byte in enumerate(data):
            address = item.address + offset
            if address in written:
                collector.add(
                    OverlapError(
                        f"la dirección 0x{address:02X} ya fue escrita por la "
                        f"línea {written[address]}",
                        parsed.line_number,
                        parsed.text,
                    )
                )
                continue
            written[address] = parsed.line_number
            image[address] = byte
            if parsed.kind == LineKind.DIRECTIVE and address <= PROGRAM_ZONE_END:
                data_in_program_zone.append(address)

        rows.append(
            ListingRow(
                address=item.address,
                data=tuple(data),
                line_number=parsed.line_number,
                source=parsed.text,
            )
        )

    collector.raise_if_any()

    warnings = []
    if data_in_program_zone:
        first = min(data_in_program_zone)
        warnings.append(
            f"datos (.DB) en la zona de programa a partir de 0x{first:02X}; "
            f"la zona de datos empieza en 0x{DATA_ZONE_START:02X} (A.6 la declara "
            f"convención, no restricción de hardware)"
        )
    if START_ADDRESS not in written:
        warnings.append(
            f"no se emitió nada en 0x{START_ADDRESS:02X}; la ejecución arranca "
            f"ahí (A.6) y encontrará NOPs"
        )

    return bytes(image), tuple(rows), tuple(warnings), _spans(written)


def _spans(written: Dict[int, int]) -> Tuple[Tuple[int, int], ...]:
    """Tramos contiguos (inicio, fin): {0,1,2,3,200,201} -> ((0, 3), (200, 201))."""
    if not written:
        return ()
    addresses = sorted(written)
    spans = []
    start = previous = addresses[0]
    for address in addresses[1:]:
        if address == previous + 1:
            previous = address
            continue
        spans.append((start, previous))
        start = previous = address
    spans.append((start, previous))
    return tuple(spans)


# API pública

def assemble(source_text: str) -> AssemblyResult:
    """Ensambla el fuente en una imagen de 256 bytes. Lanza AssemblyFailed si hay errores."""
    from .listing import (
        format_listing,
        format_load_script,
        format_load_script_bloques,
    )

    parsed_lines = parse_source(source_text)
    layout, symbols = first_pass(parsed_lines)
    binary, rows, warnings, spans = second_pass(layout, symbols)

    return AssemblyResult(
        binary=binary,
        symbols=symbols,
        rows=rows,
        listing=format_listing(rows, symbols),
        load_script=format_load_script(rows),
        load_script_bloques=format_load_script_bloques(rows),
        warnings=warnings,
        spans=spans,
    )
