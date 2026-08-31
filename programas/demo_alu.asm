; ─────────────────────────────────────────────────────────────────────────
; demo_alu.asm — las 6 funciones aprobadas por el ingeniero
;
; Ejercita ADD, SUB, AND, OR, XOR y OUT en una sola corrida. Cada operación
; imprime su resultado, así que la secuencia de salida es verificable de un
; vistazo contra la tabla de la ALU (A.3).
;
; Salida esperada:  [8, 2, 136, 238, 102, 240]
;                    │  │   │    │    │    └─ 0xF0  NOT vía XOR
;                    │  │   │    │    └────── 0x66  XOR
;                    │  │   │    └─────────── 0xEE  OR
;                    │  │   └──────────────── 0x88  AND
;                    │  └──────────────────── 5-3   SUB
;                    └─────────────────────── 5+3   ADD
; ─────────────────────────────────────────────────────────────────────────

; ── ADD: 5 + 3 = 8 ───────────────────────────────────────────────────────
      LDI A,#5
      LDI B,#3
      ADD
      OUT

; ── SUB: 5 - 3 = 2 (complemento a 2 nativo del 74LS181) ──────────────────
      LDI A,#5
      LDI B,#3
      SUB
      OUT

; ── AND: 0xCC & 0xAA = 0x88 (enmascarar bits) ────────────────────────────
      LDI A,#0xCC
      LDI B,#0xAA
      AND
      OUT

; ── OR: 0xCC | 0xAA = 0xEE (encender bits) ───────────────────────────────
      LDI A,#0xCC
      LDI B,#0xAA
      OR
      OUT

; ── XOR: 0xCC ^ 0xAA = 0x66 (detectar diferencias) ───────────────────────
      LDI A,#0xCC
      LDI B,#0xAA
      XOR
      OUT

; ── NOT vía XOR: 0x0F ^ 0xFF = 0xF0 ──────────────────────────────────────
; El set no tiene instrucción NOT. Se suple con XOR contra 0xFF, igual que
; hacen arquitecturas RISC reales que tampoco la tienen.
      LDI A,#0x0F
      LDI B,#0xFF
      XOR
      OUT

      HLT
