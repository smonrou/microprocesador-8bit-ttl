; ─────────────────────────────────────────────────────────────
; Prueba rápida generada por el depurador
; Temporales de las macros NOT/NEG: 0xF0 (A) y 0xF1 (B)
; ─────────────────────────────────────────────────────────────

; ── paso 1: A ← 0x05 ──
      MOV A,0x05
      OUT

; ── paso 2: NOT A ──
      MOV [0xF0],A  ; guarda A
      MOV A,0
      ADD           ; A = B (copia vía ALU)
      MOV [0xF1],A  ; guarda B
      MOV B,0xFF
      MOV A,[0xF0]
      XOR           ; A = NOT A
      MOV B,[0xF1]  ; restaura B
      OUT

; ── paso 3: NOT A ──
      MOV [0xF0],A  ; guarda A
      MOV A,0
      ADD           ; A = B (copia vía ALU)
      MOV [0xF1],A  ; guarda B
      MOV B,0xFF
      MOV A,[0xF0]
      XOR           ; A = NOT A
      MOV B,[0xF1]  ; restaura B
      OUT

; ── paso 4: B ← 0x03 ──
      MOV B,0x03
      OUT

; ── paso 5: NOT B ──
      MOV [0xF0],A  ; guarda A
      MOV A,0xFF
      XOR           ; A = NOT B
      MOV [0xF1],A
      MOV B,[0xF1]  ; B = NOT B
      MOV A,[0xF0]  ; restaura A
      OUT

; ── paso 6: ADD ──
      ADD           ; A = A ADD B
      OUT

; ── paso 7: NEG A ──
      MOV [0xF0],A  ; guarda A
      MOV A,0
      ADD           ; A = B (copia vía ALU)
      MOV [0xF1],A  ; guarda B
      MOV B,[0xF0]  ; B = A original
      MOV A,0
      SUB           ; A = 0 - A
      MOV B,[0xF1]  ; restaura B
      OUT

; ── paso 8: B ← 0x0F ──
      MOV B,0x0F
      OUT

; ── paso 9: AND ──
      AND           ; A = A AND B
      OUT

; ── paso 10: NEG B ──
      MOV [0xF0],A  ; guarda A
      MOV A,0
      SUB           ; A = 0 - B
      MOV [0xF1],A
      MOV B,[0xF1]  ; B = -B
      MOV A,[0xF0]  ; restaura A
      OUT

; ── paso 11: OR ──
      OR            ; A = A OR B
      OUT

; ── paso 12: XOR ──
      XOR           ; A = A XOR B
      OUT

; ── paso 13: B ← 0x0E ──
      MOV B,0x0E
      OUT

; ── paso 14: SUB ──
      SUB           ; A = A SUB B
      OUT

      HLT
