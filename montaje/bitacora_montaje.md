# Bitácora del montaje físico

Registro de lo que realmente pasó al armar el microprocesador en las 4 protoboards: fechas, mediciones, resultados de cada prueba, problemas y cómo se resolvieron. Es la evidencia para la documentación y la defensa.

- **Guía paso a paso:** artifacts de la tabla de abajo. Las casillas y resultados que se marcan ahí se guardan en cada artifact; Claude puede leerlos y pasarlos aquí.
- **Fuente de verdad del cableado:** `montaje/netlist.py` (verificado por `tests/test_montaje.py`). Si algo del montaje cambia, se cambia ahí y se regeneran las guías (`python -m montaje.generar` y `python -m montaje.paginas`); nunca a mano en la protoboard sin anotarlo aquí.
- **Totales:** 188 cables definitivos, 63 cables de prueba, 10 integrados TTL. Resistencias permanentes: 8 de 330 Ω (LEDs), 8 de 330 Ω (serie del bus F) y 7 de 1 kΩ (reposo de CLEAR, SEL, los tres relojes, el reloj del PC y /LOAD del PC). Aparte van las 9 de 1 kΩ del banco de pruebas, que se retiran al cerrar la fase 4.

## Guías de montaje (artifacts)

| Guía | Link |
|---|---|
| Índice: plano completo, fases, colores y compras | https://claude.ai/artifact/4YDStVh8xM15Zxtyc1AgQE |
| Fase 0: Preparación, base y alimentación | https://claude.ai/artifact/Lz3Gcy2F6wgJpQeLqwysSF |
| Fase 1: Etapa de salida: registro de salida, 74LS240 y 8 LEDs | https://claude.ai/artifact/MhKsW5Wu5Zy6q6dgDhpyrZ |
| Fase 2: ALU: dos 74LS181 en cascada | https://claude.ai/artifact/FjTbYyfb3M2PRDjEggrfVo |
| Fase 3: Registros A y B | https://claude.ai/artifact/Tg8jgcV5L1cbpsGkFw6Jd4 |
| Fase 4: Multiplexor de entrada a A y contador de programa (PC) | https://claude.ai/artifact/9eajKKMk6WGTS7pKxnpGBx |
| Fase 5: Arduino Mega | https://claude.ai/artifact/U2PCDCou3fc7hgg4teGUCk |
| Fase 6: Cierre y verificación final | https://claude.ai/artifact/HiRFmeVUpYudrBvFQYKwLJ |

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
| 2026-09-28 | **Buffer de salida: 74LS240** en lugar del 74LS244 | Es el chip que se tiene en físico. Mismo pinout, pero invierte: cada LED va de +5 V a la salida (+5 V → LED → 330 Ω → Y del 240, puente rojo al riel +). El 240 hunde la corriente y el LED sigue encendiendo con bit = 1; sirve cualquier color |
| 2026-09-30 | **Relojes del acumulador y del PC desde el Mega** en las pruebas de la fase 4 (sketch `firmware/prueba_fase4/`) | El reloj manual (cable tocando el riel) rebota: con SEL en + un segundo flanco carga F a medio calcular y A toma valores al azar. Se adelantaron cables definitivos de la fase 5: GND, pin 41 → CLK A (BB2-h29), pin 7 → CLK S (BB4-h19), pin 42 → CLK PC (BB1-c33) y los 8 grises PC0–PC7 → A8–A15 |
|  |  |  |

## Fase 0 — Preparación, base y alimentación

**Guía:** https://claude.ai/artifact/Lz3Gcy2F6wgJpQeLqwysSF

- **Inicio:** 
- **Fin:** 
- **Última marca en la guía:** 2026-09-19
- **Estado:** ✅ completa (prueba 4 y fuente confirmadas el 2026-10-02)

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
| 4 | Conecta la fuente. Voltaje + a − en BB1, riel superior, fila 3 y fila 61 | 4.75 – 5.25 V | Correcto (confirmado el 2026-10-02) | ✅ |
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

