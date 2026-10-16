; diag2_bits_A.asm — un bit a la vez por el registro A y la ALU (F=A).
; Esperado: OUT = 1, 2, 4, 8, 16, 32, 64, 128 (usar STEP para verlo en LEDs).
      MOV A,1
      OUT
      MOV A,2
      OUT
      MOV A,4
      OUT
      MOV A,8
      OUT
      MOV A,16
      OUT
      MOV A,32
      OUT
      MOV A,64
      OUT
      MOV A,128
      OUT
      HLT
