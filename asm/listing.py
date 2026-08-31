"""Pure formatting: assembly listing, symbol table, serial LOAD script.

Takes plain dataclasses, returns strings — no assembly logic here.

The FUENTE column echoes the raw source line untouched. A listing that
pretty-prints the source hides what the user actually typed.
"""

from typing import Dict, Iterable, Sequence

# Bytes por línea LOADB. Ver format_load_script_bloques() para el porqué de 8.
BYTES_POR_BLOQUE = 8

BYTES_PER_ROW = 4
ADDRESS_WIDTH = 2      # memory is 256 bytes; 4 hex digits would be dishonest
BYTES_WIDTH = BYTES_PER_ROW * 3 - 1   # "XX XX XX XX"
LINE_WIDTH = 3

HEADER = (
    f"{'DIR':<{ADDRESS_WIDTH + 1}}  {'BYTES':<{BYTES_WIDTH}}  "
    f"{'LÍN':>{LINE_WIDTH}}  FUENTE"
)
SEPARATOR = (
    f"{'-' * (ADDRESS_WIDTH + 1)}  {'-' * BYTES_WIDTH}  "
    f"{'-' * LINE_WIDTH}  {'-' * 44}"
)


def _format_bytes(data: Sequence[int]) -> str:
    return " ".join(f"{byte:02X}" for byte in data)


def format_listing(rows: Iterable, symbols: Dict[str, int]) -> str:
    lines = [HEADER, SEPARATOR]

    for row in rows:
        chunks = [
            row.data[index : index + BYTES_PER_ROW]
            for index in range(0, len(row.data), BYTES_PER_ROW)
        ] or [()]

        for chunk_index, chunk in enumerate(chunks):
            if row.address is None:
                address_text = ""
            else:
                address_text = f"{row.address + chunk_index * BYTES_PER_ROW:02X}"

            if chunk_index == 0:
                line_text = f"{row.line_number:>{LINE_WIDTH}}"
                source_text = row.source
            else:
                # Continuation row for a long .DB: repeat the address only.
                line_text = " " * LINE_WIDTH
                source_text = ""

            lines.append(
                f"{address_text:<{ADDRESS_WIDTH + 1}}  "
                f"{_format_bytes(chunk):<{BYTES_WIDTH}}  "
                f"{line_text}  {source_text}".rstrip()
            )

    lines.append("")
    lines.append("TABLA DE SÍMBOLOS")
    if symbols:
        width = max(len(name) for name in symbols)
        # Sorted by address: more useful than alphabetical when reading a
        # memory map.
        for name, address in sorted(symbols.items(), key=lambda item: item[1]):
            lines.append(f"{name:<{width}} = 0x{address:02X} ({address})")
    else:
        lines.append("(ninguno)")

    return "\n".join(lines)


def format_load_script(rows: Iterable) -> str:
    """Serial LOAD commands, one byte per line (B.3 protocol).

    Sparse — only addresses actually written, so a 29-byte program is 29
    lines instead of 256 pasted into a serial monitor.

    The block form below is what the CLI writes; this one stays available
    through the API for byte-by-byte inspection or as a fallback.
    """
    lines = []
    for row in rows:
        if row.address is None or not row.data:
            continue
        for offset, byte in enumerate(row.data):
            lines.append(f"LOAD 0x{row.address + offset:02X} 0x{byte:02X}")
    return "\n".join(lines)


def _bytes_por_direccion(rows: Iterable) -> Dict[int, int]:
    escritos = {}
    for row in rows:
        if row.address is None or not row.data:
            continue
        for offset, byte in enumerate(row.data):
            escritos[row.address + offset] = byte
    return escritos


def _rangos_contiguos(direcciones: Sequence[int]):
    """Agrupa direcciones ordenadas en tramos consecutivos."""
    if not direcciones:
        return
    inicio = anterior = direcciones[0]
    for direccion in direcciones[1:]:
        if direccion == anterior + 1:
            anterior = direccion
            continue
        yield (inicio, anterior)
        inicio = anterior = direccion
    yield (inicio, anterior)


def format_load_script_bloques(rows: Iterable) -> str:
    """Comandos LOADB, varios bytes por línea (B.3 protocol).

    Es lo que escribe el CLI en el archivo `.load`: el programa de referencia
    baja de 29 líneas a 5.

    BYTES_POR_BLOQUE está en 8 por una razón concreta: el buffer de recepción
    del Arduino son 64 bytes, y `LOADB 0xNN ` más ocho `0xNN ` da 51
    caracteres. Subirlo a 16 pasaría de 90 y podría perder bytes en silencio
    al pegar el archivo de golpe en el monitor serie.
    """
    escritos = _bytes_por_direccion(rows)
    direcciones = sorted(escritos)

    lines = []
    for inicio, fin in _rangos_contiguos(direcciones):
        for base in range(inicio, fin + 1, BYTES_POR_BLOQUE):
            ultimo = min(base + BYTES_POR_BLOQUE - 1, fin)
            valores = " ".join(
                f"0x{escritos[direccion]:02X}"
                for direccion in range(base, ultimo + 1)
            )
            lines.append(f"LOADB 0x{base:02X} {valores}")
    return "\n".join(lines)
