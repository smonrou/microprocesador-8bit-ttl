; ─────────────────────────────────────────────────────────────────────────
; referencia.asm — programa canónico de A.7: multiplicación 4 × 3
;
; Copia fiel del listado de A.7 en contexto_proyecto.md, con direcciones
; numéricas tal como aparecen en el documento. La directiva .DB al final
; cumple la precondición que A.7 exige ("la dirección 204 debe contener el
; valor 4 antes de ejecutar") — antes había que escribirla a mano.
;
; Resultado esperado: OUT muestra 12 (0x0C), luego HLT.
; ─────────────────────────────────────────────────────────────────────────

      LDI A,#0
      STA 200        ; resultado = 0
      LDI A,#3
      STA 201        ; contador = 3

LOOP: LDA 200
      LDB 204        ; el 4 vive en la dirección 204
      ADD
      STA 200        ; resultado += 4

      LDA 201
      LDI B,#1
      SUB
      STA 201        ; contador -= 1
      JNZ LOOP

      LDA 200
      OUT            ; muestra 12
      HLT

; ── Zona de datos (0xC0-0xFF según A.6) ──────────────────────────────────
.ORG 204
      .DB 4          ; precondición de A.7
