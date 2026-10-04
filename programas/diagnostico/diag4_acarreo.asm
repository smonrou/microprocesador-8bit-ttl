; diag4_acarreo.asm — acarreo entre los dos 74LS181 (bit 3 -> bit 4).
; 0x0F + 0x01 = 0x10. Si sale 0x00, el Cn+4 (pin 16) del 181 bajo no llega
; al Cn (pin 7) del 181 alto.
      MOV A,0x0F
      MOV B,0x01
      ADD
      OUT
      HLT
