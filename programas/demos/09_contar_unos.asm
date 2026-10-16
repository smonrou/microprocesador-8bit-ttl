; Salida esperada (0b10110110): [182, 5]   → primero el dato, luego cuántos 1

       MOV A,[DATO]
       OUT
       MOV A,0
       MOV [UNOS],A
       MOV A,1
       MOV [MASCARA],A

BIT:   MOV A,[DATO]
       MOV B,[MASCARA]
       AND
       JZ CERO
       MOV A,[UNOS]
       MOV B,1
       ADD
       MOV [UNOS],A

CERO:  MOV A,[MASCARA]
       MOV B,[MASCARA]
       ADD
       MOV [MASCARA],A
       JNZ BIT

       MOV A,[UNOS]
       OUT
       HLT

.ORG 0xC0
DATO:    .DB 0b10110110
UNOS:    .DB 0
MASCARA: .DB 0
