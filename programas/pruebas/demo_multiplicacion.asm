; 4*3 a traves de sumas
      MOV A,0
      MOV [RESULTADO],A     ; resultado = 0

      MOV A,3               ; multiplicador
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
CONTADOR:      .DB 0        ; 0xC9 

.ORG 204
MULTIPLICANDO: .DB 4        ; multiplicando
