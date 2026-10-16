       MOV A,0
       MOV [ANTERIOR],A
       MOV A,1
       MOV [ACTUAL],A
       MOV A,[TERMINOS]
       MOV [CONTADOR],A

OTRO:  MOV A,[ACTUAL]
       OUT
       MOV B,[ANTERIOR]
       ADD
       MOV [SIGUIENTE],A

       MOV A,[ACTUAL]
       MOV [ANTERIOR],A
       MOV A,[SIGUIENTE]
       MOV [ACTUAL],A

       MOV A,[CONTADOR]
       MOV B,1
       SUB
       MOV [CONTADOR],A
       JNZ OTRO
       HLT

.ORG 0xC0
TERMINOS:  .DB 13
ANTERIOR:  .DB 0
ACTUAL:    .DB 0
SIGUIENTE: .DB 0
CONTADOR:  .DB 0
