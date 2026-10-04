; ─────────────────────────────────────────────────────────────────────────
; 04_fibonacci.asm — sucesión de Fibonacci
;
; Cada término es la suma de los dos anteriores: 1, 1, 2, 3, 5, 8, ...
; Como solo hay dos registros, los dos términos viven en memoria y se
; "corren" una posición en cada vuelta (anterior ← actual ← siguiente).
;
; Demuestra: recurrencia con variables en memoria, ADD, bucle con contador.
;
; PARA CAMBIAR CUÁNTOS TÉRMINOS: LOAD 0xC0 <n>
; Con 13 términos el último es 233; el 14.º (377) no cabe en 8 bits y
; saldría 121 (377 - 256) con el acarreo encendido.
; En hardware: VEL 400 antes de RUN.
;
; Salida esperada: [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233]
; ─────────────────────────────────────────────────────────────────────────

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

; ── Zona de datos ────────────────────────────────────────────────────────
.ORG 0xC0
TERMINOS:  .DB 13            ; <<<< cuántos términos mostrar (0xC0)
ANTERIOR:  .DB 0             ; 0xC1
ACTUAL:    .DB 0             ; 0xC2
SIGUIENTE: .DB 0             ; 0xC3
CONTADOR:  .DB 0             ; 0xC4