## Fase 1 — Etapa de salida: registro de salida, 74LS240 y 8 LEDs

**Guía:** https://claude.ai/artifact/MhKsW5Wu5Zy6q6dgDhpyrZ

- **Inicio:** 
- **Fin:** 
- **Estado:** ✅ completa (confirmado el 2026-10-02)

### Resultados de la prueba

| # | Prueba | Esperado | Resultado | OK |
|---|---|---|---|---|
| 1 | Conecta la fuente. Toca los chips con el dedo | Tibios como mucho. Si uno quema: desconecta y revisa su VCC/GND | Correcto (confirmado el 2026-10-02) | ✅ |
| 2 | Los 8 interruptores en OFF → presiona y suelta el pulsador | Los 8 LEDs encendidos (11111111) | Correcto (confirmado el 2026-10-02) | ✅ |
| 3 | Los 8 en ON → pulsa | Los 8 apagados (00000000) | Correcto (confirmado el 2026-10-02) | ✅ |
| 4 | Solo el interruptor 1 en OFF → pulsa | Solo el LED de la derecha (bit 0) | Correcto (confirmado el 2026-10-02) | ✅ |
| 5 | Solo el interruptor 8 en OFF → pulsa | Solo el LED de la izquierda (bit 7) | Correcto (confirmado el 2026-10-02) | ✅ |
| 6 | Recorre los interruptores 2 a 7 uno por uno, pulsando cada vez | Se enciende un solo LED que avanza de derecha a izquierda | Correcto (confirmado el 2026-10-02) | ✅ |
| 7 | Cambia interruptores sin pulsar | Los LEDs no cambian: el registro retiene | Correcto (confirmado el 2026-10-02) | ✅ |
| 8 | Multímetro en la salida del 240 (pata Y) de un LED encendido, y luego de uno apagado | Encendido ≈ 0.2 – 0.5 V; apagado ≈ 3 V o más | Correcto (confirmado el 2026-10-02) | ✅ |

### Problemas y soluciones

| Síntoma | Causa encontrada | Solución |
|---|---|---|
|  |  |  |

### Fotos

- 

## Fase 2 — ALU: dos 74LS181 en cascada

**Guía:** https://claude.ai/artifact/FjTbYyfb3M2PRDjEggrfVo

- **Inicio:** 
- **Fin:** 
- **Estado:** ✅ completa: pruebas 1–11 correctas y C.5 resuelto (2026-09-29); cierre hecho y VCC de las ALU corregido (2026-10-02)

### Resultados de la prueba

| # | Prueba | Esperado | Resultado | OK |
|---|---|---|---|---|
| 1 | ADD 3+2 · A=00000011, B=00000010 · M=0 S3-S0=1001 C̄n=1 | LEDs 00000101 | 00000101 | ✅ |
| 2 | ADD 15+1 · A=00001111, B=00000001 · igual control | LEDs 00010000 (el acarreo cruzó de ALU BAJA a ALTA) | 00010000 | ✅ |
| 3 | ADD 255+1 · A=11111111, B=00000001 | LEDs 00000000 · C̄n+4 ALTA en bajo (hubo acarreo) | 00000000 · C̄n+4 = 0.11 V (bajo) | ✅ |
| 4 | SUB 5−3 · A=00000101, B=00000011 · M=0 S=0110 C̄n=0 | LEDs 00000010 · anota C̄n+4 ALTA (alto/bajo) | 00000010 · C̄n+4 = 0.118 V (bajo) | ✅ |
| 5 | SUB 3−5 · A=00000011, B=00000101 | LEDs 11111110 · anota C̄n+4 ALTA | 11111110 · C̄n+4 = 4.26 V (alto) | ✅ |
| 6 | SUB 5−5 · A=00000101, B=00000101 | LEDs 00000000 · anota C̄n+4 ALTA | 00000000 · C̄n+4 = 0.123 V (bajo) | ✅ |
| 7 | AND · A=11001100, B=10101010 · M=1 S=1011 | LEDs 10001000 | Hecha con A=10101010, B=11110000 (misma cobertura, B se mueve por bloques): 10100000 | ✅ |
| 8 | OR · mismas A y B · M=1 S=1110 | LEDs 11101110 | Con A=10101010, B=11110000: 11111010 | ✅ |
| 9 | XOR · mismas A y B · M=1 S=0110 | LEDs 01100110 | Con A=10101010, B=11110000: 01011010 | ✅ |
| 10 | Pasar A · M=1 S=1111 | LEDs = A | LEDs = A | ✅ |
| 11 | Pasar B · M=1 S=1010 | LEDs = B | LEDs = B | ✅ |

