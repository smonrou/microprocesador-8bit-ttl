"""Two-pass assembler.

Pass 1 walks the parsed lines computing each one's address (accounting for
1 vs 2 byte instructions) and builds the symbol table. Pass 2 emits bytes,
resolving labels to addresses.

Pass 1 needs only `spec.length`, which comes from the frozen
sim.isa.OPCODE_TABLE. Our opcodes are fixed-width (4 bits, always), so
layout is pure arithmetic with zero heuristics — that is exactly why two
passes suffice.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from sim.isa import Mode
from sim.memory import SIZE as MEMORY_SIZE

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

PROGRAM_ZONE_END = 0xBF   # A.6: programa 0x00-0xBF, datos 0xC0-0xFF
DATA_ZONE_START = 0xC0
START_ADDRESS = 0x00      # A.6: la ejecución siempre arranca aquí


@dataclass(frozen=True)
class LayoutItem:
    parsed: ParsedLine
    address: Optional[int]   # None for zero-size lines
    size: int


@dataclass(frozen=True)
class ListingRow:
    address: Optional[int]
    data: Tuple[int, ...]
    line_number: int
    source: str


@dataclass(frozen=True)
class AssemblyResult:
    binary: bytes                        # exactly 256 bytes, zero-filled
    symbols: Dict[str, int]
    rows: Tuple[ListingRow, ...]
    listing: str = ""
    load_script: str = ""                # LOAD, un byte por línea
    load_script_bloques: str = ""        # LOADB, varios bytes por línea
    warnings: Tuple[str, ...] = ()
    spans: Tuple[Tuple[int, int], ...] = ()


# ── Pass 1: layout and symbol table ───────────────────────────────────────

def first_pass(parsed_lines: List[ParsedLine]):
    """Compute addresses and collect labels. Returns (layout, symbols)."""
    collector = ErrorCollector()
    layout: List[LayoutItem] = []
    symbols: Dict[str, int] = {}
    defined_at: Dict[str, int] = {}   # label -> line number, for duplicate messages
    pointer = START_ADDRESS

    for parsed in parsed_lines:
        # .ORG moves the pointer before anything on this line is placed.
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


# ── Pass 2: resolve and emit ──────────────────────────────────────────────

def _resolve(operand: Operand, symbols: Dict[str, int], parsed: ParsedLine) -> int:
    """Operand -> byte value. Labels resolve through the symbol table."""
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

    # Labels are structurally in range, but re-checking costs nothing and
    # documents the invariant.
    if value < 0 or value > 0xFF:
        raise OperandRangeError(
            f"operando fuera de rango: {value}", parsed.line_number, parsed.text
        )
    return value


def second_pass(layout: List[LayoutItem], symbols: Dict[str, int]):
    """Emit bytes. Returns (binary, rows, warnings, spans)."""
    collector = ErrorCollector()
    image = bytearray(MEMORY_SIZE)
    written: Dict[int, int] = {}       # address -> line number that wrote it
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
                # A.4: [OPCODE(4 bits)][0000] — el nibble bajo siempre 0000.
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
    """Contiguous (start, end) ranges of emitted addresses."""
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


# ── Public API ────────────────────────────────────────────────────────────

def assemble(source_text: str) -> AssemblyResult:
    """Assemble source text into a 256-byte image. Raises AssemblyFailed."""
    from .listing import (
        format_listing,
        format_load_script,
        format_load_script_bloques,
    )

    parsed_lines = parse_source(source_text)          # phase 1
    layout, symbols = first_pass(parsed_lines)         # phase 2
    binary, rows, warnings, spans = second_pass(layout, symbols)  # phase 3

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
