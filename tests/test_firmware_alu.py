"""El 74LS181 emulado (hal_falso.cpp) contra sim/alu.py.

Barrido exhaustivo de los 65536 pares (A, B) por operación. Si el emulador y
el simulador discrepan en un solo par, la prueba lo señala con los valores
exactos. Ancla el emulador al simulador antes de que el núcleo se apoye en él.
"""

import subprocess

import pytest

from sim import alu

FUNCIONES = {
    "ADD": alu.add,
    "SUB": alu.sub,
    "AND": alu.bit_and,
    "OR": alu.bit_or,
    "XOR": alu.bit_xor,
}


@pytest.fixture(scope="module")
def salida_alu(binario_prueba_alu):
    proceso = subprocess.run([str(binario_prueba_alu)],
                             capture_output=True, text=True)
    assert proceso.returncode == 0, proceso.stderr
    return proceso.stdout.splitlines()


@pytest.fixture(scope="module")
def filas(salida_alu):
    agrupadas = {}
    for linea in salida_alu:
        nombre, a, b, f, z, c = linea.split()
        agrupadas.setdefault(nombre, []).append(
            (int(a), int(b), int(f), int(z), int(c))
        )
    return agrupadas


def test_el_barrido_cubre_todas_las_operaciones(filas):
    assert set(filas) == set(FUNCIONES) | {"PASAR_A", "PASAR_B"}


@pytest.mark.parametrize("nombre", sorted(FUNCIONES))
def test_barrido_exhaustivo_contra_el_simulador(filas, nombre):
    funcion = FUNCIONES[nombre]
    casos = filas[nombre]
    assert len(casos) == 65536

    for a, b, f, z, c in casos:
        esperado_f, esperado_z, esperado_c = funcion(a, b)
        if (f, z, c) != (esperado_f, esperado_z, esperado_c):
            pytest.fail(
                f"{nombre} con A=0x{a:02X} B=0x{b:02X}: "
                f"el emulador dio F=0x{f:02X} Z={z} C={c}, "
                f"el simulador esperaba F=0x{esperado_f:02X} "
                f"Z={esperado_z} C={esperado_c}"
            )


def test_pasar_a_devuelve_el_registro_a(filas):
    # Bitácora 6.2: F = A con M=1, S=1111. Así lee el núcleo el registro A.
    for a, _b, f, _z, _c in filas["PASAR_A"]:
        assert f == a


def test_pasar_b_devuelve_el_registro_b(filas):
    # Bitácora 6.2: F = B con M=1, S=1010.
    for _a, b, f, _z, _c in filas["PASAR_B"]:
        assert f == b


def test_sub_no_da_prestamo_cuando_a_mayor_o_igual_que_b(filas):
    # C=1 significa que NO hubo préstamo. Pendiente C.5: por verificar en
    # protoboard, pero el emulador y el simulador deben coincidir en la
    # convención que ambos asumen.
    for a, b, _f, _z, c in filas["SUB"]:
        assert c == (1 if a >= b else 0)


def test_las_operaciones_logicas_fuerzan_carry_cero(filas):
    # A.5: en modo lógico (M=1) el acarreo no es significativo, se define 0.
    for nombre in ("AND", "OR", "XOR"):
        assert all(c == 0 for _a, _b, _f, _z, c in filas[nombre])