### C.5 — nivel de C̄n+4 (pin 16, ALU ALTA) en SUB

| Caso | A ≥ B | Voltaje medido | Nivel | Lo que supone el firmware |
|---|---|---|---|---|
| 5 − 3 | sí | 118.4 mV | bajo | bajo |
| 3 − 5 | no | 4.26 V | alto | alto |
| 5 − 5 | sí | 122.5 mV | bajo | bajo |

**Conclusión C.5:** ✅ resuelto (2026-09-29). Los tres casos coinciden con el firmware: C̄n+4 en bajo = no hubo préstamo (A ≥ B). `CARRY_SUB_INVERTIDO` se queda en `0`; `contexto_proyecto.md` Parte C actualizado.

### Problemas y soluciones

| Síntoma | Causa encontrada | Solución |
|---|---|---|
| Bits altos (4–7) siempre en 1 | Control de la ALU flotando: S2, S3 y el M de la ALU BAJA medían 1.3–1.5 V (entrada TTL al aire). La ALU quedaba en "Pasar A" y los LEDs copiaban el dip | Recableado del control (BB3 a8–a13) y de sus puentes temporales. Regla: cada pata de control mide < 0.4 V o > 4 V |
| Con la prueba del 0 (M=1 S=0011) salía 00001111 con C̄n=1 y 00000000 con C̄n=0 | ALU BAJA en modo aritmético (M=0, "menos 1") y ALU ALTA en lógico | Mismo arreglo del control; en modo lógico C̄n no debe influir |
| En ADD, parte alta siempre en 1111 | M de la ALU ALTA (d29) fijo en ≈4.65 V: no le llegaba el puente de M, así que calculaba A XNOR B | Recableado de a8–a13; d29 sigue al puente de M |
| Solo el bit 7 en 1; 255+1 daba 01111111 | Puentes de la zona de las filas 27/28 (A7 = j27 del dip, B7 = j28 al riel) mal colocados; B7 no seguía a su puente | Recolocados: j27 ← dip n.º 8, j28 → riel. Medido A7 = 4.86 V y B7 = 0.03 V con A=FF, B=01 |
| VCC en las ALU 4.62–4.65 V (mínimo LS: 4.75 V) | Caída por cableado/contactos bajo carga: los rieles daban 5.14 V en la fase 0 | Alimentación corregida antes de cerrar el montaje ✅ (2026-10-02) |

### Fotos

- 

## Fase 3 — Registros A y B

**Guía:** https://claude.ai/artifact/Tg8jgcV5L1cbpsGkFw6Jd4

- **Inicio:** 
- **Fin:** 
- **Estado:** ✅ pruebas 1–6 correctas (2026-09-29; 4–6 reportadas por el usuario sin detalle, como esperadas). Cierre: retirar los 8 cables dip → D de REG A (BB2-b44…b51 → a22, a23, a26, a27, j27, j26, j23, j22)

### Resultados de la prueba

