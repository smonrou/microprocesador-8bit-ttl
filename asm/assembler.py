from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from sim.isa import Mode
from sim.memory import SIZE as MEMORY_SIZE   # 256 bytes

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

# Mapa de memoria (A.6).
PROGRAM_ZONE_END = 0xBF   # A.6: programa 0x00-0xBF, datos 0xC0-0xFF
DATA_ZONE_START = 0xC0
START_ADDRESS = 0x00      # A.6: la ejecución siempre arranca aquí


@dataclass(frozen=True)
class LayoutItem:
    """Una línea con su dirección asignada (resultado de la pasada 1)."""
    parsed: ParsedLine
    address: Optional[int]   # None en las líneas que no ocupan bytes
    size: int                # bytes que ocupa (0, 1, 2, o N para .DB)


@dataclass(frozen=True)
class ListingRow:
    """Una fila del listado final (resultado de la pasada 2)."""
    address: Optional[int]
    data: Tuple[int, ...]    # bytes emitidos por esa línea
    line_number: int
    source: str              # línea fuente original


@dataclass(frozen=True)
class AssemblyResult:
    """Todo lo que produce assemble()."""
    binary: bytes                        # exactamente 256 bytes, relleno con ceros
    symbols: Dict[str, int]              # tabla de símbolos: etiqueta -> dirección
    rows: Tuple[ListingRow, ...]         # una fila por línea del fuente
    listing: str = ""                    # listado ya formateado (.lst)
    load_script: str = ""                # LOAD, un byte por línea
    load_script_bloques: str = ""        # LOADB, varios bytes por línea
    warnings: Tuple[str, ...] = ()       # avisos que no impiden ensamblar
    spans: Tuple[Tuple[int, int], ...] = ()  # tramos de memoria escritos (inicio, fin)


# ── Pasada 1: distribución en memoria y tabla de símbolos ─────────────────

def first_pass(parsed_lines: List[ParsedLine]):
    """Calcula direcciones y recoge las etiquetas. Devuelve (layout, symbols).

    Idea central: un "puntero de ensamblado" que empieza en 0x00 y avanza
    tantos bytes como ocupe cada línea. Una etiqueta vale lo que valga el
    puntero en la línea donde se define.
    """
    collector = ErrorCollector()
    layout: List[LayoutItem] = []
    symbols: Dict[str, int] = {}
    defined_at: Dict[str, int] = {}   # etiqueta -> número de línea, para el mensaje de duplicada
    pointer = START_ADDRESS

    for parsed in parsed_lines:
        # .ORG mueve el puntero antes de colocar nada de esta línea.
        if parsed.kind == LineKind.DIRECTIVE and parsed.directive == ".ORG":
            pointer = parsed.operands[0].value
            layout.append(LayoutItem(parsed=parsed, address=None, size=0))
            continue

        # Registrar la etiqueta (si hay) con la dirección actual.
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

        # Líneas que no ocupan memoria (vacías, comentarios, solo etiqueta):
        # no tienen dirección y el puntero no se mueve.
        size = parsed.size
        if size == 0:
            layout.append(LayoutItem(parsed=parsed, address=None, size=0))
            continue

        # Última dirección que ocuparía esta línea. Dos controles:
        #  - que no se salga de los 256 bytes (vale para todo);
        #  - que una INSTRUCCIÓN no invada la zona de datos (los .DB sí
        #    pueden ir en cualquier parte).
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

        # Se asigna la dirección y el puntero avanza al siguiente byte libre.
        layout.append(LayoutItem(parsed=parsed, address=pointer, size=size))
        pointer = end + 1

    collector.raise_if_any()
    return layout, symbols


# ── Pasada 2: resolver y emitir ───────────────────────────────────────────

def _resolve(operand: Operand, symbols: Dict[str, int], parsed: ParsedLine) -> int:
    """Operando -> valor del byte. Las etiquetas se buscan en la tabla de
    símbolos; los números ya traen su valor."""
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

    # Las etiquetas siempre están en rango por construcción, pero volver a
    # comprobarlo no cuesta nada y deja documentada la garantía.
    if value < 0 or value > 0xFF:
        raise OperandRangeError(
            f"operando fuera de rango: {value}", parsed.line_number, parsed.text
        )
    return value


def second_pass(layout: List[LayoutItem], symbols: Dict[str, int]):
    """Emite los bytes. Devuelve (binary, rows, warnings, spans)."""
    collector = ErrorCollector()
    image = bytearray(MEMORY_SIZE)     # imagen de memoria: 256 ceros (0x00 = NOP)
    written: Dict[int, int] = {}       # dirección -> línea que la escribió
    data_in_program_zone: List[int] = []
    rows: List[ListingRow] = []

    for item in layout:
        parsed = item.parsed

        # Líneas sin bytes: van al listado, pero no escriben memoria.
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

        # Calcular los bytes de esta línea.
        try:
            if parsed.kind == LineKind.INSTRUCTION:
                # A.4: [OPCODE(4 bits)][0000] — el nibble bajo siempre 0000.
                # Ej.: opcode 0x6 (ADD) -> 0x6 << 4 = 0x60.
                data = [parsed.spec.opcode << 4]
                if parsed.spec.length == 2:
                    # Byte 2: el inmediato o la dirección (etiqueta resuelta).
                    data.append(_resolve(parsed.operands[0], symbols, parsed))
            else:  # .DB: un byte por cada valor escrito
                data = [
                    _resolve(operand, symbols, parsed) for operand in parsed.operands
                ]
        except AssemblerError as error:
            # Se anota el error y la línea queda en el listado sin bytes.
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

        # Escribir los bytes en la imagen, byte a byte.
        for offset, byte in enumerate(data):
            address = item.address + offset
            # Con .ORG dos líneas pueden caer en la misma dirección: error.
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
            # Se recuerda si hay datos (.DB) dentro de la zona de programa,
            # para avisar al final.
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

    # Avisos: no son errores, el ensamblado igual termina bien.
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
    """Tramos contiguos (inicio, fin) de direcciones escritas.

    Ej.: direcciones {0,1,2,3, 200,201} -> ((0, 3), (200, 201)).
    """
    if not written:
        return ()
    addresses = sorted(written)
    spans = []
    start = previous = addresses[0]
    for address in addresses[1:]:
        # Si sigue a la anterior, el tramo se alarga.
        if address == previous + 1:
            previous = address
            continue
        # Si hay un hueco, se cierra el tramo y empieza otro.
        spans.append((start, previous))
        start = previous = address
    spans.append((start, previous))   # cerrar el último tramo
    return tuple(spans)


#  API pública 

def assemble(source_text: str) -> AssemblyResult:
    """Ensambla el texto fuente en una imagen de 256 bytes. Lanza
    AssemblyFailed si hay errores.

    Encadena las tres fases; cada una aborta si encuentra errores, así que
    si se llega al return el resultado está completo.
    """
    # Import dentro de la función: el formateo solo se necesita aquí, al
    # final, una vez que los bytes ya están calculados.
    from .listing import (
        format_listing,
        format_load_script,
        format_load_script_bloques,
    )

    parsed_lines = parse_source(source_text)          # fase 1: análisis de líneas
    layout, symbols = first_pass(parsed_lines)         # fase 2: direcciones y símbolos
    binary, rows, warnings, spans = second_pass(layout, symbols)  # fase 3: emitir bytes

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
