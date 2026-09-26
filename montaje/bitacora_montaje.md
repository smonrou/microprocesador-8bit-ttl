# Bitácora del montaje físico

Registro de lo que realmente pasó al armar el microprocesador en las 4 protoboards: fechas, mediciones, resultados de cada prueba, problemas y cómo se resolvieron. Es la evidencia para la documentación y la defensa.

- **Guía paso a paso:** artifacts de la tabla de abajo. Las casillas y resultados que se marcan ahí se guardan en cada artifact; Claude puede leerlos y pasarlos aquí.
- **Fuente de verdad del cableado:** `montaje/netlist.py` (verificado por `tests/test_montaje.py`). Si algo del montaje cambia, se cambia ahí y se regeneran las guías (`python -m montaje.generar` y `python -m montaje.paginas`); nunca a mano en la protoboard sin anotarlo aquí.
- **Totales:** 188 cables definitivos, 63 cables de prueba, 10 integrados TTL. Resistencias permanentes: 8 de 220 Ω (LEDs), 8 de 330 Ω (serie del bus F) y 7 de 1 kΩ (reposo de CLEAR, SEL, los tres relojes, el reloj del PC y /LOAD del PC). Aparte van las 9 de 1 kΩ del banco de pruebas, que se retiran al cerrar la fase 4.

## Guías de montaje (artifacts)

| Guía | Link |
|---|---|
| Índice: plano completo, fases, colores y compras | https://claude.ai/artifact/3Et1w2RqYGTCZERfkgsorB |
| Fase 0: Preparación, base y alimentación | https://claude.ai/artifact/LBEYepv8NYrCCVcnSVbr9K |
| Fase 1: Etapa de salida: registro de salida, 74LS244 y 8 LEDs | https://claude.ai/artifact/WeFKZu5PRsN8ZTFX8wjgUm |
| Fase 2: ALU: dos 74LS181 en cascada | https://claude.ai/artifact/4PMaFtAbBHvTVFfcX48KMF |
| Fase 3: Registros A y B | https://claude.ai/artifact/4Tu72dRn3nBvR3QbLUSUzV |
| Fase 4: Multiplexor de entrada a A y contador de programa (PC) | https://claude.ai/artifact/2WNVRdJk6En1Y2xn3QmYfb |
| Fase 5: Arduino Mega | https://claude.ai/artifact/Xpejh7JomeKUjAvVGAAbzd |
| Fase 6: Cierre y verificación final | https://claude.ai/artifact/BetMDcMWtAQ57s2jDWBecG |

## Decisiones tomadas durante el montaje

| Fecha | Decisión | Por qué |
|---|---|---|
| 2026-09-17 | Etapa de salida (273 + 244 + LEDs) se arma **antes** que la ALU | Sus LEDs sirven de pantalla para probar ALU, registros y mux sin el Arduino |
| 2026-09-17 | 74LS181 en columnas d/h (DIP-24 de 600 mil) | Medido en físico: entre las dos filas de patas quedan 3 agujeros más el canal |
| 2026-09-17 | Pines 22/23 del 181: 23 = A1, 22 = B1 | Datasheet TI; §6.5 del registro de diseño los tenía cruzados (corregido) |
| 2026-09-17 | Colocación de chips por minimización de largo de cable | Búsqueda por coordenadas sobre filas y giro; 3633 → 3225 pasos de cable |
| 2026-09-19 | 5 resistencias de 1 kΩ de reposo en CLEAR, SEL y los tres relojes (fase 5) | Esos pines colgaban solo del Mega; quedan en alta impedancia al resetear y en cada carga de firmware, y una entrada TTL flotante conmuta con el ruido |
| 2026-09-19 | 8 resistencias de 330 Ω en serie en el bus F hacia el Mega (fase 5) | Si un pin del Mega quedara como `OUTPUT` habría contención contra la 74LS181; la resistencia la limita a ~15 mA en vez de quemar uno de los dos |
| 2026-09-25 | **PC físico: 2× 74LS161 en cascada** en BB1 (filas 32 y 44), montados en la fase 4 | El ingeniero no acepta el PC como variable del Arduino. Carga paralela desde el bus D (saltos), CLEAR compartido, Q → Mega A8–A15 (PORTK). Reloj en el pin 42 y /LOAD en el 43, con sus 1 kΩ de reposo. Ver §22 del registro de diseño |
| 2026-09-25 | Renumeración de cables desde la fase 1 (+4) al agregar el PC | Los cables #1–28 de la fase 0 no cambiaron, así que su avance marcado sigue válido. De la fase 1 en adelante no había nada marcado todavía |
|  |  |  |

