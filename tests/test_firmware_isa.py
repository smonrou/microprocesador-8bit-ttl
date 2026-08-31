"""Guardián de sincronía entre el firmware (isa.h / isa.cpp) y sim/isa.py.

El firmware no puede importar Python, así que la tabla está escrita dos veces
por necesidad. Estos tests leen el C++ y verifican que ambas coincidan: si
alguien cambia una sin la otra, la suite falla. "Parte A es inmutable" (D.1).
"""

import re
from pathlib import Path

import pytest

from sim.cpu import ALU_CONTROL
from sim.isa import (
    OPCODE_TABLE,
    STEPS_2BYTE,
    STEPS_ALU,
    STEPS_CONTROL,
    Category,
    Mode,
)

FIRMWARE = Path(__file__).resolve().parent.parent / "firmware" / "microprocesador"
ISA_H = FIRMWARE / "isa.h"
ISA_CPP = FIRMWARE / "isa.cpp"


@pytest.fixture(scope="module")
def isa_h():
    return ISA_H.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def isa_cpp():
    return ISA_CPP.read_text(encoding="utf-8")


def defines(texto):
    """Extrae los #define NOMBRE VALOR con valor numérico (dec, hex o bin)."""
    encontrados = {}
    patron = re.compile(r"^#define\s+(\w+)\s+(0x[0-9A-Fa-f]+|0b[01]+|\d+)\s*(?://.*)?$",
                        re.MULTILINE)
    for nombre, valor in patron.findall(texto):
        encontrados[nombre] = int(valor, 0)
    return encontrados


def filas_tabla(texto):
    """Extrae las filas de TABLA_OPCODES como tuplas de campos."""
    cuerpo = texto.split("TABLA_OPCODES[16] = {")[1].split("};")[0]
    filas = []
    for linea in cuerpo.splitlines():
        linea = linea.strip()
        if not linea.startswith("{"):
            continue
        campos = linea.strip("{},").split(",")
        filas.append([campo.strip().strip('"') for campo in campos])
    return filas


# ── Opcodes ───────────────────────────────────────────────────────────────

NOMBRES_C = {
    "NOP": "OP_NOP", "LDA": "OP_LDA", "LDB": "OP_LDB",
    "LDI A": "OP_LDI_A", "LDI B": "OP_LDI_B", "STA": "OP_STA",
    "ADD": "OP_ADD", "SUB": "OP_SUB", "AND": "OP_AND", "OR": "OP_OR",
    "XOR": "OP_XOR", "OUT": "OP_OUT", "HLT": "OP_HLT",
    "JMP": "OP_JMP", "JZ": "OP_JZ", "JNZ": "OP_JNZ",
}


def test_hay_dieciseis_opcodes_definidos(isa_h):
    valores = defines(isa_h)
    assert all(nombre in valores for nombre in NOMBRES_C.values())


@pytest.mark.parametrize("spec", list(OPCODE_TABLE.values()), ids=lambda s: s.mnemonic)
def test_cada_opcode_coincide_con_el_simulador(isa_h, spec):
    valores = defines(isa_h)
    nombre_c = NOMBRES_C[spec.mnemonic]
    assert valores[nombre_c] == spec.opcode


# ── Constantes de la ALU (A.3) ────────────────────────────────────────────

def test_modo_aritmetico_y_logico(isa_h):
    valores = defines(isa_h)
    assert valores["ALU_ARITMETICO"] == 0
    assert valores["ALU_LOGICO"] == 1


@pytest.mark.parametrize("mnemonico", ["ADD", "SUB", "AND", "OR", "XOR"])
def test_selectores_s_coinciden_con_alu_control(isa_h, mnemonico):
    valores = defines(isa_h)
    _, s_esperado, _ = ALU_CONTROL[mnemonico]
    assert valores[f"ALU_{mnemonico}"] == int(s_esperado, 2)


@pytest.mark.parametrize("mnemonico", ["ADD", "SUB", "AND", "OR", "XOR"])
def test_modo_m_coincide_con_alu_control(isa_h, mnemonico):
    valores = defines(isa_h)
    m_esperado, _, _ = ALU_CONTROL[mnemonico]
    modo_c = valores["ALU_ARITMETICO"] if m_esperado == 0 else valores["ALU_LOGICO"]
    assert modo_c == m_esperado


def test_sub_y_xor_comparten_selector(isa_h):
    # A.3: error frecuente. Solo M los distingue.
    valores = defines(isa_h)
    assert valores["ALU_SUB"] == valores["ALU_XOR"] == 0b0110


def test_carry_de_entrada_invertido(isa_h):
    # A.3: C̄n (pin 7) está invertido. ADD sin acarreo -> HIGH, SUB -> LOW.
    valores = defines(isa_h)
    assert valores["CN_ADD"] == 1
    assert valores["CN_SUB"] == 0

    _, _, cn_add = ALU_CONTROL["ADD"]
    _, _, cn_sub = ALU_CONTROL["SUB"]
    assert valores["CN_ADD"] == cn_add
    assert valores["CN_SUB"] == cn_sub


