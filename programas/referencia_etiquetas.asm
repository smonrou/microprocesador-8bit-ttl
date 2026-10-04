; ─────────────────────────────────────────────────────────────────────────
; referencia_etiquetas.asm — misma multiplicación 4 × 3 de A.7, escrita con
; etiquetas de datos en vez de direcciones numéricas.
;
; Ensambla a bytes IDÉNTICOS a referencia.asm (hay un test que lo verifica):
; las etiquetas son azúcar sintáctico puro, resuelto en la primera pasada.
; Esta versión es la legible; referencia.asm es la fiel al documento.
;
; Resultado esperado: OUT muestra 12 (0x0C), luego HLT.
; ─────────────────────────────────────────────────────────────────────────

      MOV A,0
      MOV [RESULTADO],A  ; resultado = 0
      MOV A,3
      MOV [CONTADOR],A   ; contador = 3

LOOP: MOV A,[RESULTADO]
      MOV B,[CUATRO]
      ADD
      MOV [RESULTADO],A  ; resultado += 4

      MOV A,[CONTADOR]
      MOV B,1
      SUB
      MOV [CONTADOR],A   ; contador -= 1
      JNZ LOOP

      MOV A,[RESULTADO]
      OUT                ; muestra 12
      HLT

; ── Zona de datos (0xC0-0xFF según A.6) ──────────────────────────────────
.ORG 200
RESULTADO: .DB 0         ; 200 (0xC8) — acumulador del producto
CONTADOR:  .DB 0         ; 201 (0xC9) — cuántas sumas quedan

.ORG 204
CUATRO:    .DB 4         ; 204 (0xCC) — el multiplicando
