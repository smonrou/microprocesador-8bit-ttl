; Salida: la posición (0 = primero) donde está el valor, o 255 (todos los
; LEDs encendidos) si no está.
; Salida esperada (buscar 23 en 15,42,8,99,23,64,7,51): [4]

            MOV A,ARREGLO
            MOV [PTR],A
            MOV A,0
            MOV [INDICE],A

OTRO:       MOV A,[BUSCADO]
LEER:       .DB 0x20
PTR:        .DB ARREGLO
            XOR
            JZ ENCONTRADO

            MOV A,[PTR]
            MOV B,1
            ADD
            MOV [PTR],A
            MOV A,[INDICE]
            ADD
            MOV [INDICE],A
            MOV B,[LONGITUD]
            XOR
            JNZ OTRO

            MOV A,0xFF
            OUT
            HLT

ENCONTRADO: MOV A,[INDICE]
            OUT
            HLT

.ORG 0xC0
BUSCADO:  .DB 23
LONGITUD: .DB 8
INDICE:   .DB 0

.ORG 0xD0
ARREGLO:  .DB 15, 42, 8, 99, 23, 64, 7, 51
