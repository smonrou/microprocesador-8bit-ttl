"""Instruction set definition — mirrors contexto_proyecto.md section A.5 row for row.

Frozen spec, do not invent opcodes or change encoding/flag semantics here.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Tuple


class Mode(Enum):
    IMPLICIT = auto()   # operands are always A and/or B, no operand byte
    DIRECT = auto()      # operand byte is a memory address
    IMMEDIATE = auto()   # operand byte is the data itself
    NONE = auto()         # no operands at all (NOP, HLT)


class Category(Enum):
    ALU = auto()
    LOAD_DIRECT = auto()
    STORE_DIRECT = auto()
    LOAD_IMMEDIATE = auto()
    JUMP_UNCONDITIONAL = auto()
    JUMP_CONDITIONAL = auto()
    OUTPUT = auto()
    CONTROL = auto()


# Microstep label tuples, per instruction "shape" (session decision, see plan doc):
# - ALU (1 byte):            5 steps — A.8 worked example (ADD)
# - CONTROL/OUTPUT (1 byte): 3 steps — no ALU involved, symmetric reduction of ALU shape
# - IMMEDIATE (2 bytes):     4 steps — A.8 worked example (LDI A)
# - DIRECT/JUMP (2 bytes):   4 steps — same shape as IMMEDIATE (fetch operand, then execute)
STEPS_ALU: Tuple[str, ...] = ("FETCH", "DECODE", "EXECUTE", "WAIT", "WRITE")
STEPS_CONTROL: Tuple[str, ...] = ("FETCH", "DECODE", "EXECUTE")
STEPS_2BYTE: Tuple[str, ...] = ("FETCH", "DECODE", "FETCH2", "EXECUTE")


@dataclass(frozen=True)
class InstructionSpec:
    opcode: int
    mnemonic: str
    length: int              # 1 or 2 bytes
    mode: Mode
    affects_flags: bool
    category: Category
    microstep_labels: Tuple[str, ...]
    register: Optional[str] = None  # 'A' or 'B' — target/source register, when applicable


OPCODE_TABLE = {
    0x0: InstructionSpec(0x0, "NOP", 1, Mode.NONE, False, Category.CONTROL, STEPS_CONTROL),
    0x1: InstructionSpec(0x1, "LDA", 2, Mode.DIRECT, False, Category.LOAD_DIRECT, STEPS_2BYTE, register="A"),
    0x2: InstructionSpec(0x2, "LDB", 2, Mode.DIRECT, False, Category.LOAD_DIRECT, STEPS_2BYTE, register="B"),
    0x3: InstructionSpec(0x3, "LDI A", 2, Mode.IMMEDIATE, False, Category.LOAD_IMMEDIATE, STEPS_2BYTE, register="A"),
    0x4: InstructionSpec(0x4, "LDI B", 2, Mode.IMMEDIATE, False, Category.LOAD_IMMEDIATE, STEPS_2BYTE, register="B"),
    0x5: InstructionSpec(0x5, "STA", 2, Mode.DIRECT, False, Category.STORE_DIRECT, STEPS_2BYTE, register="A"),
    0x6: InstructionSpec(0x6, "ADD", 1, Mode.IMPLICIT, True, Category.ALU, STEPS_ALU),
    0x7: InstructionSpec(0x7, "SUB", 1, Mode.IMPLICIT, True, Category.ALU, STEPS_ALU),
    0x8: InstructionSpec(0x8, "AND", 1, Mode.IMPLICIT, True, Category.ALU, STEPS_ALU),
    0x9: InstructionSpec(0x9, "OR", 1, Mode.IMPLICIT, True, Category.ALU, STEPS_ALU),
    0xA: InstructionSpec(0xA, "XOR", 1, Mode.IMPLICIT, True, Category.ALU, STEPS_ALU),
    0xB: InstructionSpec(0xB, "OUT", 1, Mode.IMPLICIT, False, Category.OUTPUT, STEPS_CONTROL),
    0xC: InstructionSpec(0xC, "HLT", 1, Mode.NONE, False, Category.CONTROL, STEPS_CONTROL),
    0xD: InstructionSpec(0xD, "JMP", 2, Mode.DIRECT, False, Category.JUMP_UNCONDITIONAL, STEPS_2BYTE),
    0xE: InstructionSpec(0xE, "JZ", 2, Mode.DIRECT, False, Category.JUMP_CONDITIONAL, STEPS_2BYTE),
    0xF: InstructionSpec(0xF, "JNZ", 2, Mode.DIRECT, False, Category.JUMP_CONDITIONAL, STEPS_2BYTE),
}

ALU_MNEMONICS = {"ADD", "SUB", "AND", "OR", "XOR"}
