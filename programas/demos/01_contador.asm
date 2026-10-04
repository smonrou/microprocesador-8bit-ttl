; ─────────────────────────────────────────────────────────────────────────
; 01_contador.asm — contador binario en los LEDs
;
; Cuenta 1, 2, 3, ... hasta LIMITE y muestra cada valor con OUT. En los
; 8 LEDs se ve contar en binario. La condición de salida compara la cuenta
; con el límite usando XOR: si son iguales todos los bits se anulan, el
; resultado es 0 y la bandera Z se enciende.
;
; Demuestra: bucle, comparación de igualdad con XOR + JNZ.
;
; PARA CAMBIAR EL LÍMITE: LOAD 0xC0 <n>   (LIMITE = 0 cuenta las 256 vueltas)
; En hardware: VEL 300 antes de RUN para ver la cuenta.
;
; Salida esperada: [1, 2, 3, ..., 15]
; ─────────────────────────────────────────────────────────────────────────

       MOV A,0
       MOV [CUENTA],A       ; cuenta = 0

SIGUE: MOV A,[CUENTA]
       MOV B,1
       ADD
       MOV [CUENTA],A       ; cuenta += 1
       OUT                  ; muestra la cuenta

       MOV B,[LIMITE]
       XOR                  ; A = cuenta XOR limite → 0 solo si son iguales
       JNZ SIGUE            ; distintos: seguir contando
       HLT

; ── Zona de datos ────────────────────────────────────────────────────────
.ORG 0xC0
LIMITE: .DB 15              ; <<<< hasta dónde contar (0xC0)
CUENTA: .DB 0               ; 0xC1 — se inicializa desde el programa
