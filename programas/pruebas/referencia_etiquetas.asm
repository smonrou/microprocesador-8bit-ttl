; Resultado esperado: OUT muestra 12 (0x0C), luego HLT.

      MOV A,0
      MOV [RESULTADO],A
      MOV A,3
      MOV [CONTADOR],A

LOOP: MOV A,[RESULTADO]
      MOV B,[CUATRO]
      ADD
      MOV [RESULTADO],A

      MOV A,[CONTADOR]
      MOV B,1
      SUB
      MOV [CONTADOR],A
      JNZ LOOP

      MOV A,[RESULTADO]
      OUT  ; muestra 12
      HLT

.ORG 200
RESULTADO: .DB 0
CONTADOR:  .DB 0

.ORG 204
CUATRO:    .DB 4
