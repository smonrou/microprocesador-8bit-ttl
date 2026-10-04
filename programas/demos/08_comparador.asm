; ─────────────────────────────────────────────────────────────────────────
; 08_comparador.asm — ordenar dos números (mayor y menor)
;
; Solo hay saltos por la bandera Z, así que no se puede saltar "si A < B".
; Se resuelve con una carrera: se restan 1 a copias de los dos números a la
; vez; el que llega primero a 0 es el menor.
;
; Demuestra: igualdad con XOR + JZ, comparación de magnitud solo con Z,
; ramas que terminan en HLT distintos.
;
; PARA CAMBIAR LOS DATOS: LOAD 0xC0 <x>   LOAD 0xC1 <y>
;
; Salida esperada (x=23, y=42): [42, 23]   → primero el mayor, luego el menor
; ─────────────────────────────────────────────────────────────────────────

         MOV A,[NUM_X]
         MOV B,[NUM_Y]
         XOR
         JZ X_MAYOR           ; iguales: cualquier orden sirve

         MOV A,[NUM_X]
         MOV [CX],A
         MOV A,[NUM_Y]
         MOV [CY],A

CARRERA: MOV A,[CX]
         MOV B,0
         OR
         JZ Y_MAYOR           ; x se agotó primero → y es mayor
         MOV A,[CY]
         OR
         JZ X_MAYOR           ; y se agotó primero → x es mayor
         MOV B,1
         SUB
         MOV [CY],A           ; cy -= 1
         MOV A,[CX]
         SUB
         MOV [CX],A           ; cx -= 1
         JMP CARRERA

X_MAYOR: MOV A,[NUM_X]
         OUT
         MOV A,[NUM_Y]
         OUT
         HLT

Y_MAYOR: MOV A,[NUM_Y]
         OUT
         MOV A,[NUM_X]
         OUT
         HLT

; ── Zona de datos ────────────────────────────────────────────────────────
.ORG 0xC0
NUM_X: .DB 23                ; <<<< primer número  (0xC0)
NUM_Y: .DB 42                ; <<<< segundo número (0xC1)
CX:    .DB 0                 ; 0xC2
CY:    .DB 0                 ; 0xC3
