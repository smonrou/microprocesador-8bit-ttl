         MOV A,[NUM_X]
         MOV B,[NUM_Y]
         XOR
         JZ X_MAYOR

         MOV A,[NUM_X]
         MOV [CX],A
         MOV A,[NUM_Y]
         MOV [CY],A

CARRERA: MOV A,[CX]
         MOV B,0
         OR
         JZ Y_MAYOR
         MOV A,[CY]
         OR
         JZ X_MAYOR
         MOV B,1
         SUB
         MOV [CY],A
         MOV A,[CX]
         SUB
         MOV [CX],A
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
