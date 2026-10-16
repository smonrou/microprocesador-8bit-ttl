; diag1_salida.asm — prueba la etapa de salida (273 + 244 + LEDs).
; Esperado: OUT = 0x55, LEDs 01010101.
      MOV A,0x55
      OUT
      HLT
