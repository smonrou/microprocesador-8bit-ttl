"""Formateo puro: listado de ensamblado, tabla de símbolos, script LOAD serie.

Recibe dataclasses simples y devuelve strings — aquí no hay lógica de
ensamblado.

La columna FUENTE repite la línea original sin tocar. Un listado que
"embellece" el fuente esconde lo que el usuario escribió de verdad.

Ejemplo de listado:
    DIR  BYTES        LÍN  FUENTE
    ---  -----------  ---  --------------------------------------------
    08   10 C8         17  LOOP: MOV A,[200]
    0A   20 CC         18        MOV B,[204]
    0C   60            19        ADD
"""

from typing import Dict, Iterable, Sequence

# Bytes por línea LOADB. Ver format_load_script_bloques() para el porqué de 8.
BYTES_POR_BLOQUE = 8

# Anchos de las columnas del listado.
BYTES_PER_ROW = 4      # bytes por fila; un .DB más largo continúa en otra fila
ADDRESS_WIDTH = 2      # la memoria es de 256 bytes; 4 dígitos hex no serían honestos
BYTES_WIDTH = BYTES_PER_ROW * 3 - 1   # "XX XX XX XX" (2 dígitos + espacio por byte)
LINE_WIDTH = 3         # número de línea del fuente

# Encabezado y línea separadora, alineados con los anchos de arriba.
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
    """Listado completo: una fila por línea del fuente y, al final, la
    tabla de símbolos."""
    lines = [HEADER, SEPARATOR]

    for row in rows:
        # Partir los bytes de la línea en trozos de BYTES_PER_ROW. Una
        # instrucción da un solo trozo; un .DB largo puede dar varios.
        # "or [()]": una línea sin bytes igual produce una fila (vacía).
        chunks = [
            row.data[index : index + BYTES_PER_ROW]
            for index in range(0, len(row.data), BYTES_PER_ROW)
        ] or [()]

        for chunk_index, chunk in enumerate(chunks):
            # Columna DIR: vacía si la línea no ocupa memoria; si no, la
            # dirección del primer byte de este trozo.
            if row.address is None:
                address_text = ""
            else:
                address_text = f"{row.address + chunk_index * BYTES_PER_ROW:02X}"

            if chunk_index == 0:
                line_text = f"{row.line_number:>{LINE_WIDTH}}"
                source_text = row.source
            else:
                # Fila de continuación de un .DB largo: solo se repite la dirección.
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
        width = max(len(name) for name in symbols)   # para alinear los '='
        # Ordenada por dirección: al leer un mapa de memoria es más útil que
        # el orden alfabético.
        for name, address in sorted(symbols.items(), key=lambda item: item[1]):
            lines.append(f"{name:<{width}} = 0x{address:02X} ({address})")
    else:
        lines.append("(ninguno)")

    return "\n".join(lines)


def format_load_script(rows: Iterable) -> str:
    """Comandos LOAD del protocolo serie, un byte por línea (protocolo B.3).

    Ej.: "LOAD 0x00 0x30".

    Disperso: solo las direcciones que de verdad se escribieron, así que un
    programa de 29 bytes son 29 líneas y no 256 pegadas en el monitor serie.

    La forma por bloques de más abajo es la que escribe el CLI; esta sigue
    disponible desde la API para revisar byte a byte o como respaldo.
    """
    lines = []
    for row in rows:
        if row.address is None or not row.data:
            continue   # líneas que no ocupan memoria
        for offset, byte in enumerate(row.data):
            lines.append(f"LOAD 0x{row.address + offset:02X} 0x{byte:02X}")
    return "\n".join(lines)


def _bytes_por_direccion(rows: Iterable) -> Dict[int, int]:
    """Aplana las filas en un diccionario dirección -> byte."""
    escritos = {}
    for row in rows:
        if row.address is None or not row.data:
            continue
        for offset, byte in enumerate(row.data):
            escritos[row.address + offset] = byte
    return escritos


def _rangos_contiguos(direcciones: Sequence[int]):
    """Agrupa direcciones ordenadas en tramos consecutivos.

    Es un generador (usa yield): va entregando (inicio, fin) de a uno.
    Ej.: [0, 1, 2, 200, 201] -> (0, 2), (200, 201).
    """
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
    """Comandos LOADB, varios bytes por línea (protocolo B.3).

    Ej.: "LOADB 0x00 0x30 0x00 0x50 0xC8 ..." (dirección inicial y luego
    hasta 8 bytes consecutivos).

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
    # Un LOADB solo sirve para bytes consecutivos, así que primero se separa
    # en tramos contiguos y luego cada tramo se corta en bloques de 8.
    for inicio, fin in _rangos_contiguos(direcciones):
        for base in range(inicio, fin + 1, BYTES_POR_BLOQUE):
            ultimo = min(base + BYTES_POR_BLOQUE - 1, fin)   # el último bloque puede ser más corto
            valores = " ".join(
                f"0x{escritos[direccion]:02X}"
                for direccion in range(base, ultimo + 1)
            )
            lines.append(f"LOADB 0x{base:02X} {valores}")
    return "\n".join(lines)