## Fase 0 — Preparación, base y alimentación

**Guía:** https://claude.ai/artifact/LBEYepv8NYrCCVcnSVbr9K

- **Inicio:** 
- **Fin:** 
- **Última marca en la guía:** 2026-09-19
- **Estado:** 🟨 casi completa: falta la prueba 4 y la casilla de la fuente (ver abajo)

Avance leído de la guía el 2026-09-25:

- **Hecho:** preparación (6/6), los 28 cables, el capacitor C_ENT, el cierre (2/2) y las pruebas 1–3 y 5–8.
- **Sin marcar:** la prueba 4 (sin resultado anotado) y la pieza FUENTE.
- **Rieles puenteados:** la guía no lo registra. Anótalo aquí (lo pide el cierre de la fase).

### Resultados de la prueba

| # | Prueba | Esperado | Resultado | OK |
|---|---|---|---|---|
| 1 | Sin fuente, continuidad entre el + de BB1 (arriba) y el + de BB4 (abajo) | Pita | 5.14V (anotado así en la guía) | ✅ |
| 2 | Sin fuente, continuidad entre el − de BB1 y el − de BB4 | Pita | 5.14V (anotado así en la guía) | ✅ |
| 3 | Sin fuente, continuidad entre + y − (cualquier protoboard) | NO pita. Si pita, hay un corto: no conectes la fuente | 5.14V (anotado así en la guía) | ✅ |
| 4 | Conecta la fuente. Voltaje + a − en BB1, riel superior, fila 3 y fila 61 | 4.75 – 5.25 V |  | ⬜ |
| 5 | Igual en BB1 riel inferior | 4.75 – 5.25 V | 5.14 V | ✅ |
| 6 | Igual en BB2 (superior e inferior) | 4.75 – 5.25 V | 5.14 V | ✅ |
| 7 | Igual en BB3 (superior e inferior) | 4.75 – 5.25 V | 5.14 V | ✅ |
| 8 | Igual en BB4 (superior e inferior) | 4.75 – 5.25 V | 5.14 V | ✅ |

Las pruebas 1–3 son de continuidad (pita / no pita), pero en la guía quedó escrito "5.14V" en las tres; se marcaron como correctas. Conviene confirmar que se hicieron sin fuente.

### Problemas y soluciones

| Síntoma | Causa encontrada | Solución |
|---|---|---|
|  |  |  |

### Fotos

- 

## Fase 1 — Etapa de salida: registro de salida, 74LS244 y 8 LEDs

**Guía:** https://claude.ai/artifact/WeFKZu5PRsN8ZTFX8wjgUm

- **Inicio:** 
- **Fin:** 
- **Estado:** ⬜ pendiente

### Resultados de la prueba

| # | Prueba | Esperado | Resultado | OK |
|---|---|---|---|---|
| 1 | Conecta la fuente. Toca los chips con el dedo | Tibios como mucho. Si uno quema: desconecta y revisa su VCC/GND |  | ⬜ |
| 2 | Los 8 interruptores en OFF → presiona y suelta el pulsador | Los 8 LEDs encendidos (11111111) |  | ⬜ |
| 3 | Los 8 en ON → pulsa | Los 8 apagados (00000000) |  | ⬜ |
| 4 | Solo el interruptor 1 en OFF → pulsa | Solo el LED de la derecha (bit 0) |  | ⬜ |
| 5 | Solo el interruptor 8 en OFF → pulsa | Solo el LED de la izquierda (bit 7) |  | ⬜ |
| 6 | Recorre los interruptores 2 a 7 uno por uno, pulsando cada vez | Se enciende un solo LED que avanza de derecha a izquierda |  | ⬜ |
| 7 | Cambia interruptores sin pulsar | Los LEDs no cambian: el registro retiene |  | ⬜ |
| 8 | Multímetro en la salida del 244 de un LED encendido | ≈ 3.0 – 3.4 V |  | ⬜ |

### Problemas y soluciones

| Síntoma | Causa encontrada | Solución |
|---|---|---|
|  |  |  |

### Fotos

