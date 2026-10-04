; ─────────────────────────────────────────────────────────────────────────
; 02_luz_corrediza.asm — un LED encendido que recorre los 8 bits
;
; El set no tiene instrucción de desplazamiento, pero sumar un número
; consigo mismo (A + A = 2·A) desplaza todos sus bits una posición a la
; izquierda. Cuando el 1 sale por el bit 7, el resultado es 0 (Z = 1) y el
; bit perdido queda en el acarreo (C = 1): eso termina cada vuelta.
;
; Demuestra: ADD como desplazamiento, Z/C al desbordar 8 bits, bucles
; anidados (bits dentro de vueltas).
;
; PARA CAMBIAR LAS VUELTAS: LOAD 0xC0 <n>   (n >= 1)
; En hardware: VEL 200 antes de RUN.
;
; Salida esperada: [1, 2, 4, 8, 16, 32, 64, 128] repetido 3 veces
; ─────────────────────────────────────────────────────────────────────────

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

; ── Zona de datos ────────────────────────────────────────────────────────
.ORG 0xC0
VUELTAS:  .DB 3              ; <<<< cuántas vueltas dar (0xC0)
CONTADOR: .DB 0              ; 0xC1
TEMP:     .DB 0              ; 0xC2 — puente para copiar A en B