| # | Prueba | Esperado | Resultado | OK |
|---|---|---|---|---|
| 1 | Dip = 10100101 · pulsador solo en CLK A · pulsa | Se carga A (todavía no se ve) | Cargó (verificado en la prueba 2) | ✅ |
| 2 | Control en Pasar A (M=1 S=1111) · pulsador solo en CLK de salida · pulsa | LEDs 10100101 | 10100101 | ✅ |
| 3 | Dip = 01011010 · pulsador solo en CLK B · pulsa · luego Pasar B (S=1010) y pulsa CLK de salida | LEDs 01011010 | Hecha con B=00001111 (01011010 es el complemento de A y confundía A con NOT B): 00001111 | ✅ |
| 4 | Cambia el dip sin pulsar CLK A ni CLK B · Pasar A y pulsa CLK de salida | LEDs siguen en 10100101: A retiene | 10100101 con dip en 11111111 | ✅ |
| 5 | Carga A=00000101 y B=00000011 · ADD (M=0 S=1001 C̄n=1) · pulsa CLK de salida | LEDs 00001000 | 00001000 | ✅ |
| 6 | Pasa un momento el puente de CLEAR del riel + al − y regrésalo · Pasar A · pulsa CLK de salida | LEDs 00000000 (A, B y salida en cero) | 00000000 | ✅ |

### Problemas y soluciones

| Síntoma | Causa encontrada | Solución |
|---|---|---|
| Sin pulsador físico | No se tiene el botón | Reloj manual con un cable en BB2-e55: tocar el riel − y retirarlo; el 273 carga al retirarlo (flanco de subida). Rebotes inofensivos en los 273 (recargan el mismo dato); en la fase 4 sí cuentan para el PC |
| Todos los LEDs encendidos al conectar la fuente | Normal: el 273 no se borra al encender | En la fase 5 el Mega activa CLEAR al arrancar |
| Los LEDs cambiaron al meter el cable del reloj de salida, sin pulsar | La punta estacionada no estaba en el riel + (quedó en 0): meterla al nodo en reposo (1) fue un flanco de subida | Estacionar los relojes que no se usan en el riel + (externo, raya roja) |
| Pasar A mostraba 11111101 en vez de 10100101 | El dip switch no estaba hundido por completo: sus interruptores no llegaban a las D de REG A (D3 medía 4.77 V con el interruptor en ON) | Dip presionado a fondo |
| Pasar B mostraba 10100101 (parecía A) | Alimentación de REG B mal puesta: B no cargaba. El valor de prueba 01011010 es el complemento de A, así que no se distinguía "muestra A" de "muestra NOT B" | Alimentación de REG B corregida (VCC pata 20 en f6, GND pata 10 en e15). Probado con B=00001111 → 00001111; el registro de salida se verificó antes con M=1 S=0011 → 00000000 |

### Fotos

- 

## Fase 4 — Multiplexor de entrada a A y contador de programa (PC)

**Guía:** https://claude.ai/artifact/9eajKKMk6WGTS7pKxnpGBx

- **Inicio:** 2026-09-30
- **Fin:** 
- **Estado:** ✅ completa: pruebas 1–10 correctas (2026-09-30); cierre hecho (2026-10-02). Los cables del Mega adelantados (GND, 41, 7, 42, grises A8–A15) son definitivos y se quedan

### Resultados de la prueba

