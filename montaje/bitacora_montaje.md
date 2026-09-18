# Bitácora del montaje físico

Registro de lo que realmente pasó al armar el microprocesador en las 4 protoboards: fechas, mediciones, resultados de cada prueba, problemas y cómo se resolvieron. Es la evidencia para la documentación y la defensa.

- **Guía paso a paso:** artifacts de la tabla de abajo. Las casillas y resultados que se marcan ahí se guardan en cada artifact; Claude puede leerlos y pasarlos aquí.
- **Fuente de verdad del cableado:** `montaje/netlist.py` (verificado por `tests/test_montaje.py`). Si algo del montaje cambia, se cambia ahí y se regeneran las guías (`python -m montaje.generar` y `python -m montaje.paginas`); nunca a mano en la protoboard sin anotarlo aquí.
- **Totales:** 158 cables definitivos, 61 cables de prueba, 8 integrados TTL.

## Guías de montaje (artifacts)

| Guía | Link |
|---|---|
| Índice: plano completo, fases, colores y compras | https://claude.ai/artifact/3Et1w2RqYGTCZERfkgsorB |
| Fase 0: Preparación, base y alimentación | https://claude.ai/artifact/LBEYepv8NYrCCVcnSVbr9K |
| Fase 1: Etapa de salida: registro de salida, 74LS244 y 8 LEDs | https://claude.ai/artifact/WeFKZu5PRsN8ZTFX8wjgUm |
| Fase 2: ALU: dos 74LS181 en cascada | https://claude.ai/artifact/4PMaFtAbBHvTVFfcX48KMF |
| Fase 3: Registros A y B | https://claude.ai/artifact/4Tu72dRn3nBvR3QbLUSUzV |
| Fase 4: Multiplexor de entrada a A | https://claude.ai/artifact/2WNVRdJk6En1Y2xn3QmYfb |
| Fase 5: Arduino Mega | https://claude.ai/artifact/Xpejh7JomeKUjAvVGAAbzd |
| Fase 6: Cierre y verificación final | https://claude.ai/artifact/BetMDcMWtAQ57s2jDWBecG |

## Decisiones tomadas durante el montaje

| Fecha | Decisión | Por qué |
|---|---|---|
| 2026-09-17 | Etapa de salida (273 + 244 + LEDs) se arma **antes** que la ALU | Sus LEDs sirven de pantalla para probar ALU, registros y mux sin el Arduino |
| 2026-09-17 | 74LS181 en columnas d/h (DIP-24 de 600 mil) | Medido en físico: entre las dos filas de patas quedan 3 agujeros más el canal |
| 2026-09-17 | Pines 22/23 del 181: 23 = A1, 22 = B1 | Datasheet TI; §6.5 del registro de diseño los tenía cruzados (corregido) |
| 2026-09-17 | Colocación de chips por minimización de largo de cable | Búsqueda por coordenadas sobre filas y giro; 3633 → 3225 pasos de cable |
|  |  |  |

## Fase 0 — Preparación, base y alimentación

**Guía:** https://claude.ai/artifact/LBEYepv8NYrCCVcnSVbr9K

- **Inicio:** 
- **Fin:** 
- **Estado:** ⬜ pendiente

### Resultados de la prueba

| # | Prueba | Esperado | Resultado | OK |
|---|---|---|---|---|
| 1 | Sin fuente, continuidad entre el + de BB1 (arriba) y el + de BB4 (abajo) | Pita |  | ⬜ |
| 2 | Sin fuente, continuidad entre el − de BB1 y el − de BB4 | Pita |  | ⬜ |
| 3 | Sin fuente, continuidad entre + y − (cualquier protoboard) | NO pita. Si pita, hay un corto: no conectes la fuente |  | ⬜ |
| 4 | Conecta la fuente. Voltaje + a − en BB1, riel superior, fila 3 y fila 61 | 4.75 – 5.25 V |  | ⬜ |
| 5 | Igual en BB1 riel inferior | 4.75 – 5.25 V |  | ⬜ |
| 6 | Igual en BB2 (superior e inferior) | 4.75 – 5.25 V |  | ⬜ |
| 7 | Igual en BB3 (superior e inferior) | 4.75 – 5.25 V |  | ⬜ |
| 8 | Igual en BB4 (superior e inferior) | 4.75 – 5.25 V |  | ⬜ |

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

## Fase 4 — Multiplexor de entrada a A

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

