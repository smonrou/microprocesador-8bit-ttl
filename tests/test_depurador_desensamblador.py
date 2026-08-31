"""El desensamblador contra el listado que produce el ensamblador."""

import pytest

from asm import assemble
from asm.examples import read_source
from depurador import desensamblador
from sim.isa import OPCODE_TABLE


def test_una_instruccion_de_un_byte():
    linea = desensamblador.desensamblar_en([0x60], 0)
    assert linea.texto == "ADD"
    assert linea.longitud == 1
    assert linea.operando is None


def test_una_instruccion_directa_de_dos_bytes():
    linea = desensamblador.desensamblar_en([0x10, 0xC8], 0)
    assert linea.texto == "LDA 0xC8"
    assert linea.longitud == 2
    assert linea.operando == 0xC8


def test_una_instruccion_inmediata_lleva_almohadilla():
    assert desensamblador.desensamblar_en([0x30, 0x04], 0).texto == "LDI A,#0x04"
    assert desensamblador.desensamblar_en([0x40, 0x01], 0).texto == "LDI B,#0x01"


def test_los_cuatro_bits_bajos_del_opcode_se_ignoran():
    # A.4: el opcode son SIEMPRE los 4 bits altos. El nibble bajo no se usa.
    assert desensamblador.desensamblar_en([0x6F], 0).mnemonico == "ADD"
    assert desensamblador.desensamblar_en([0x60], 0).mnemonico == "ADD"


def test_ningun_byte_es_invalido():
    # Con opcode de 4 bits fijos, los 16 valores existen: no hay "opcode ilegal".
    memoria = [0] * 256
    for primero in range(256):
        memoria[0] = primero
        assert desensamblador.desensamblar_en(memoria, 0).mnemonico


def test_la_direccion_da_la_vuelta_a_los_ocho_bits():
    memoria = [0] * 256
    memoria[0xFF] = 0x10
    memoria[0x00] = 0xAB      # el operando se lee en 0x100 -> 0x00
    linea = desensamblador.desensamblar_en(memoria, 0xFF)
    assert linea.texto == "LDA 0xAB"


def test_desensamblar_el_programa_de_referencia():
    binario = assemble(read_source("programas/referencia.asm")).binary
    lineas = desensamblador.desensamblar(binario, 0x00, 0x1B)

    assert [linea.texto for linea in lineas] == [
        "LDI A,#0x00",
        "STA 0xC8",
        "LDI A,#0x03",
        "STA 0xC9",
        "LDA 0xC8",
        "LDB 0xCC",
        "ADD",
        "STA 0xC8",
        "LDA 0xC9",
        "LDI B,#0x01",
        "SUB",
        "STA 0xC9",
        "JNZ 0x08",
        "LDA 0xC8",
        "OUT",
        "HLT",
    ]


def test_las_direcciones_coinciden_con_el_listado():
    binario = assemble(read_source("programas/referencia.asm")).binary
    lineas = desensamblador.desensamblar(binario, 0x00, 0x1B)
    direcciones = [linea.direccion for linea in lineas]
    # Las mismas de programas/referencia.lst.
    assert direcciones == [0x00, 0x02, 0x04, 0x06, 0x08, 0x0A, 0x0C, 0x0D,
                           0x0F, 0x11, 0x13, 0x14, 0x16, 0x18, 0x1A, 0x1B]


def test_los_bytes_crudos_son_los_del_binario():
    binario = assemble(read_source("programas/referencia.asm")).binary
    for linea in desensamblador.desensamblar(binario, 0x00, 0x1B):
        esperados = [binario[linea.direccion + i] for i in range(linea.longitud)]
        assert linea.bytes_crudos == esperados


def test_desensamblar_cubre_los_256_bytes():
    memoria = list(range(256))
    lineas = desensamblador.desensamblar(memoria)
    assert sum(linea.longitud for linea in lineas) >= 256
    assert lineas[0].direccion == 0


def test_una_memoria_en_ceros_es_todo_nop():
    lineas = desensamblador.desensamblar([0] * 256)
    assert len(lineas) == 256
    assert all(linea.texto == "NOP" for linea in lineas)


def test_una_instruccion_de_dos_bytes_al_borde_sale_completa():
    memoria = [0] * 256
    memoria[0x10] = 0x10
    memoria[0x11] = 0xC8
    lineas = desensamblador.desensamblar(memoria, 0x10, 0x10)
    assert len(lineas) == 1
    assert lineas[0].texto == "LDA 0xC8"


def test_indice_por_direccion_apunta_al_primer_byte():
    binario = assemble(read_source("programas/referencia.asm")).binary
    lineas = desensamblador.desensamblar(binario, 0x00, 0x1B)
    indice = desensamblador.indice_por_direccion(lineas)

    assert lineas[indice[0x08]].texto == "LDA 0xC8"     # la etiqueta LOOP
    assert 0x09 not in indice                            # es el operando, no una línea


def test_el_desensamblador_no_repite_la_tabla_de_opcodes():
    # Igual que asm/mnemonics.py: la única fuente es sim/isa.py.
    import inspect
    fuente = inspect.getsource(desensamblador)
    assert "0x60" not in fuente and "OP_ADD" not in fuente
    assert "OPCODE_TABLE" in fuente


def test_mnemonico_de_un_ir_suelto():
    # La línea #pc= de STATE trae el IR pero no el operando.
    assert desensamblador.mnemonico_de(0x30) == "LDI A"
    assert desensamblador.mnemonico_de(0x00) == "NOP"
    assert desensamblador.mnemonico_de(0xC0) == "HLT"
    assert desensamblador.mnemonico_de(0x6F) == "ADD"


def test_mnemonico_de_funciona_para_los_256_valores():
    for ir in range(256):
        assert desensamblador.mnemonico_de(ir)


@pytest.mark.parametrize("opcode", sorted(OPCODE_TABLE))
def test_todo_opcode_desensambla_con_su_nemonico(opcode):
    spec = OPCODE_TABLE[opcode]
    linea = desensamblador.desensamblar_en([opcode << 4, 0x00], 0)
    assert linea.mnemonico == spec.mnemonic
    assert linea.longitud == spec.length
