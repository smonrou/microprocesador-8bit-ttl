"""Listado de ensamblado (artefacto para la documentación, B.2) y script
LOAD para el monitor serial (B.3)."""

import pytest

from asm import assemble

SOURCE = (
    "      LDI A,#0\n"
    "      STA 200        ; resultado = 0\n"
    "LOOP: LDA 200\n"
    "      HLT\n"
    "\n"
    ".ORG 204\n"
    "CUATRO: .DB 4\n"
)


@pytest.fixture
def result():
    return assemble(SOURCE)


# ── Listado ───────────────────────────────────────────────────────────────

def test_one_row_per_source_line(result):
    assert len(result.rows) == len(SOURCE.splitlines())


def test_listing_has_header(result):
    assert "DIR" in result.listing and "BYTES" in result.listing
    assert "FUENTE" in result.listing


def test_listing_row_shows_address_and_bytes(result):
    assert "00   30 00" in result.listing


def test_listing_echoes_raw_source_including_comments(result):
    # El listado no re-renderiza el fuente: sangría y comentarios intactos.
    assert "      STA 200        ; resultado = 0" in result.listing


def test_empty_lines_appear_without_address(result):
    rows = {row.line_number: row for row in result.rows}
    assert rows[5].address is None and rows[5].data == ()


def test_org_line_has_no_bytes(result):
    rows = {row.line_number: row for row in result.rows}
    assert rows[6].data == ()


def test_symbol_table_sorted_by_address(result):
    table = result.listing.split("TABLA DE SÍMBOLOS")[1]
    assert table.index("LOOP") < table.index("CUATRO")
    assert "LOOP" in table and "0x04" in table
    assert "CUATRO" in table and "0xCC" in table


def test_long_db_wraps_onto_continuation_rows():
    listing = assemble(".ORG 0xC0\n.DB 1,2,3,4,5,6\n").listing
    assert "C0   01 02 03 04" in listing
    assert "C4   05 06" in listing


def test_listing_reports_no_symbols():
    assert "(ninguno)" in assemble("HLT\n").listing


# ── Script LOAD ───────────────────────────────────────────────────────────

def test_load_script_has_one_line_per_emitted_byte(result):
    emitted = sum(len(row.data) for row in result.rows)
    assert len(result.load_script.splitlines()) == emitted


def test_load_script_first_line(result):
    assert result.load_script.splitlines()[0] == "LOAD 0x00 0x30"


def test_load_script_is_sparse_not_256_lines(result):
    # Disperso: solo direcciones escritas. Pegar 256 líneas en el monitor
    # serial sería absurdo.
    assert len(result.load_script.splitlines()) < 20


def test_load_script_includes_data_zone_byte(result):
    assert "LOAD 0xCC 0x04" in result.load_script


def test_load_script_uses_hex_with_prefix(result):
    for line in result.load_script.splitlines():
        parts = line.split()
        assert parts[0] == "LOAD"
        assert parts[1].startswith("0x") and parts[2].startswith("0x")


# ── Script LOADB (el que escribe el CLI) ─────────────────────────────────

def reconstruir(script):
    """Ejecuta un script LOADB sobre una memoria vacía, como haría el
    Arduino, y devuelve la imagen resultante."""
    imagen = bytearray(256)
    for linea in script.splitlines():
        partes = linea.split()
        assert partes[0] == "LOADB"
        direccion = int(partes[1], 0)
        for offset, texto in enumerate(partes[2:]):
            imagen[direccion + offset] = int(texto, 0)
    return bytes(imagen)


def test_loadb_reconstruye_el_binario_exacto(result):
    # LA garantía que importa: lo que se pega en el monitor serial carga
    # exactamente el programa que se ensambló, ni un byte de más ni de menos.
    assert reconstruir(result.load_script_bloques) == result.binary


@pytest.mark.parametrize("ruta", [
    "programas/referencia.asm",
    "programas/referencia_etiquetas.asm",
    "programas/demo_alu.asm",
    "programas/demo_multiplicacion.asm",
])
def test_loadb_reconstruye_todos_los_programas(ruta):
    from asm.examples import read_source

    resultado = assemble(read_source(ruta))
    assert reconstruir(resultado.load_script_bloques) == resultado.binary


def test_loadb_agrupa_de_ocho_en_ocho(result):
    from asm.listing import BYTES_POR_BLOQUE

    for linea in result.load_script_bloques.splitlines():
        bytes_en_la_linea = len(linea.split()) - 2   # menos LOADB y dirección
        assert 1 <= bytes_en_la_linea <= BYTES_POR_BLOQUE


def test_ninguna_linea_supera_el_buffer_del_arduino(result):
    # El buffer de recepción del Arduino son 64 bytes. Pasarse podría hacer
    # que se pierdan comandos en silencio al pegar el archivo de golpe.
    for linea in result.load_script_bloques.splitlines():
        assert len(linea) < 64


def test_loadb_no_cruza_tramos_no_contiguos(result):
    # El programa vive en 0x00-0x1B y el dato en 0xCC. Ninguna línea puede
    # abarcar el hueco: LOADB escribe bytes consecutivos.
    lineas = result.load_script_bloques.splitlines()
    ultima = lineas[-1].split()
    assert int(ultima[1], 0) == 0xCC
    assert len(ultima) == 3   # LOADB, dirección, un solo byte


def test_loadb_tiene_muchas_menos_lineas_que_load(result):
    bloques = len(result.load_script_bloques.splitlines())
    sueltas = len(result.load_script.splitlines())
    assert bloques < sueltas / 3


def test_loadb_empieza_en_la_direccion_de_arranque(result):
    assert result.load_script_bloques.splitlines()[0].startswith("LOADB 0x00 ")


def test_el_cli_escribe_el_formato_de_bloques(tmp_path):
    from asm.__main__ import main

    fuente = tmp_path / "p.asm"
    fuente.write_text("LDI A,#5\nOUT\nHLT\n", encoding="utf-8")
    assert main([str(fuente)]) == 0

    contenido = (tmp_path / "p.load").read_text(encoding="utf-8")
    assert contenido.startswith("LOADB ")
    assert "\nLOAD " not in contenido
