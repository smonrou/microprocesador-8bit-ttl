; diag3_bits_B.asm — un bit a la vez por el registro B (A=0, ADD => A=B).
; Esperado: OUT = 1, 2, 4, 8, 16, 32, 64, 128.
      MOV B,1
      MOV A,0
      ADD
      OUT
      MOV B,2
      MOV A,0
      ADD
      OUT
      MOV B,4
      MOV A,0
      ADD
      OUT
      MOV B,8
      MOV A,0
      ADD
      OUT
      MOV B,16
      MOV A,0
      ADD
      OUT
      MOV B,32
      MOV A,0
      ADD
      OUT
      MOV B,64
      MOV A,0
      ADD
      OUT
      MOV B,128
      MOV A,0
      ADD
      OUT
      HLT
