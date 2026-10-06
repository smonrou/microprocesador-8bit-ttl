
       MOV A,[VECES]
       MOV [CONTADOR],A
       MOV A,[PATRON]

OTRA:  OUT                  ; muestra el patrón actual
       MOV B,0xFF
       XOR                  ; A = NOT A
       MOV [TEMP],A         ; guarda el patrón invertido

       MOV A,[CONTADOR]
       MOV B,1
       SUB
       MOV [CONTADOR],A     ; contador -= 1  (aquí se fija Z)
       MOV A,[TEMP]         ; recupera el patrón — MOV no toca Z
       JNZ OTRA
       HLT


.ORG 0xC0
PATRON:   .DB 0x55           ;patrón inicial
VECES:    .DB 8              ; cuántos patrones mostrar
CONTADOR: .DB 0              
TEMP:     .DB 0              
