       MOV A,0
       MOV [CUENTA],A

SIGUE: MOV A,[CUENTA]
       MOV B,1
       ADD
       MOV [CUENTA],A
       OUT

       MOV B,[LIMITE]
       XOR
       JNZ SIGUE
       HLT

.ORG 0xC0
LIMITE: .DB 15
CUENTA: .DB 0
