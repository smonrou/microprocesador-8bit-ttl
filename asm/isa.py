from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

MEMORY_SIZE = 256


class Mode(Enum):
    IMPLICIT = auto()    # opera sobre A y/o B, sin byte de operando
    DIRECT = auto()      # el operando es una dirección
    IMMEDIATE = auto()   # el operando es el dato
    NONE = auto()        # NOP, HLT


@dataclass(frozen=True)
class InstructionSpec:
    opcode: int
    mnemonic: str            # único por opcode, el parser se arma a partir de esto
    length: int
    mode: Mode
    register: Optional[str] = None


# Tabla de la ISA (A.5)
OPCODE_TABLE = {
    0x0: InstructionSpec(0x0, "NOP", 1, Mode.NONE),
    0x1: InstructionSpec(0x1, "MOV A,[dir]", 2, Mode.DIRECT, register="A"),
    0x2: InstructionSpec(0x2, "MOV B,[dir]", 2, Mode.DIRECT, register="B"),
    0x3: InstructionSpec(0x3, "MOV A,inm", 2, Mode.IMMEDIATE, register="A"),
    0x4: InstructionSpec(0x4, "MOV B,inm", 2, Mode.IMMEDIATE, register="B"),
    0x5: InstructionSpec(0x5, "MOV [dir],A", 2, Mode.DIRECT, register="A"),
    0x6: InstructionSpec(0x6, "ADD", 1, Mode.IMPLICIT),
    0x7: InstructionSpec(0x7, "SUB", 1, Mode.IMPLICIT),
    0x8: InstructionSpec(0x8, "AND", 1, Mode.IMPLICIT),
    0x9: InstructionSpec(0x9, "OR", 1, Mode.IMPLICIT),
    0xA: InstructionSpec(0xA, "XOR", 1, Mode.IMPLICIT),
    0xB: InstructionSpec(0xB, "OUT", 1, Mode.IMPLICIT),
    0xC: InstructionSpec(0xC, "HLT", 1, Mode.NONE),
    0xD: InstructionSpec(0xD, "JMP", 2, Mode.DIRECT),
    0xE: InstructionSpec(0xE, "JZ", 2, Mode.DIRECT),
    0xF: InstructionSpec(0xF, "JNZ", 2, Mode.DIRECT),
}
