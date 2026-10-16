
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

.ORG 0xC0
NUM_X: .DB 23
NUM_Y: .DB 42
CX:    .DB 0
CY:    .DB 0
