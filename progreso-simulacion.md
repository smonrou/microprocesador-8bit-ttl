# Progreso — Simulación física en Proteus

> **Documento histórico (agosto–septiembre de 2026).** Registra la simulación en Proteus, no el estado actual. Desde entonces: la sintaxis de mnemónicos pasó a estilo x86 (2026-09-28), el PC pasó a hardware (2× 74LS161, 2026-09-25), el buffer de salida real es un 74LS240, el carry en SUB se midió en la placa (C.5, resuelto 2026-09-29) y el Mega ya corre en el hardware real (2026-10-01). Para el estado actual ver `montaje/bitacora_montaje.md`, `contexto_proyecto.md` y `CLAUDE.md`. Las menciones a PC/IR/MAR "como software", al display de 7 segmentos, a `DISPLAY_ANODO_COMUN` (que ya no existe) y a cifras de pruebas (713) describen el estado de aquel momento.

**Guía de referencia (instructivo de cómo se conectó todo):** https://claude.ai/code/artifact/d5bff553-693d-4422-a440-39ba9a54d675

## Ya definido / avanzado

- **Las dos ALU colocadas y cableadas en Proteus** (screenshot confirmado, verificado contra la guía):
  - `ALU BAJA` y `ALU ALTA` (74LS181) presentes, pinout correcto.
  - Control (S0-S3, M) compartido en paralelo entre las dos ALU.
  - Cadena de acarreo correcta: Arduino pin 44 → CN de ALU BAJA; CN+4 (pin16) de ALU BAJA → CN (pin7) de ALU ALTA, cable directo; CN+4 (pin16) de ALU ALTA → Arduino pin 2.
  - Bus F (8 líneas) cableado con el orden correcto (F0 de ALU BAJA → pin 37, no invertido).
  - Parte `ARDUINO MEGA2560` colocada.