| # | Prueba | Esperado | Resultado | OK |
|---|---|---|---|---|
| 1 | SEL en − · dip = 00000001 · pulsador solo en CLK A · pulsa | A = 1 | Cargó (verificado en la 3) | ✅ |
| 2 | Pulsador en CLK B · pulsa | B = 1 (mismo dip) | Cargó (verificado en la 3) | ✅ |
| 3 | ADD (M=0 S=1001 C̄n=1) · pulsador en CLK de salida · pulsa | LEDs 00000010 (A+B) | 00000010 (tras poner los amarillos que faltaban; antes 11001110) | ✅ |
| 4 | SEL en + · pulsador en CLK A · pulsa una vez | A = A + B = 2 | Con reloj manual: valores al azar (rebote). Con el Mega (`P`): correcto | ✅ |
| 5 | Pulsador en CLK de salida · pulsa | LEDs 00000011 | 00000011 (reloj del Mega) | ✅ |
| 6 | Repite: CLK A, luego CLK de salida, tres veces más | LEDs 00000100, 00000101, 00000110: el acumulador suma | 00000100, 00000101, 00000110; recorrido completo 00000000 → 11111111 de uno en uno | ✅ |
| 7 | PC: pasa un momento el puente de CLEAR de REG A del riel + al − y regrésalo | Las 8 Q de los dos 161 en 0 V | Monitor: PC = 0000 0000 | ✅ |
| 8 | PC: dip = 10100101 · /LOAD en − · pulsador solo en CLK PC · pulsa · /LOAD en + | PC = 10100101 (carga paralela) | 0xA5 (reloj del Mega, pin 42; lectura por A8–A15) | ✅ |
| 9 | PC: dip = 00001111 · /LOAD en − · pulsa · /LOAD en + · pulsa otra vez | Q0 de PC ALTO (pin 14) en 1: pasó a 0001xxxx, la cascada funciona | 0x0F → 0x10 exacto | ✅ |
| 10 | PC: dip = 11111111 · /LOAD en − · pulsa · /LOAD en + · pulsa otra vez | Q de PC ALTO todo en 0: 0xFF + 1 dio la vuelta a 0x00 | 0xFF → 0x00 exacto; luego cuenta 0x01 → 0x22 de uno en uno | ✅ |

### Verificación estática del lazo F → mux → REG A (SEL en +, sin pulsar)

A cargada desde el dip con SEL en −, B = 1, ALU en ADD; luego SEL en + y se mide entrada B del mux, salida Y y D de REG A.

| Estado | A | F esperado | Resultado |
|---|---|---|---|
| E1 | 00000101 | 00000110 | ✅ (entradas B: bit 1 4.42 V, bit 2 4.43 V, el resto 0.06–0.18 V) |
| E2 | 00001010 | 00001011 | ✅ |
| E3 | 11101111 | 11110000 | ❌ 01000000 → naranjas de los bits 4 y 7 cruzados (D4 4.90 V con Y4 = 0.15 V; D7 0.18 V con Y7 = 4.92 V). ✅ tras corregir |

Control medido: SEL 4.92 V (MUX BAJO) y 4.91 V (MUX ALTO) en +, G̅ 0.9 mV y 0.2 mV, CLEAR de REG A 4.88 V.

### Problemas y soluciones

| Síntoma | Causa encontrada | Solución |
|---|---|---|
| Prueba 3 daba 11001110; bits 2, 3, 6 y 7 de A siempre en 1 | Faltaban cables amarillos REG B D → entradas A del mux (canales 3 y 4): entradas al aire leen 1 | Amarillos puestos |
| E3 daba 01000000 en vez de 11110000 | Naranjas de los bits 4 y 7 intercambiados: MUX ALTO 1Y llegaba a D7 y 4Y a D4 | BB1-a23 → BB2-j27 (bit 4) y BB1-j24 → BB2-j22 (bit 7); comprobado por continuidad |
| Acumulador (SEL en +) con valores al azar, incluso bajando, aunque el cableado medía bien en estático | Rebote del reloj manual: un segundo flanco a los pocos ns carga F mientras la ALU todavía propaga el acarreo. Con SEL en − no se nota porque la D no cambia | Relojes desde el Mega (sketch `firmware/prueba_fase4/`): suma exacta de 0 a 255 |
| Monitor siempre en PC = 0000 0000 | Fuente de la protoboard desconectada (el Mega estaba alimentado por USB) | Conectar la fuente |
| El PC parecía regresar 8 posiciones (0x37 → 0x30, 0x0F leído 0x07) | Bit 3 (PC3, BB1-j37 → Mega A11) no llegaba al Mega: A11 flotaba. El contador sí contaba bien (llegaba a 0x40) | Cable gris de PC3 corregido; cuenta 0x01 → 0x22 sin saltos |

### Fotos

- 

## Fase 5 — Arduino Mega

**Guía:** https://claude.ai/artifact/U2PCDCou3fc7hgg4teGUCk

