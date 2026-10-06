
       MOV A,0
       MOV [CUENTA],A       ; cuenta = 0

SIGUE: MOV A,[CUENTA]
       MOV B,1
       ADD
       MOV [CUENTA],A       ; cuenta += 1
       OUT                  ; muestra la cuenta

       MOV B,[LIMITE]
       XOR                  ; A = cuenta XOR limite → 0 solo si son iguales
       JNZ SIGUE            ; distintos: seguir contando
       HLT

.ORG 0xC0
LIMITE: .DB 15               
CUENTA: .DB 0              
