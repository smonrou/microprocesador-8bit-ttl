"""Los cuatro formatos numéricos que pidió el usuario, sobre el mismo byte."""

import pytest

from depurador import formato_numerico as fn


@pytest.mark.parametrize("valor,esperado", [
    (0, "00000000"),
    (1, "00000001"),
    (12, "00001100"),
    (0x0C, "00001100"),
    (255, "11111111"),
    (0x80, "10000000"),
])
def test_binario_siempre_trae_los_ocho_bits(valor, esperado):
    assert fn.binario(valor) == esperado


def test_binario_no_lleva_prefijo():
    # Lo que se lee en los LEDs son bits pelados, no "0b...".
    assert not fn.binario(5).startswith("0b")


def test_binario_agrupado_parte_en_nibbles():
    assert fn.binario_agrupado(0x0C) == "0000 1100"
    assert fn.binario_agrupado(0xF0) == "1111 0000"


@pytest.mark.parametrize("valor,esperado", [
    (0, "0x00"), (12, "0x0C"), (255, "0xFF"), (0xAB, "0xAB"),
])
def test_hexadecimal_dos_digitos_en_mayuscula(valor, esperado):
    assert fn.hexadecimal(valor) == esperado


@pytest.mark.parametrize("valor,esperado", [
    (0x00, 0), (0x7F, 127), (0x80, -128), (0xFF, -1), (0xFC, -4), (0x0C, 12),
])
def test_con_signo_es_complemento_a_dos_de_ocho_bits(valor, esperado):
    assert fn.con_signo(valor) == esperado


@pytest.mark.parametrize("valor,esperado", [
    (0x00, 0), (0x7F, 127), (0x80, 128), (0xFF, 255),
])
def test_sin_signo_es_el_byte_tal_cual(valor, esperado):
    assert fn.sin_signo(valor) == esperado


def test_con_signo_y_sin_signo_coinciden_debajo_de_0x80():
    for valor in range(0x80):
        assert fn.con_signo(valor) == fn.sin_signo(valor)


def test_con_signo_y_sin_signo_difieren_en_256_desde_0x80():
    for valor in range(0x80, 0x100):
        assert fn.sin_signo(valor) - fn.con_signo(valor) == 256


def test_con_signo_con_letrero_siempre_escribe_el_signo():
    assert fn.con_signo_con_letrero(12) == "+12"
    assert fn.con_signo_con_letrero(0xFC) == "-4"
    assert fn.con_signo_con_letrero(0) == "+0"


def test_los_valores_se_enmascaran_a_ocho_bits():
    # La memoria del proyecto es de 8 bits; Memory.write también enmascara.
    assert fn.hexadecimal(0x1FF) == "0xFF"
    assert fn.binario(256) == "00000000"
    assert fn.sin_signo(-1) == 255


def test_resumen_numerico_trae_los_cuatro_formatos():
    resumen = fn.resumen_numerico(0x0C)
    assert resumen.byte == 12
    assert resumen.binario == "00001100"
    assert resumen.hexadecimal == "0x0C"
    assert resumen.sin_signo == 12
    assert resumen.con_signo == 12


def test_resumen_numerico_de_un_negativo():
    resumen = fn.resumen_numerico(0xFC)
    assert resumen.sin_signo == 252
    assert resumen.con_signo == -4
    assert resumen.hexadecimal == "0xFC"
    assert resumen.binario == "11111100"


def test_la_linea_del_resumen_muestra_todo_junto():
    assert fn.resumen_numerico(0x0C).linea() == "0x0C  0000 1100  12  +12"
    assert fn.resumen_numerico(0xFC).linea() == "0xFC  1111 1100  252  -4"


def test_el_resumen_se_imprime_como_su_linea():
    assert str(fn.resumen_numerico(12)) == fn.resumen_numerico(12).linea()


def test_el_resumen_es_inmutable():
    resumen = fn.resumen_numerico(1)
    with pytest.raises(Exception):
        resumen.byte = 2


def test_los_256_bytes_tienen_resumen_coherente():
    for valor in range(256):
        resumen = fn.resumen_numerico(valor)
        assert int(resumen.binario, 2) == valor
        assert int(resumen.hexadecimal, 16) == valor
        assert resumen.sin_signo == valor
        assert resumen.con_signo % 256 == valor