- **Inicio:** 
- **Fin:** 
- **Estado:** ✅ completa: cableado verificado con `prueba_fase5` (`T` = TODO OK), prueba 3 (referencia) correcta el 2026-10-01 y pruebas 1, 2, 4, 5 y 6 correctas (2026-10-02). Los temporales de las fases 2 y 4 ya se retiraron

### Resultados de la prueba

| # | Prueba | Esperado | Resultado | OK |
|---|---|---|---|---|
| 1 | Monitor serial: STATE | Responde el bloque de estado (PC=0x00) | Correcto (confirmado el 2026-10-02) | ✅ |
| 2 | LOADB 0x00 0x30 0x55 0xB0 0xC0 y luego RUN (MOV A,0x55 · OUT · HLT) | LEDs 01010101 | Correcto (confirmado el 2026-10-02) | ✅ |
| 3 | BORRAR, pega las 5 líneas de programas/referencia.load, RUN | LEDs 00001100 · traza 34 ciclos · A=0x0C · DETENIDO | Funcionó correctamente (2026-10-01), tras `prueba_fase5` `T` = TODO OK dos veces seguidas | ✅ |
| 4 | LOAD 0xCC 0x09 · LOAD 0x05 0x07 · RESET · RUN (9 × 7) | LEDs 00111111 (63) | Correcto (confirmado el 2026-10-02) | ✅ |
| 5 | RESET y varios STEP | Avanza un microciclo por comando, igual que el simulador | Correcto (confirmado el 2026-10-02) | ✅ |
| 6 | STATE tras cada instrucción, y el multímetro en las Q de los 161 | El PC= del monitor es el mismo valor que marcan los 161 | Correcto (confirmado el 2026-10-02) | ✅ |

### Problemas y soluciones

