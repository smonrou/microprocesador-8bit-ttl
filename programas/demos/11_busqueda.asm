; ─────────────────────────────────────────────────────────────────────────
; 11_busqueda.asm — buscar un valor en un arreglo
;
; Recorre el arreglo con la misma técnica de 10_suma_arreglo.asm (código
; automodificable) y compara cada elemento con el buscado usando XOR: si
; son iguales el resultado es 0 y JZ salta a "encontrado".
;
; Demuestra: búsqueda lineal, comparación con XOR, dos finales posibles,
; código automodificable.
;
; PARA CAMBIAR QUÉ SE BUSCA: LOAD 0xC0 <valor>
; PARA CAMBIAR EL ARREGLO:   LOAD 0xD0..0xD7 <valor>   LONGITUD: LOAD 0xC1 <n>
;
; Salida: la posición (0 = primero) donde está el valor, o 255 (todos los
; LEDs encendidos) si no está.
; Salida esperada (buscar 23 en 15,42,8,99,23,64,7,51): [4]
; ─────────────────────────────────────────────────────────────────────────

            MOV A,ARREGLO        ; dirección del primer elemento
            MOV [PTR],A          ; reescribe el operando de LEER
            MOV A,0
            MOV [INDICE],A

OTRO:       MOV A,[BUSCADO]
LEER:       .DB 0x20             ; MOV B,[...]  ← instrucción que se automodifica
PTR:        .DB ARREGLO          ;   su byte de dirección
            XOR                  ; ¿elemento == buscado?
            JZ ENCONTRADO

            MOV A,[PTR]
            MOV B,1
            ADD
            MOV [PTR],A          ; siguiente elemento
            MOV A,[INDICE]
            ADD
            MOV [INDICE],A       ; indice += 1
            MOV B,[LONGITUD]
            XOR                  ; ¿ya se revisaron todos?
            JNZ OTRO

            MOV A,0xFF           ; no está
            OUT
            HLT

ENCONTRADO: MOV A,[INDICE]
            OUT
            HLT

; ── Zona de datos ────────────────────────────────────────────────────────
.ORG 0xC0
BUSCADO:  .DB 23             ; <<<< valor a buscar (0xC0)
LONGITUD: .DB 8              ; <<<< cuántos elementos (0xC1)
INDICE:   .DB 0              ; 0xC2

.ORG 0xD0
ARREGLO:  .DB 15, 42, 8, 99, 23, 64, 7, 51   ; <<<< 0xD0-0xD7
