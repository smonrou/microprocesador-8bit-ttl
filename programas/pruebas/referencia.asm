; Resultado esperado: OUT muestra 12 (0x0C), luego HLT.

      MOV A,0
      MOV [200],A
      MOV A,3
      MOV [201],A

LOOP: MOV A,[200]
      MOV B,[204]
      ADD
      MOV [200],A

      MOV A,[201]
      MOV B,1
      SUB
      MOV [201],A
      JNZ LOOP

      MOV A,[200]
      OUT  ; muestra 12
      HLT

.ORG 204
      .DB 4
