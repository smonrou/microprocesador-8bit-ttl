; Salida esperada (sumas parciales de 12,7,30,25,3,18,40,5):
; [12, 19, 49, 74, 77, 95, 135, 140]   → total 140

       MOV A,ARREGLO
       MOV [PTR],A
       MOV A,[LONGITUD]
       MOV [CONTADOR],A
       MOV A,0
       MOV [SUMA],A

OTRO:  MOV A,[SUMA]
LEER:  .DB 0x20
PTR:   .DB ARREGLO
       ADD
       MOV [SUMA],A
       OUT

       MOV A,[PTR]
       MOV B,1
       ADD
       MOV [PTR],A

       MOV A,[CONTADOR]
       SUB
       MOV [CONTADOR],A
       JNZ OTRO
       HLT

.ORG 0xC0
LONGITUD: .DB 8
CONTADOR: .DB 0
SUMA:     .DB 0

.ORG 0xD0
ARREGLO:  .DB 12, 7, 30, 25, 3, 18, 40, 5
