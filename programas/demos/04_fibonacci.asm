
       MOV A,0
       MOV [ANTERIOR],A     ; F(0) = 0
       MOV A,1
       MOV [ACTUAL],A       ; F(1) = 1
       MOV A,[TERMINOS]
       MOV [CONTADOR],A

OTRO:  MOV A,[ACTUAL]
       OUT                  ; muestra el término actual
       MOV B,[ANTERIOR]
       ADD
       MOV [SIGUIENTE],A    ; siguiente = actual + anterior

       MOV A,[ACTUAL]
       MOV [ANTERIOR],A     ; anterior = actual
       MOV A,[SIGUIENTE]
       MOV [ACTUAL],A       ; actual = siguiente

       MOV A,[CONTADOR]
       MOV B,1
       SUB
       MOV [CONTADOR],A     ; contador -= 1
       JNZ OTRO
       HLT

.ORG 0xC0
TERMINOS:  .DB 13            ; cuántos términos mostrar
ANTERIOR:  .DB 0             ; 0xC1
ACTUAL:    .DB 0             ; 0xC2
SIGUIENTE: .DB 0             ; 0xC3
CONTADOR:  .DB 0             ; 0xC4