| Síntoma | Causa encontrada | Solución |
|---|---|---|
| 2026-10-01: `demo_alu.load` corre, pero `referencia.load` y `demo_multiplicacion.load` nunca llegan al HLT. En la traza, el primer conteo del PC va de 0x00 a **0x11** (el operando sale de Mem[0x11] = 0x40) y desde ahí todo corre desplazado 0x10. A se carga con 0x40 y se lee **0x50**; B vale **0x40** aunque nadie la cargó. Al arrancar, justo después del CLEAR, el PC ya leía 0x11 | Resuelto el 2026-10-01 (ver las filas siguientes). Diagnóstico inicial: `prueba_fase5` `T` (2026-10-01): pines del Mega, lectura de F y lectura y conteo del PC **OK** (pruebas 1–3 y 7). Fallan las entradas de la placa: tras CLEAR con el bus en 0xFF, B se lee 0x40, así que B6 del 181 parece tomar el bus D6 y no REG B Q6. También fallan los bits 4–5 de B, el bit 5 de A y P2/P5 del PC al cargar. SUB 0x40−0x40 da 0xD0, Z nunca es 1 y el JNZ no termina. Mapa (prueba 10): ALU ALTA B0 fijo en 1 → el blanco #141 (BB2-j14 → BB3-a22) está suelto, o sigue puesto el temporal #119 de la fase 2 (BB3-a22 → riel +). B1 sigue a REG B Q6 y B2 al bus D6 → los blancos #143 y #145 están un agujero corridos en REG B (j10 y j9 en vez de j11 y j10). ALU ALTA A1 sigue a REG A Q4 y A0 no sigue a nada → verdes #140/#142 mal en la fila 23 de BB3. PC ALTO P0 al aire y P1 sigue a D4 → amarillo #199 en BB1-a47 en vez de a46, #200 suelto. PC BAJO P2 sin señal fija → #197 con falso contacto | Hipótesis inicial (la causa real quedó en las filas siguientes): reasentar #141 (o retirar #119 si sigue ahí), mover #143 a BB2-j11 y #145 a BB2-j10, dejar #140 en BB3-a23 y #142 en BB3-j23, #199 a BB1-a46 y #200 a BB1-a47, reasentar #197. Repetir `T` |
| 2.ª corrida de `T` (tras mover #143/#145 y reasentar): B2 y PC BAJO P2 ya bien. Siguen: ALU ALTA A0, B0 y PC ALTO P0 (los tres de bit 4) fijos en 1 en el mapa, pero bien en las pruebas 5 y 8; A1 sigue a REG A Q4; B1 sigue al bus D5 | Bit 4 en tres chips a la vez y de forma intermitente → sospecha del bus D4 (Mega pin 26, #217 → BB2-j13). B1 → #143 en la fila 12 en vez de la 11. A1 → por medir con continuidad | Resuelto en las corridas 3.ª–6.ª |
| 3.ª y 4.ª corridas: el Mega pin 27 (D5) estaba en BB2-j11, la fila de REG B Q5 → B1 tomaba el bus D5. Corregido a j12, y quedó bien todo el nibble alto. Gris #249 (PC6 → A14) reasentado. Después fallan ALU BAJA A0/A1 y PC BAJO P0/P1 (falso contacto), y 5+3 da 0xF8 de forma intermitente | Bits 0–1 de A y del PC a la vez, con REG B bien → amarillos #171/#174 (bus D0/D1 → MUX BAJO 1A/2A). 0xF8 = nibble alto en XNOR → la ALU ALTA no recibe M a veces: puente morado #100 (BB3-a13 → a29), el mismo punto que en la fase 2 | Reasentar #171/#174 y #100. `prueba_fase5` ahora repite 200 veces la prueba del M de las dos ALU y prueba el acarreo entre ellas |
| 5.ª corrida, tras reasentar: siguen A0/A1 y P0/P1 (A0 y P0 ya fijos en 1). La ALU ALTA ve M=1 en las 200 lecturas (5+3 = 0xF9) | #171 no llega a la fila 9 de BB1 (MUX BAJO 1A) y #174 hace mal contacto. La prueba del M se rehízo con M=0 S=0011, que no depende de A ni de B. Con ella, las **dos** ALU ven M=1 (5+3 = 0xF9 = 5 XNOR 3; 0x40−0x40 = 0x01 = 0x41 XOR 0x40) → el cable del Mega pin 45 no llega a la línea M (BB3-b13), que flota en 1. La prueba anterior ya lo decía; se descartó por error como falsa alarma | Medir continuidad pata a pata y cambiar los cables que no pasen |
| 6.ª corrida: el Mega pin 45 no hacía contacto del lado de BB3 → corregido; el control de las dos ALU y el acarreo quedan bien (200/200). Solo quedan A0/A1 y P0/P1 | Bus D0/D1 → MUX BAJO 1A/2A (#171, #174) | Corregido (2026-10-01): `T` = TODO OK dos veces seguidas y `referencia.load` funciona. **Regla:** después de tocar la placa, subir `firmware/prueba_fase5/` y correr `T` antes de cualquier programa |

### Fotos

- 

## Fase 6 — Cierre y verificación final

**Guía:** https://claude.ai/artifact/HiRFmeVUpYudrBvFQYKwLJ

- **Inicio:** 
- **Fin:** 
- **Estado:** ✅ completa (confirmado el 2026-10-02)

### Resultados de la prueba

| # | Prueba | Esperado | Resultado | OK |
|---|---|---|---|---|
| 1 | Programa de referencia | LEDs 00001100 | Correcto (confirmado el 2026-10-02) | ✅ |
| 2 | Demo de instrucciones.md con datos que elija otra persona | LEDs = lo que da el simulador | Correcto (confirmado el 2026-10-02) | ✅ |
| 3 | python -m asm programas/demo_alu.asm --run y el mismo programa en la placa | Mismo resultado | Correcto (confirmado el 2026-10-02) | ✅ |

### Problemas y soluciones

| Síntoma | Causa encontrada | Solución |
|---|---|---|
|  |  |  |

### Fotos

- 

