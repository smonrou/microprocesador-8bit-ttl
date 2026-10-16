        MOV A,[VUELTAS]
        MOV [CONTADOR],A

VUELTA: MOV A,1
CORRE:  OUT
        MOV [TEMP],A
        MOV B,[TEMP]
        ADD
        JNZ CORRE

        MOV A,[CONTADOR]
        MOV B,1
        SUB
        MOV [CONTADOR],A
        JNZ VUELTA
        HLT

.ORG 0xC0
VUELTAS:  .DB 3
CONTADOR: .DB 0
TEMP:     .DB 0