- 

## Fase 2 — ALU: dos 74LS181 en cascada

**Guía:** https://claude.ai/artifact/4PMaFtAbBHvTVFfcX48KMF

- **Inicio:** 
- **Fin:** 
- **Estado:** ⬜ pendiente

### Resultados de la prueba

| # | Prueba | Esperado | Resultado | OK |
|---|---|---|---|---|
| 1 | ADD 3+2 · A=00000011, B=00000010 · M=0 S3-S0=1001 C̄n=1 | LEDs 00000101 |  | ⬜ |
| 2 | ADD 15+1 · A=00001111, B=00000001 · igual control | LEDs 00010000 (el acarreo cruzó de ALU BAJA a ALTA) |  | ⬜ |
| 3 | ADD 255+1 · A=11111111, B=00000001 | LEDs 00000000 · C̄n+4 ALTA en bajo (hubo acarreo) |  | ⬜ |
| 4 | SUB 5−3 · A=00000101, B=00000011 · M=0 S=0110 C̄n=0 | LEDs 00000010 · anota C̄n+4 ALTA (alto/bajo) |  | ⬜ |
| 5 | SUB 3−5 · A=00000011, B=00000101 | LEDs 11111110 · anota C̄n+4 ALTA |  | ⬜ |
| 6 | SUB 5−5 · A=00000101, B=00000101 | LEDs 00000000 · anota C̄n+4 ALTA |  | ⬜ |
| 7 | AND · A=11001100, B=10101010 · M=1 S=1011 | LEDs 10001000 |  | ⬜ |
| 8 | OR · mismas A y B · M=1 S=1110 | LEDs 11101110 |  | ⬜ |
| 9 | XOR · mismas A y B · M=1 S=0110 | LEDs 01100110 |  | ⬜ |
| 10 | Pasar A · M=1 S=1111 | LEDs = A |  | ⬜ |
| 11 | Pasar B · M=1 S=1010 | LEDs = B |  | ⬜ |

### C.5 — nivel de C̄n+4 (pin 16, ALU ALTA) en SUB

| Caso | A ≥ B | Voltaje medido | Nivel | Lo que supone el firmware |
|---|---|---|---|---|
| 5 − 3 | sí |  |  | bajo |
| 3 − 5 | no |  |  | alto |
| 5 − 5 | sí |  |  | bajo |

**Conclusión C.5:** ⬜ pendiente (si los tres salen al revés: `CARRY_SUB_INVERTIDO 1` en `isa.h` y actualizar `contexto_proyecto.md` Parte C).

### Problemas y soluciones

| Síntoma | Causa encontrada | Solución |
|---|---|---|
|  |  |  |

### Fotos

- 

## Fase 3 — Registros A y B

**Guía:** https://claude.ai/artifact/4Tu72dRn3nBvR3QbLUSUzV

- **Inicio:** 
- **Fin:** 
- **Estado:** ⬜ pendiente

### Resultados de la prueba

| # | Prueba | Esperado | Resultado | OK |
|---|---|---|---|---|
| 1 | Dip = 10100101 · pulsador solo en CLK A · pulsa | Se carga A (todavía no se ve) |  | ⬜ |
| 2 | Control en Pasar A (M=1 S=1111) · pulsador solo en CLK de salida · pulsa | LEDs 10100101 |  | ⬜ |
| 3 | Dip = 01011010 · pulsador solo en CLK B · pulsa · luego Pasar B (S=1010) y pulsa CLK de salida | LEDs 01011010 |  | ⬜ |
| 4 | Cambia el dip sin pulsar CLK A ni CLK B · Pasar A y pulsa CLK de salida | LEDs siguen en 10100101: A retiene |  | ⬜ |
| 5 | Carga A=00000101 y B=00000011 · ADD (M=0 S=1001 C̄n=1) · pulsa CLK de salida | LEDs 00001000 |  | ⬜ |
| 6 | Pasa un momento el puente de CLEAR del riel + al − y regrésalo · Pasar A · pulsa CLK de salida | LEDs 00000000 (A, B y salida en cero) |  | ⬜ |

### Problemas y soluciones

| Síntoma | Causa encontrada | Solución |
|---|---|---|
|  |  |  |

### Fotos

- 

## Fase 4 — Multiplexor de entrada a A y contador de programa (PC)

