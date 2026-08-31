"""A.5 regla crítica: solo ADD/SUB/AND/OR/XOR tocan Z y C. Todo lo demás
debe dejarlas intactas."""

import pytest

from sim.cpu import CPU
from sim.memory import Memory

# LDI A,#5 ; LDI B,#5 ; SUB  -> A=0, Z=1, C=1 (resta a cero, sin préstamo)
SETUP_Z1_C1 = [0x30, 0x05, 0x40, 0x05, 0x70]  # addr 0x00-0x04, next addr = 0x05

NON_ALU_SUFFIXES = {
    "NOP": [0x00, 0xC0],
    "LDA": [0x10, 0x00, 0xC0],
    "LDB": [0x20, 0x00, 0xC0],
    "LDI A": [0x30, 0x07, 0xC0],
    "LDI B": [0x40, 0x07, 0xC0],
    "STA": [0x50, 0xC5, 0xC0],
    "OUT": [0xB0, 0xC0],
    "JMP": [0xD0, 0x07, 0xC0],   # jumps to the HLT right after it
    "JZ": [0xE0, 0x07, 0xC0],    # Z=1 -> jumps, still to the HLT right after it
    "JNZ": [0xF0, 0x07, 0xC0],   # Z=1 -> falls through to the same HLT
}


def test_sta_does_not_clear_z_so_jz_still_jumps():
    # SUB (Z=1) -> STA -> JZ: el salto SI debe ocurrir (B.1, caso obligatorio)
    program = [
        0x30, 0x05,        # 0x00 LDI A,#5
        0x40, 0x05,        # 0x02 LDI B,#5
        0x70,               # 0x04 SUB          -> A=0, Z=1
        0x50, 0xC0,         # 0x05 STA 0xC0      (no debe tocar Z)
        0xE0, 0x0C,         # 0x07 JZ 0x0C
        0x30, 0x99,         # 0x09 LDI A,#0x99   (marca "NO saltó" — no debe ejecutarse)
        0xC0,                # 0x0B HLT
        0x30, 0x42,         # 0x0C LDI A,#0x42   (marca "SI saltó")
        0xC0,                # 0x0E HLT
    ]
    memory = Memory()
    memory.load_bytes(program)
    cpu = CPU(memory)
    cpu.run()
    assert cpu.a == 0x42, "JZ no saltó: STA probablemente borró la bandera Z"


@pytest.mark.parametrize("mnemonic", list(NON_ALU_SUFFIXES.keys()))
def test_non_alu_instruction_preserves_flags(mnemonic):
    program = SETUP_Z1_C1 + NON_ALU_SUFFIXES[mnemonic]
    memory = Memory()
    memory.load_bytes(program)
    cpu = CPU(memory)
    cpu.run()
    assert cpu.z == 1, f"{mnemonic} modificó Z"
    assert cpu.c == 1, f"{mnemonic} modificó C"


def test_hlt_preserves_flags():
    memory = Memory()
    memory.load_bytes(SETUP_Z1_C1 + [0xC0])  # HLT right after the SUB
    cpu = CPU(memory)
    cpu.run()
    assert cpu.z == 1 and cpu.c == 1
