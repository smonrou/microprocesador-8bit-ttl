; ─────────────────────────────────────────────────────────────────────────
; 10_suma_arreglo.asm — sumar un arreglo con código automodificable
;
; El set no tiene direccionamiento indirecto ([A] no existe): una
; instrucción MOV B,[dir] siempre lee la misma dirección. Pero programa y
; datos comparten la misma memoria (von Neumann), así que el programa puede
; REESCRIBIR el byte de dirección de su propia instrucción y apuntarla al
; siguiente elemento en cada vuelta.
;
; Detalle del ensamblador: no admite ETIQUETA+1, así que la instrucción que
; se modifica se escribe byte a byte con .DB (opcode 0x20 = MOV B,[dir]) para
; poder etiquetar su operando. Por eso el ensamblador avisa ".DB en zona de
; programa": es intencional.
;
; Demuestra: arquitectura von Neumann, código automodificable, recorrido de
; arreglos. El programa reinicia el puntero al empezar, así que se puede
; repetir con RESET + RUN sin volver a cargar el .load.
;
; PARA CAMBIAR LOS DATOS: LOAD 0xD0..0xD7 <valor>   LONGITUD: LOAD 0xC0 <n>
; En hardware: VEL 400 antes de RUN (se ven las sumas parciales).
;
; Salida esperada (sumas parciales de 12,7,30,25,3,18,40,5):
;                  [12, 19, 49, 74, 77, 95, 135, 140]   → total 140
; ─────────────────────────────────────────────────────────────────────────

       MOV A,ARREGLO        ; dirección del primer elemento (inmediato)
       MOV [PTR],A          ; reescribe el operando de LEER
       MOV A,[LONGITUD]
       MOV [CONTADOR],A
       MOV A,0
       MOV [SUMA],A

OTRO:  MOV A,[SUMA]
LEER:  .DB 0x20             ; MOV B,[...]  ← instrucción que se automodifica
PTR:   .DB ARREGLO          ;   su byte de dirección
       ADD
       MOV [SUMA],A         ; suma += elemento
       OUT                  ; suma parcial

       MOV A,[PTR]
       MOV B,1
       ADD
       MOV [PTR],A          ; apunta al siguiente elemento

       MOV A,[CONTADOR]
       SUB                  ; (B sigue valiendo 1)
       MOV [CONTADOR],A     ; contador -= 1
       JNZ OTRO
       HLT

; ── Zona de datos ────────────────────────────────────────────────────────
.ORG 0xC0
LONGITUD: .DB 8              ; <<<< cuántos elementos sumar (0xC0)
CONTADOR: .DB 0              ; 0xC1
SUMA:     .DB 0              ; 0xC2

.ORG 0xD0
ARREGLO:  .DB 12, 7, 30, 25, 3, 18, 40, 5   ; <<<< 0xD0-0xD7
