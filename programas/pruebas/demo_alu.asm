
; Salida esperada:  [8, 2, 136, 238, 102, 240]

; ADD: 5 + 3 = 8 
      MOV A,5
      MOV B,3
      ADD
      OUT

; SUB: 5 - 3 = 2 
      MOV A,5
      MOV B,3
      SUB
      OUT

; AND: 0xCC & 0xAA = 0x88 (enmascarar bits) 
      MOV A,0xCC
      MOV B,0xAA
      AND
      OUT

; OR: 0xCC | 0xAA = 0xEE
      MOV A,0xCC
      MOV B,0xAA
      OR
      OUT

;  XOR: 0xCC ^ 0xAA = 0x66
      MOV A,0xCC
      MOV B,0xAA
      XOR
      OUT

; ── NOT vía XOR: 0x0F ^ 0xFF = 0xF0
; El set no tiene instrucción NOT. Se suple con XOR contra 0xFF, igual que
; hacen arquitecturas RISC reales que tampoco la tienen.
      MOV A,0x0F
      MOV B,0xFF
      XOR
      OUT

      HLT
