"""Tabla de opcodes que usa el depurador.

Copia de lo que necesita del ISA (Parte A, congelada): el opcode son los 4 bits
altos del primer byte. Si cambia el ISA, hay que cambiarlo aquí, en
``firmware/unidad_control/isa.cpp`` y en ``asm/isa.py``.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, Optional


class Categoria(Enum):
    ALU = auto()
    CARGA_DIRECTA = auto()
    GUARDADO_DIRECTO = auto()
    CARGA_INMEDIATA = auto()
    SALTO_INCONDICIONAL = auto()
    SALTO_CONDICIONAL = auto()
    SALIDA = auto()
    CONTROL = auto()


@dataclass(frozen=True)
class Instruccion:
    opcode: int
    mnemonico: str
    longitud: int                    # 1 o 2 bytes
    categoria: Categoria
    registro: Optional[str] = None   # 'A' o 'B', si aplica


TABLA_DE_OPCODES: Dict[int, Instruccion] = {
    0x0: Instruccion(0x0, "NOP", 1, Categoria.CONTROL),
    0x1: Instruccion(0x1, "MOV A,[dir]", 2, Categoria.CARGA_DIRECTA, "A"),
    0x2: Instruccion(0x2, "MOV B,[dir]", 2, Categoria.CARGA_DIRECTA, "B"),
    0x3: Instruccion(0x3, "MOV A,inm", 2, Categoria.CARGA_INMEDIATA, "A"),
    0x4: Instruccion(0x4, "MOV B,inm", 2, Categoria.CARGA_INMEDIATA, "B"),
    0x5: Instruccion(0x5, "MOV [dir],A", 2, Categoria.GUARDADO_DIRECTO, "A"),
    0x6: Instruccion(0x6, "ADD", 1, Categoria.ALU),
    0x7: Instruccion(0x7, "SUB", 1, Categoria.ALU),
    0x8: Instruccion(0x8, "AND", 1, Categoria.ALU),
    0x9: Instruccion(0x9, "OR", 1, Categoria.ALU),
    0xA: Instruccion(0xA, "XOR", 1, Categoria.ALU),
    0xB: Instruccion(0xB, "OUT", 1, Categoria.SALIDA),
    0xC: Instruccion(0xC, "HLT", 1, Categoria.CONTROL),
    0xD: Instruccion(0xD, "JMP", 2, Categoria.SALTO_INCONDICIONAL),
    0xE: Instruccion(0xE, "JZ", 2, Categoria.SALTO_CONDICIONAL),
    0xF: Instruccion(0xF, "JNZ", 2, Categoria.SALTO_CONDICIONAL),
}
