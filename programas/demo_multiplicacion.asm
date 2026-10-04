; ─────────────────────────────────────────────────────────────────────────
; demo_multiplicacion.asm — multiplicación genérica por sumas repetidas
;
; Mismo algoritmo que el programa canónico de A.7, pero con los dos
; operandos aislados y marcados, para cambiarlos en vivo durante la defensa.
;
; PARA CAMBIAR LOS OPERANDOS: edita las dos líneas marcadas con  <<<<
;
; Restricción: el producto debe caber en 8 bits (máximo 255). 12×20=240 sí;
; 16×16=256 desborda y da 0 con la bandera C encendida.
;
; Con los valores actuales (4 × 3) la salida esperada es 12.
; ─────────────────────────────────────────────────────────────────────────

      MOV A,0
      MOV [RESULTADO],A     ; resultado = 0

      MOV A,3               ; <<<< MULTIPLICADOR: cuántas veces sumar
      MOV [CONTADOR],A

LOOP: MOV A,[RESULTADO]
      MOV B,[MULTIPLICANDO]
      ADD
      MOV [RESULTADO],A     ; resultado += multiplicando

      MOV A,[CONTADOR]
      MOV B,1
      SUB
      MOV [CONTADOR],A      ; contador -= 1
      JNZ LOOP              ; repetir mientras no llegue a cero

      MOV A,[RESULTADO]
      OUT                   ; muestra el producto
      HLT

; ── Zona de datos (0xC0-0xFF según A.6) ──────────────────────────────────
.ORG 200
RESULTADO:     .DB 0        ; 0xC8 — acumulador
CONTADOR:      .DB 0        ; 0xC9 — se inicializa desde el programa

.ORG 204
MULTIPLICANDO: .DB 4        ; <<<< MULTIPLICANDO: qué número sumar (0xCC)