**Guía:** https://claude.ai/artifact/2WNVRdJk6En1Y2xn3QmYfb

- **Inicio:** 
- **Fin:** 
- **Estado:** ⬜ pendiente

### Resultados de la prueba

| # | Prueba | Esperado | Resultado | OK |
|---|---|---|---|---|
| 1 | SEL en − · dip = 00000001 · pulsador solo en CLK A · pulsa | A = 1 |  | ⬜ |
| 2 | Pulsador en CLK B · pulsa | B = 1 (mismo dip) |  | ⬜ |
| 3 | ADD (M=0 S=1001 C̄n=1) · pulsador en CLK de salida · pulsa | LEDs 00000010 (A+B) |  | ⬜ |
| 4 | SEL en + · pulsador en CLK A · pulsa una vez | A = A + B = 2 |  | ⬜ |
| 5 | Pulsador en CLK de salida · pulsa | LEDs 00000011 |  | ⬜ |
| 6 | Repite: CLK A, luego CLK de salida, tres veces más | LEDs 00000100, 00000101, 00000110: el acumulador suma |  | ⬜ |
| 7 | PC: pasa un momento el puente de CLEAR de REG A del riel + al − y regrésalo | Las 8 Q de los dos 161 en 0 V |  | ⬜ |
| 8 | PC: dip = 10100101 · /LOAD en − · pulsador solo en CLK PC · pulsa · /LOAD en + | PC = 10100101 (carga paralela) |  | ⬜ |
| 9 | PC: dip = 00001111 · /LOAD en − · pulsa · /LOAD en + · pulsa otra vez | Q0 de PC ALTO (pin 14) en 1: pasó a 0001xxxx, la cascada funciona |  | ⬜ |
| 10 | PC: dip = 11111111 · /LOAD en − · pulsa · /LOAD en + · pulsa otra vez | Q de PC ALTO todo en 0: 0xFF + 1 dio la vuelta a 0x00 |  | ⬜ |

### Problemas y soluciones

| Síntoma | Causa encontrada | Solución |
|---|---|---|
|  |  |  |

### Fotos

- 

## Fase 5 — Arduino Mega

**Guía:** https://claude.ai/artifact/Xpejh7JomeKUjAvVGAAbzd

- **Inicio:** 
- **Fin:** 
- **Estado:** ⬜ pendiente

### Resultados de la prueba

| # | Prueba | Esperado | Resultado | OK |
|---|---|---|---|---|
| 1 | Monitor serial: STATE | Responde el bloque de estado (PC=0x00) |  | ⬜ |
| 2 | LOADB 0x00 0x30 0x55 0xB0 0xC0 y luego RUN (LDI A,#0x55 · OUT · HLT) | LEDs 01010101 |  | ⬜ |
| 3 | BORRAR, pega las 5 líneas de programas/referencia.load, RUN | LEDs 00001100 · traza 34 ciclos · A=0x0C · DETENIDO |  | ⬜ |
| 4 | LOAD 0xCC 0x09 · LOAD 0x05 0x07 · RESET · RUN (9 × 7) | LEDs 00111111 (63) |  | ⬜ |
| 5 | RESET y varios STEP | Avanza un microciclo por comando, igual que el simulador |  | ⬜ |
| 6 | STATE tras cada instrucción, y el multímetro en las Q de los 161 | El PC= del monitor es el mismo valor que marcan los 161 |  | ⬜ |

### Problemas y soluciones

| Síntoma | Causa encontrada | Solución |
|---|---|---|
|  |  |  |

### Fotos

- 

## Fase 6 — Cierre y verificación final

**Guía:** https://claude.ai/artifact/BetMDcMWtAQ57s2jDWBecG

- **Inicio:** 
- **Fin:** 
- **Estado:** ⬜ pendiente

### Resultados de la prueba

| # | Prueba | Esperado | Resultado | OK |
|---|---|---|---|---|
| 1 | Programa de referencia | LEDs 00001100 |  | ⬜ |
| 2 | Demo de instrucciones.md con datos que elija otra persona | LEDs = lo que da el simulador |  | ⬜ |
| 3 | python -m asm programas/demo_alu.asm --run y el mismo programa en la placa | Mismo resultado |  | ⬜ |

### Problemas y soluciones

| Síntoma | Causa encontrada | Solución |
|---|---|---|
|  |  |  |

### Fotos

- 

