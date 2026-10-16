       MOV A,[VECES]
       MOV [CONTADOR],A
       MOV A,[PATRON]

OTRA:  OUT
       MOV B,0xFF
       XOR
       MOV [TEMP],A

       MOV A,[CONTADOR]
       MOV B,1
       SUB
       MOV [CONTADOR],A
       MOV A,[TEMP]
       JNZ OTRA
       HLT

.ORG 0xC0
PATRON:   .DB 0x55
VECES:    .DB 8
CONTADOR: .DB 0
TEMP:     .DB 0
