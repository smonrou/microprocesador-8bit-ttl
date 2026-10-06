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

      MOV A,0
      MOV [200],A    ; resultado = 0
      MOV A,3
      MOV [201],A    ; contador = 3

LOOP: MOV A,[200]
      MOV B,[204]    ; el 4 vive en la dirección 204
      ADD
      MOV [200],A    ; resultado += 4

      MOV A,[201]
      MOV B,1
      SUB
      MOV [201],A    ; contador -= 1
      JNZ LOOP

      MOV A,[200]
      OUT            ; muestra 12
      HLT

; ── Zona de datos (0xC0-0xFF según A.6) ──────────────────────────────────
.ORG 204
      .DB 4          ; precondición de A.7
