; ─────────────────────────────────────────────────────────────────────────
; 03_parpadeo.asm — patrón que se invierte (LEDs alternados)
;
; Muestra un patrón y luego su complemento, una y otra vez. El set no tiene
; NOT: se obtiene con XOR contra 0xFF (cada bit se invierte). Con el patrón
; 0x55 = 01010101 los LEDs alternan con 0xAA = 10101010.
;
; Demuestra: XOR como NOT, que MOV no altera las banderas (el JNZ usa la Z
; del SUB aunque entre medio haya un MOV A,[TEMP]).
;
; PARA CAMBIAR EL PATRÓN: LOAD 0xC0 <patron>   (p. ej. 0x0F, 0x81, 0x33)
; PARA CAMBIAR CUÁNTOS:   LOAD 0xC1 <n>
; En hardware: VEL 400 antes de RUN.
;
; Salida esperada: [85, 170, 85, 170, 85, 170, 85, 170]
; ─────────────────────────────────────────────────────────────────────────

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

; ── Zona de datos ────────────────────────────────────────────────────────
.ORG 0xC0
PATRON:   .DB 0x55           ; <<<< patrón inicial (0xC0)
VECES:    .DB 8              ; <<<< cuántos patrones mostrar (0xC1)
CONTADOR: .DB 0              ; 0xC2
TEMP:     .DB 0              ; 0xC3
