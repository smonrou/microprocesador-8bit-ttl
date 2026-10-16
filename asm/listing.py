from typing import Dict, Iterable, Sequence

# bytes por línea LOADB (ver format_load_script_bloques)
BYTES_POR_BLOQUE = 8

BYTES_PER_ROW = 4
ADDRESS_WIDTH = 2
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
    """(16, 200) -> "10 C8"."""
    return " ".join(f"{byte:02X}" for byte in data)


def format_listing(rows: Iterable, symbols: Dict[str, int]) -> str:
    lines = [HEADER, SEPARATOR]

    for row in rows:
        # "or [()]" para que las líneas sin bytes también tengan fila
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
                # continuación de un .DB largo
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
        for name, address in sorted(symbols.items(), key=lambda item: item[1]):
            lines.append(f"{name:<{width}} = 0x{address:02X} ({address})")
    else:
        lines.append("(ninguno)")

    return "\n".join(lines)


def format_load_script(rows: Iterable) -> str:
    """Un LOAD por byte escrito: "LOAD 0x00 0x30". El CLI usa la forma por bloques."""
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
    """[0, 1, 2, 200, 201] -> (0, 2), (200, 201)"""
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
    """LOADB (B.3): dirección inicial y hasta 8 bytes consecutivos.

    Con 8 bytes la línea mide 51 caracteres; con 16 pasaría el buffer de
    64 bytes del Arduino y se perderían bytes al pegar.
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
