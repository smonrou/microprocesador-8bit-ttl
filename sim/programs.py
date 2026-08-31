"""Reference program (contexto_proyecto.md A.7) — canonical acceptance test.

Hand-assembled raw bytes (no assembler exists yet, that's task B.2, separate
and future). Each byte is commented with its source line / meaning so this
stays checkable against A.7 by inspection.

      LDI A,#0
      STA 200        ; resultado = 0
      LDI A,#3
      STA 201        ; contador = 3
LOOP: LDA 200
      LDB 204        ; el 4 vive en la dirección 204
      ADD
      STA 200        ; resultado += 4
      LDA 201
      LDI B,#1
      SUB
      STA 201        ; contador -= 1
      JNZ LOOP
      LDA 200
      OUT            ; muestra 12
      HLT
"""

from .memory import Memory

LOOP_ADDRESS = 0x08  # address of the LDA 200 that starts LOOP:

REFERENCE_PROGRAM = [
    0x30, 0x00,  # 0x00 LDI A,#0
    0x50, 0xC8,  # 0x02 STA 200        ; resultado = 0
    0x30, 0x03,  # 0x04 LDI A,#3
    0x50, 0xC9,  # 0x06 STA 201        ; contador = 3
    0x10, 0xC8,  # 0x08 LOOP: LDA 200
    0x20, 0xCC,  # 0x0A LDB 204        ; el 4 vive en la dirección 204
    0x60,        # 0x0C ADD
    0x50, 0xC8,  # 0x0D STA 200        ; resultado += 4
    0x10, 0xC9,  # 0x0F LDA 201
    0x40, 0x01,  # 0x11 LDI B,#1
    0x70,        # 0x13 SUB
    0x50, 0xC9,  # 0x14 STA 201        ; contador -= 1
    0xF0, 0x08,  # 0x16 JNZ LOOP
    0x10, 0xC8,  # 0x18 LDA 200
    0xB0,        # 0x1A OUT            ; muestra 12
    0xC0,        # 0x1B HLT
]

RESULT_ADDRESS = 0xC8   # 200 — "resultado"
COUNTER_ADDRESS = 0xC9  # 201 — "contador"
CONST_4_ADDRESS = 0xCC  # 204 — precondition: must hold 4 before running

EXPECTED_OUTPUT = 12


def build_reference_memory() -> Memory:
    memory = Memory()
    memory.load_bytes(REFERENCE_PROGRAM, start=0x00)
    memory.write(CONST_4_ADDRESS, 4)  # precondition from A.7
    return memory
