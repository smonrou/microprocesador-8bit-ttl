"""Lectura de los archivos .load que genera el ensamblador."""

import io

from depurador import cargador


def test_lee_el_load_de_referencia():
    lineas = cargador.leer_lineas("programas/referencia.load")
    assert lineas
    assert all(linea.startswith("LOADB") for linea in lineas)


def test_el_load_de_referencia_carga_el_dato_de_la_direccion_204():
    # A.7 exige que 0xCC valga 4 antes de ejecutar.
    lineas = cargador.leer_lineas("programas/referencia.load")
    assert any(linea.startswith("LOADB 0xCC") for linea in lineas)


def test_no_devuelve_lineas_vacias():
    texto = "LOADB 0x00 0x30\n\n   \nLOADB 0x02 0x50\n"
    assert cargador.lineas_de_texto(texto) == ["LOADB 0x00 0x30", "LOADB 0x02 0x50"]


def test_descarta_comentarios():
    texto = "; anotado a mano\nLOADB 0x00 0x30\n# otra nota\n"
    assert cargador.lineas_de_texto(texto) == ["LOADB 0x00 0x30"]


def test_recorta_los_espacios_de_los_bordes():
    assert cargador.lineas_de_texto("   RUN   \n") == ["RUN"]


def test_soporta_finales_de_linea_de_windows():
    assert cargador.lineas_de_texto("LOADB 0x00 0x30\r\nRUN\r\n") == [
        "LOADB 0x00 0x30", "RUN"]


def test_un_texto_vacio_no_da_lineas():
    assert cargador.lineas_de_texto("") == []
    assert cargador.lineas_de_texto("\n\n\n") == []


def test_leer_lineas_y_lineas_de_texto_coinciden():
    with io.open("programas/referencia.load", encoding="utf-8") as archivo:
        contenido = archivo.read()
    assert (cargador.leer_lineas("programas/referencia.load")
            == cargador.lineas_de_texto(contenido))


def test_ruta_load_de_un_asm():
    assert (cargador.ruta_load_de("programas/referencia.asm").replace("\\", "/")
            == "programas/referencia.load")


def test_todos_los_load_del_repo_se_leen():
    for nombre in ("referencia", "demo_alu", "demo_multiplicacion",
                   "referencia_etiquetas"):
        lineas = cargador.leer_lineas(f"programas/{nombre}.load")
        assert lineas, nombre
