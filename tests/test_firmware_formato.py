"""El volcado A.9 del firmware contra sim/trace.py, byte a byte.

Si los dos formatos difieren, comparar un volcado del hardware contra uno del
simulador durante la depuración se vuelve un ejercicio de vista. Aquí se
fuerza que sean idénticos.
"""

import pytest

from asm import assemble
from asm.examples import read_source
from sim.cpu import CPU
from sim.memory import Memory
from sim.trace import format_cycle

PROGRAMAS = [
    "programas/referencia.asm",
    "programas/demo_alu.asm",
    "programas/demo_multiplicacion.asm",
]


def bloques_del_simulador(binario):
    memoria = Memory()
    memoria.load_bytes(binario)
    cpu = CPU(memoria)

    bloques = []
    while not cpu.halted:
        resultado = cpu.step()
        if resultado.completed:
            bloques.append(format_cycle(resultado.trace))
    return bloques


@pytest.mark.parametrize("ruta", PROGRAMAS)
def test_los_bloques_a9_coinciden_byte_a_byte(ejecutar_arnes, ruta):
    binario = assemble(read_source(ruta)).binary
    obtenidos = ejecutar_arnes(binario, "--bloques")["bloques"]
    esperados = bloques_del_simulador(binario)

    assert len(obtenidos) == len(esperados)

    for indice, (obtenido, esperado) in enumerate(zip(obtenidos, esperados), 1):
        if obtenido != esperado:
            pytest.fail(
                f"{ruta}: el bloque de la instrucción {indice} difiere.\n\n"
                f"--- firmware ---\n{obtenido}\n\n"
                f"--- simulador ---\n{esperado}"
            )


def test_cubre_todas_las_categorias(ejecutar_arnes):
    # El programa de referencia usa carga directa, inmediata, guarda, ALU,
    # salto condicional, salida y control. Falta el salto incondicional.
    binario = assemble(read_source("programas/referencia.asm")).binary
    bloques = "\n".join(ejecutar_arnes(binario, "--bloques")["bloques"])

    assert "→ A" in bloques           # carga directa
    assert "#0x" in bloques            # carga inmediata
    assert "A → Mem[" in bloques       # guarda
    assert "ALU: M=" in bloques        # operación de ALU
    assert "salta" in bloques          # salto condicional
    assert "Muestra A" in bloques      # salida
    assert "EXECUTE HLT" in bloques    # control


def test_salto_incondicional_tambien_coincide(ejecutar_arnes):
    binario = assemble("JMP FIN\nNOP\nFIN: HLT\n").binary
    obtenidos = ejecutar_arnes(binario, "--bloques")["bloques"]
    esperados = bloques_del_simulador(binario)
    assert obtenidos == esperados


def test_bloque_de_nop_coincide(ejecutar_arnes):
    binario = assemble("NOP\nHLT\n").binary
    assert (ejecutar_arnes(binario, "--bloques")["bloques"]
            == bloques_del_simulador(binario))


# ── Líneas clave=valor para Processing ───────────────────────────────────

@pytest.mark.parametrize("ruta", PROGRAMAS)
def test_hay_una_linea_clave_valor_por_instruccion(ejecutar_arnes, ruta):
    binario = assemble(read_source(ruta)).binary
    resultado = ejecutar_arnes(binario, "--bloques")
    assert len(resultado["claves"]) == len(resultado["instrucciones"])


def test_las_lineas_clave_valor_son_ascii_puro(ejecutar_arnes):
    # Processing parsea estas líneas: ningún acento ni carácter de dibujo
    # puede colarse en ellas, pase lo que pase con la codificación del
    # monitor serie.
    binario = assemble(read_source("programas/referencia.asm")).binary
    for linea in ejecutar_arnes(binario, "--bloques")["claves"]:
        linea.encode("ascii")   # lanza si hay algo fuera de ASCII


def test_las_claves_esperadas_estan_presentes(ejecutar_arnes):
    binario = assemble(read_source("programas/referencia.asm")).binary
    primera = ejecutar_arnes(binario, "--bloques")["claves"][0]

    assert primera.startswith("#")
    for clave in ("ciclo", "pc", "ir", "op", "a", "b", "z", "c", "halted"):
        assert f"{clave}=" in primera


def test_la_linea_de_out_incluye_la_salida(ejecutar_arnes):
    binario = assemble(read_source("programas/referencia.asm")).binary
    claves = ejecutar_arnes(binario, "--bloques")["claves"]

    con_salida = [linea for linea in claves if "salida=" in linea]
    assert len(con_salida) == 1
    assert "salida=12" in con_salida[0]


def test_la_ultima_linea_marca_halted(ejecutar_arnes):
    binario = assemble(read_source("programas/referencia.asm")).binary
    claves = ejecutar_arnes(binario, "--bloques")["claves"]
    assert "halted=1" in claves[-1]
    assert all("halted=0" in linea for linea in claves[:-1])
