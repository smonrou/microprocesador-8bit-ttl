; ─────────────────────────────────────────────────────────────────────────
; 09_contar_unos.asm — cuántos bits en 1 tiene un byte
;
; Se recorre el byte con una máscara de un solo bit (1, 2, 4, ..., 128).
; DATO AND máscara da 0 si ese bit está apagado (Z = 1) y distinto de 0 si
; está encendido. La máscara avanza sumándose consigo misma (ADD = desplazar
; a la izquierda); tras el bit 7 se vuelve 0 y el bucle termina.
;
; Demuestra: AND para aislar bits (enmascarar), ADD como desplazamiento,
; JZ para saltarse el conteo.
;
; PARA CAMBIAR EL DATO: LOAD 0xC0 <byte>
;
; Salida esperada (0b10110110): [182, 5]   → primero el dato, luego cuántos 1
; ─────────────────────────────────────────────────────────────────────────

       MOV A,[DATO]
       OUT                  ; muestra el byte analizado
       MOV A,0
       MOV [UNOS],A
       MOV A,1
       MOV [MASCARA],A      ; empieza por el bit 0

BIT:   MOV A,[DATO]
       MOV B,[MASCARA]
       AND                  ; aísla un bit
       JZ CERO              ; bit apagado: no cuenta
       MOV A,[UNOS]
       MOV B,1
       ADD
       MOV [UNOS],A         ; unos += 1

CERO:  MOV A,[MASCARA]
       MOV B,[MASCARA]
       ADD                  ; máscara <<= 1
       MOV [MASCARA],A
       JNZ BIT              ; 0 cuando ya pasó el bit 7

       MOV A,[UNOS]
       OUT
       HLT

; ── Zona de datos ────────────────────────────────────────────────────────
.ORG 0xC0
DATO:    .DB 0b10110110      ; <<<< byte a analizar (0xC0)
UNOS:    .DB 0               ; 0xC1
MASCARA: .DB 0               ; 0xC2
