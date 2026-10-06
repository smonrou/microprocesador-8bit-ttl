
        MOV A,[VUELTAS]
        MOV [CONTADOR],A     ; contador = vueltas

VUELTA: MOV A,1              ; enciende el bit 0
CORRE:  OUT
        MOV [TEMP],A
        MOV B,[TEMP]         ; B = A (copia a través de memoria)
        ADD                  ; A = A + A → desplaza 1 bit a la izquierda
        JNZ CORRE            ; A = 0 cuando el 1 se cae por el bit 7

        MOV A,[CONTADOR]
        MOV B,1
        SUB
        MOV [CONTADOR],A     ; contador -= 1
        JNZ VUELTA
        HLT

.ORG 0xC0
VUELTAS:  .DB 3              ; cuántas vueltas dar
CONTADOR: .DB 0              ; 0xC1
TEMP:     .DB 0              ; 0xC2 