def test_funciones_extra_del_181(isa_h):
    # Bitácora 6.2: F=A con S=1111, F=B con S=1010, ambas con M=1.
    valores = defines(isa_h)
    assert valores["ALU_PASAR_A"] == 0b1111
    assert valores["ALU_PASAR_B"] == 0b1010


def test_pendiente_carry_sub_esta_aislado(isa_h):
    # Parte C punto 5: debe seguir siendo un solo #define, sin resolver.
    valores = defines(isa_h)
    assert valores["CARRY_SUB_INVERTIDO"] == 0
    assert "protoboard" in isa_h  # el comentario que explica el pendiente


# ── Microciclos (decisión de B.1) ─────────────────────────────────────────

def test_conteo_de_pasos_coincide_con_el_simulador(isa_h):
    valores = defines(isa_h)
    assert valores["PASOS_ALU"] == len(STEPS_ALU)
    assert valores["PASOS_CONTROL"] == len(STEPS_CONTROL)
    assert valores["PASOS_2BYTES"] == len(STEPS_2BYTE)


# ── Memoria (A.6) ─────────────────────────────────────────────────────────

def test_constantes_de_memoria(isa_h):
    valores = defines(isa_h)
    assert valores["MEMORIA_TAM"] == 256
    assert valores["ZONA_PROGRAMA_FIN"] == 0xBF
    assert valores["ZONA_DATOS_INICIO"] == 0xC0
    assert valores["DIRECCION_INICIO"] == 0x00


# ── Tabla de opcodes en isa.cpp ───────────────────────────────────────────

def test_la_tabla_tiene_dieciseis_filas(isa_cpp):
    assert len(filas_tabla(isa_cpp)) == 16


def test_la_tabla_esta_en_orden_de_opcode(isa_cpp):
    filas = filas_tabla(isa_cpp)
    esperado = [NOMBRES_C[spec.mnemonic] for spec in OPCODE_TABLE.values()]
    assert [fila[0] for fila in filas] == esperado


def test_nemonicos_coinciden(isa_cpp):
    filas = filas_tabla(isa_cpp)
    esperado = [spec.mnemonic for spec in OPCODE_TABLE.values()]
    assert [fila[1] for fila in filas] == esperado


def test_longitudes_coinciden(isa_cpp):
    filas = filas_tabla(isa_cpp)
    esperado = [spec.length for spec in OPCODE_TABLE.values()]
    assert [int(fila[2]) for fila in filas] == esperado


MODOS_C = {
    Mode.IMPLICIT: "MODO_IMPLICITO",
    Mode.DIRECT: "MODO_DIRECTO",
    Mode.IMMEDIATE: "MODO_INMEDIATO",
    Mode.NONE: "MODO_NINGUNO",
}


def test_modos_coinciden(isa_cpp):
    filas = filas_tabla(isa_cpp)
    esperado = [MODOS_C[spec.mode] for spec in OPCODE_TABLE.values()]
    assert [fila[3] for fila in filas] == esperado


CATEGORIAS_C = {
    Category.ALU: "CAT_ALU",
    Category.LOAD_DIRECT: "CAT_CARGA_DIRECTA",
    Category.STORE_DIRECT: "CAT_GUARDA_DIRECTA",
    Category.LOAD_IMMEDIATE: "CAT_CARGA_INMEDIATA",
    Category.JUMP_UNCONDITIONAL: "CAT_SALTO_INCONDICIONAL",
    Category.JUMP_CONDITIONAL: "CAT_SALTO_CONDICIONAL",
    Category.OUTPUT: "CAT_SALIDA",
    Category.CONTROL: "CAT_CONTROL",
}


def test_categorias_coinciden(isa_cpp):
    filas = filas_tabla(isa_cpp)
    esperado = [CATEGORIAS_C[spec.category] for spec in OPCODE_TABLE.values()]
    assert [fila[4] for fila in filas] == esperado


REGISTROS_C = {None: "REG_NINGUNO", "A": "REG_A", "B": "REG_B"}


def test_registros_coinciden(isa_cpp):
    filas = filas_tabla(isa_cpp)
    esperado = [REGISTROS_C[spec.register] for spec in OPCODE_TABLE.values()]
    assert [fila[5] for fila in filas] == esperado


def test_microciclos_coinciden_con_el_simulador(isa_cpp):
    filas = filas_tabla(isa_cpp)
    nombre_a_constante = {
        len(STEPS_ALU): "PASOS_ALU",
        len(STEPS_CONTROL): "PASOS_CONTROL",
        len(STEPS_2BYTE): "PASOS_2BYTES",
    }
    esperado = [
        nombre_a_constante[len(spec.microstep_labels)]
        for spec in OPCODE_TABLE.values()
    ]
    assert [fila[6] for fila in filas] == esperado