- **[Guía completa de cableado ALU + banderas](https://claude.ai/code/artifact/d5bff553-693d-4422-a440-39ba9a54d675)** (artifact) con:
  - Pinout DIP-24 del 74LS181, tabla y diagrama.
  - Tabla de control (M/S3-S0/C̄n) para ADD/SUB/AND/OR/XOR + pasos A/B/NOT-A.
  - Mapeo completo Arduino↔ALU (15 pines: control x5, acarreo x2, bus F x8).
  - Banderas resueltas: C = físico (pin 2), Z = software (`F==0`, sin circuito).
  - BOM parcial (2× 74LS181, capacitores de desacople, fuente 5V).
- **Registros A y B (74LS273) colocados y cableados en Proteus** (confirmado por el usuario, cableado completo según la guía, D0-D7 de REG A dejados sueltos a propósito):
  - `REG A` y `REG B` (74LS273) presentes, pinout correcto.
  - Q0-Q7 de REG A → A0-A7 de las dos ALU (BAJA=A0-A3, ALTA=A4-A7) — resuelve los pines que quedaron sueltos en el bloque 1.
  - Q0-Q7 de REG B → B0-B7 de las dos ALU, mismo patrón.
  - Bus PORTA (Arduino pines 22-29) → D0-D7 de REG B, directo.
  - CLK A (pin 41) y CLK B (pin 40): líneas independientes, nunca compartidas.
  - CLEAR (pin 38): una señal, a REG A y REG B a la vez (clear asíncrono, activo en bajo).
- **[Guía completa de cableado de registros A y B](https://claude.ai/code/artifact/401ab472-6f27-4063-a4d9-b5c88d7be72e)** (artifact) con:
  - Pinout DIP-20 del 74LS273, tabla y diagrama.
  - Por qué REG A pasa por el mux 74LS157 y REG B no (camino de datos).
  - Mapeo completo REG A/B ↔ ALU (16 pines) y REG B ↔ Arduino (8 pines de PORTA).
  - Checklist acumulado de todas las conexiones del proyecto (bloques 1 y 2, hecho y pendiente).
- **Mux 74LS157 (bloque 3) colocado y cableado en Proteus** (confirmado por el usuario, cableado completo según la guía — cierra el pendiente de "D0-D7 de REG A sueltos" que dejó el bloque 2):
  - `MUX BAJO` y `MUX ALTO` (74LS157) presentes, pinout verificado contra el símbolo real de Proteus (E = pin 15, no pin 9 del datasheet genérico).
  - E (pin 15, habilitación) de los dos chips atado a GND del riel común (mismo GND que Arduino, ALU y registros).
  - SEL (pin 1, `Ā/B`) compartido entre los dos chips, cableado a Arduino pin 39 (`PIN_MUX`).
  - Entrada A (bus del Arduino, derivación de los mismos nodos que ya alimentan D0-D7 de REG B) y entrada B (bus F de la ALU, derivación de los mismos nodos que ya van a PORTC) cableadas a los 8 canales.
  - Salida Y (8 líneas) → D0-D7 de REG A.
- **[Guía completa de cableado del mux 74LS157](https://claude.ai/code/artifact/242e094d-c9b8-432a-8534-dbd6cff5e9e4)** (artifact) con:
  - Pinout DIP-16 del 74LS157, tabla y diagrama (MUX BAJO = bits 0-3, MUX ALTO = bits 4-7), verificado contra el símbolo real de Proteus.
  - Tabla de selección: SEL=LOW → entra el bus del Arduino (`MUX_BUS`), SEL=HIGH → entra F de la ALU (`MUX_ALU`), mapeado a `PIN_MUX` (39) en `hal.h`/`pines.h`.
  - Mapeo completo de las 3 entradas: bus del Arduino → pines A, bus F de la ALU → pines B, salida Y → D0-D7 de REG A.
  - BOM de esta etapa (2× 74LS157, 2× capacitor 0.1 µF) y checklist acumulado (bloques 1, 2 y 3).
- **[Guía de conexión del bloque 4 — unidad de control, reloj y RAM](https://claude.ai/code/artifact/85ad8879-d15f-47ea-b150-0e1d8b1c7523)** (artifact, aún no ejecutada) con:
  - Veredicto (*histórico*: el PC pasó luego a hardware con 2× 74LS161, 2026-09-25; IR, MAR y la memoria siguen en el Arduino): no hay chip nuevo — PC/IR/MAR/memoria de 256 B viven como software en el Arduino (`nucleo.h`), decisión confirmada contra `contexto_proyecto.md` A.1/A.2 y §3.3 de `proyecto_microprocesador_8bits.md`.
  - Paso a paso: resolver `DISPLAY_ANODO_COMUN` (ya eliminado del firmware) y `CARRY_SUB_INVERTIDO`, compilar y cargar el `.hex` en la parte `ARDUINO MEGA2560`, tabla de verificación del pinout de control (bloques 1-3), Virtual Terminal a 115200 baudios para `LOAD`/`RUN`/`STEP`, alimentación de los 6 chips, prueba aislada de la ALU.
  - Checklist acumulado (bloques 1-4) y ejemplo de carga del programa de referencia 4×3=12.
- **[Guía de conexión del display de 7 segmentos](https://claude.ai/code/artifact/57fd6ca5-5805-4eb8-98fa-0e4c54a9a9e1)** (artifact, aún no ejecutada) con:
  - Pinout fijo: segmentos a-g → Arduino 3-9, común dígito alto → pin 10, común dígito bajo → pin 11; 7 resistencias 220-330 Ω (no 14, compartidas entre dígitos).
  - Driver obligatorio: 1 transistor por dígito (2N3906 PNP si ánodo común, 2N2222 NPN si cátodo común) + resistencia de base 1 kΩ — un común conduce ~95 mA multiplexado, contra 40 mA máx. absoluto del pin Arduino.
  - Parte Proteus recomendada: `7SEG-MPX2-CA`/`7SEG-MPX2-CC` (multiplexada, 2 dígitos, calza con el diseño).
  - Decisión ánodo/cátodo sigue abierta (Parte C ítem 4) — la guía cubre ambas ramas y deja el default del firmware (`DISPLAY_ANODO_COMUN 1`) como recomendación para simular.
- **Bloque 4 ejecutado end-to-end en Proteus (2026-08-30) — el datapath completo calcula correctamente.** Sesión de depuración en vivo, 3 bugs reales encontrados y corregidos:
  1. **3 Arduinos "viejos" (snapshots de guías anteriores) seguían en el esquemático sin `Program File` configurado.** Proteus valida todas las partes AVR del proyecto al iniciar, no solo la activa → disparaba `AVR: Program property is not defined` + `Real Time Simulation failed to start`. Fix: excluir de la simulación (o borrar) los 3 Arduinos sin usar, dejar solo el configurado.
  2. **Protocolo serial no reconocía `\r` solo (sin `\n`).** La Virtual Terminal de Proteus manda `\r` al presionar Enter; el firmware original ignoraba `\r` (`continue`) y esperaba `\n`, que nunca llegaba → comandos se quedaban en el buffer sin ejecutarse nunca, sin error visible. **Fix aplicado en `firmware/microprocesador/consola.cpp`** (función `atender()`): ahora `\r` también dispara la ejecución de línea, igual que `\n` (seguro para terminales que mandan `\r\n` completo: el `\n` que sigue cae con buffer vacío y no reejecuta nada). **Hex recompilado con este fix — es el que está cargado en Proteus ahora.**
  3. **Bug de hardware real: `CN+4` (pin 16) de `ALU BAJA` no estaba conectado a `CN` (pin 7) de `ALU ALTA`.** Síntoma: el nibble alto (bits 4-7) de cualquier resultado de ALU salía corrupto (ej. `0x00+0x04` daba `0xF4` en vez de `0x04`) mientras el nibble bajo calculaba bien — clásico de un pin de control flotante en LS-TTL leyéndose como HIGH. Se diagnosticó leyendo el trace de `RUN` ciclo por ciclo (formato `imprimirBloqueYClaves` de `consola.cpp`) y comparando nibble por nibble contra el resultado esperado. **Fix: cable directo pin 16 de `ALU BAJA` → pin 7 de `ALU ALTA`** (la guía de Bloque 1 ya lo pedía; se había quedado sin poner).
  - **Resultado tras los 3 fixes:** el programa de referencia corre exactamente **34 ciclos** (el número calculado a mano: 4 init + 27 loop + 3 cierre) y termina en `PC=0x1C IR=0xC0(HLT) A=0x0C Z=1 C=1 DETENIDO` — **A=0x0C=12 es el resultado correcto de 4×3**. El cómputo del datapath (ALU+registros+mux+control) está verificado end-to-end.

## Pendiente

- [ ] Alimentación: VCC/GND + capacitor 0.1 µF en cada chip (ALU, registros y mux).
- [x] Cargar el `.hex` del firmware en la parte `ARDUINO MEGA2560` — hecho, con el fix de `\r` en `consola.cpp` incluido.
- [ ] Probar ALU aislada con interruptores DIP antes de integrar el Arduino (sección 07 de la guía 1) — se saltó este paso e igual se encontró el bug de la ALU por depuración en vivo del sistema integrado; sigue siendo recomendable hacerlo para futuras verificaciones.
- [x] Bloque 4: unidad de control / reloj / RAM (rol del Arduino) — ejecutado, firmware+terminal+cómputo funcionando.
- [x] **Bloque 5 — salida binaria de 8 dígitos: EJECUTADO Y FUNCIONANDO en Proteus (2026-09-04).** *(Reemplazado por el Bloque 5 v2 de LEDs, 2026-09-17.)* El `RUN` del programa de referencia muestra `0 0 0 0 1 1 0 0` en los ocho dígitos mientras la traza dice `salida=12` / `a=0x0C`. Dos hallazgos del montaje:
  1. **Los comunes del display se olvidan.** Los segmentos quedan cableados y vistosos, pero sin común no hay camino de corriente y no enciende absolutamente nada. Prueba de aislamiento: terminal GROUND directo en un común → ese dígito debe encender.
  2. **El buffer 74LS244 hace falta también en simulación.** Con cátodo común el segmento enciende en ALTO, y una salida LS-TTL en alto entrega ~0.4 mA: Proteus lo modela y el segmento no ilumina aunque la lógica sea correcta. La guía decía que se podía saltar en simulación — corregido.
- [x] ~~Bloque 5 — salida binaria de 8 dígitos (reemplaza al display hexadecimal).~~ El ingeniero rechazó la decodificación por software: si se muestra hexa, tiene que haber hardware que convierta. Se pasó a binario, donde no hay nada que convertir. Firmware ya modificado (sin tabla `PATRONES`, 5 pines en vez de 9, 713 tests en verde); falta ejecutarlo en Proteus. **[Guía de modificación del esquemático](https://claude.ai/code/artifact/582ca298-6c6b-4370-9563-68af19372823)** (artifact) con:
  - Chips nuevos: 74LS273 (registro de salida, engancha el bus F al ejecutar OUT), 74LS151 (mux 8:1 — `Y` = bit, `W` = complemento; ahí ocurre la "conversión"), 74LS138 (selección de dígito), buffer 74LS244/240, 2× `7SEG-MPX4-CC`/`CA`.
  - Tablas de cableado pin por pin de los cuatro chips + los 5 pines nuevos del Mega (3,4,5 = SEL; 6 = BLANK; 7 = CLK salida).
  - Atajo válido solo en simulación: con `7SEG-MPX4-CC` los comunes van directo del 138 (activo en bajo = cátodo activo), sin transistores; en placa real son obligatorios (~82 mA por común).
  - Tabla síntoma → causa y checklist de verificación; el `RUN` de referencia debe mostrar `0 0 0 0 1 1 0 0`.
  - **[Guía de montaje paso a paso](https://claude.ai/code/artifact/8c1e6db4-ea9c-4b13-be7f-a97e73c9d25d)** (artifact) — el procedimiento en 7 fases con un checkpoint verificable cada una (respaldo y demolición → firmware nuevo → etiquetas de red del bus F → 74LS273 con LOGICPROBE en `S0..S7` → 74LS151 → 74LS138 → displays), usando el `.hex` de `diagnostico_display` (barrido lento, 1 dígito/300 ms) para los checkpoints de bring-up y el real al final. Incluye rarezas de Proteus (pines VCC/GND ocultos, `Program property is not defined`, `\r` de la Virtual Terminal, entradas TTL flotantes).
- [x] ~~**Display no muestra `0C` aunque `A=0x0C` es correcto**~~ — sin efecto: ese bloque se eliminó del diseño (ver punto anterior). El bug quedó obsoleto junto con el display hexadecimal.
  <!-- diagnóstico original, por si el nuevo bloque presenta síntomas parecidos: -->
  <!-- El registro A tiene el valor correcto confirmado por `STATE`, así que el problema está entre el registro y el display visible, no en el cómputo. Posibles causas a revisar primero: coincidencia entre la rama elegida (ánodo/cátodo) del `7SEG-MPX2-CA/CC` colocado y el `#define DISPLAY_ANODO_COMUN` del firmware; conexión de los transistores driver (polaridad, base, colector/emisor); que el multiplexado esté corriendo (`display::refrescar()` se llama en cada `loop()`, si la CPU quedó `DETENIDO` en un bucle raro antes esto no corría — ya no debería ser el caso tras el fix del ALU); pines 3-9/10/11 realmente conectados como dice la guía del display. -->
- [x] ~~Tipo de display: ánodo o cátodo común~~ — **resuelto por eliminación (2026-09-17):** la salida pasó a 8 LEDs, ya no hay display.
- [ ] **Bloque 5 v2 — salida en 8 LEDs (decidido 2026-09-17, sin ejecutar en Proteus).** Quitar 74LS151, 74LS138, buffer de segmentos y los dos `7SEG-MPX4`; el 74LS273 de salida se queda. Nuevo: 74LS244 (Q0..Q7 del 273 → pines 2,4,6,8,11,13,15,17; salidas 18,16,14,12,9,7,5,3 → 220 Ω → LED → GND; 1G pin 1 y 2G pin 19 a GND). Pines 3–6 del Mega sin conectar, `.hex` sin cambios. Resultado esperado del `RUN` de referencia: encendidos solo los LEDs de los bits 3 y 2. Pasos en `simulacion_vs_fisico.md` §5; decisión en `proyecto_microprocesador_8bits.md` §21.
- [x] Verificación en banco real: semántica de carry en SUB (`CARRY_SUB_INVERTIDO`) — **resuelta el 2026-09-29 (C.5)**: se midió en la fase 2 del montaje, coincide con el diseño y `CARRY_SUB_INVERTIDO` queda en 0.
- [x] Simulación end-to-end en Proteus corriendo el programa de referencia (4×3=12) — **completa**: cómputo (`A=0x0C`, 34 ciclos, `DETENIDO`) y salida física en binario (`0 0 0 0 1 1 0 0`) confirmados en la misma corrida. El sistema entero funciona en simulación.
