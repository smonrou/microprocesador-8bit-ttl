# Simulación en Proteus vs. montaje físico

> Actualizado al diseño vigente (2026-09-17, con las correcciones del montaje hasta 2026-10-01): salida en **8 LEDs** (registro de salida 74LS273 → buffer → LEDs; el diseño decía 74LS244 y **el montaje real usa un 74LS240**, 2026-09-28), **10 integrados TTL** (el PC pasó a 2× 74LS161 el 2026-09-25), entrega **en protoboards**. Ver `contexto_proyecto.md` A.2 y `proyecto_microprocesador_8bits.md` §13.4/§21 para el detalle de cada decisión.

Este documento responde dos preguntas: **qué simplifica Proteus** (para no confiarse de que "si corrió en la simulación, ya está") y **qué hace falta comprar/agregar** que la simulación no exige.

⚠️ **La simulación de Proteus todavía tiene la salida anterior** (74LS151 + 74LS138 + 2 displays). Hay que pasarla a LEDs (sección 5) para que vuelva a ser idéntica al montaje.

---

## 1. Qué NO existe en Proteus (idealizaciones del simulador)

Proteus es un simulador ideal: varias cosas que en físico son obligatorias, en la simulación no hacen falta o se pueden posponer sin que nada se queje.

| Elemento | Por qué no hace falta en Proteus |
|---|---|
| Protoboard | El propio esquemático es "la placa" — no hay nada físico que insertar |
| Fuente 5V regulada real | Los terminales `POWER`/`GROUND` son ideales: sin caída de tensión, sin límite de corriente, sin ruido |
| Multímetro | Se lee todo con sondas virtuales (`LOGICPROBE`), instantáneas y sin margen de error |
| Jumpers físicos | Todo el cableado es lógico, en pantalla |
| Capacitores de desacople (0.1 µF por chip) | Proteus no modela los picos de corriente al conmutar un TTL; sin ellos no falla nada en simulación, pero en físico causan fallos intermitentes que parecen error de lógica |
| Pines VCC/GND de cada chip | Proteus los conecta de forma implícita (pines ocultos). En la protoboard cada chip necesita sus dos cables de alimentación, y olvidarlos es el error más común |

⚠️ **Lo que Proteus SÍ modela, y por eso no se puede saltar ni en simulación:** el buffer de salida (74LS244 en el diseño, 74LS240 en el montaje). Una salida LS-TTL del 273 entrega ~0.4 mA en alto — insuficiente para un LED — y Proteus refleja esa corriente real (ya pasó con los segmentos del diseño anterior). Sin el buffer, el LED no enciende en la simulación tampoco.

---

## 2. Qué es idéntico entre simulación y físico

- **Los 10 integrados TTL** (tabla completa en la sección 4) y su cableado punto a punto.
- **El firmware** — el mismo `.hex` compilado de `firmware/microprocesador/` se carga en el Arduino de Proteus y en el Arduino real, sin cambios.
- **El protocolo serial** (`LOAD`, `LOADB`, `RUN`, `STEP`, …) a 115200 baudios.
- **El programa de referencia** (4×3=12) y el resultado esperado: los ocho LEDs deben mostrar `0 0 0 0 1 1 0 0` (encendidos solo los bits 3 y 2).

---

## 3. Diferencias, elemento por elemento

| Elemento | En Proteus | En físico (obligatorio) |
|---|---|---|
| Alimentación de cada chip | Implícita (pines ocultos) | Cable a VCC y a GND en cada uno de los 10 chips. 74LS244/74LS240: VCC pin 20, GND pin 10. 74LS161: VCC pin 16, GND pin 8 |
| Habilitaciones del buffer (244/240) | Conviene atarlas igual | 1G (pin 1) y 2G (pin 19) **a GND**. Sueltas se leen como alto y los LEDs quedan apagados (con el 240 quedarían desconectados) |
| LEDs de salida | Parte `LED-RED` (o cualquier color) | Con el **74LS240 (montaje real)** cada LED va de +5 V a la salida del chip (+5 V → LED → 330 Ω → Y): el 240 invierte y hunde la corriente, así que sirve cualquier color y el LED enciende con bit = 1. Con el 244 (diseño original) hacen falta **rojos, verdes o amarillos**: en alto da 2.4–3.4 V y a un LED azul o blanco (~3 V) no le queda corriente |
| Resistencias en serie del bus F hacia el Mega | No hacen falta | 8 resistencias de 330 Ω entre el bus F y los pines PORTC del Mega: si un pin quedara como `OUTPUT` habría contención contra el 74LS181, y la resistencia limita la corriente a ~15 mA |
| Resistencias de reposo | No hacen falta | 7 de 1 kΩ permanentes (CLEAR, SEL, los tres relojes, el reloj del PC y /LOAD del PC): sin ellas esos pines quedan flotando mientras el Mega se resetea o se carga |
| Capacitores de desacople (0.1 µF) | Opcionales (no rompen nada si faltan) | Obligatorios: 1 por cada uno de los 10 chips TTL, lo más cerca posible del pin VCC |
| Capacitor electrolítico de entrada | No aplica | 1× 10–100 µF en la entrada de alimentación general |
| Fuente de alimentación | Terminales ideales `POWER`/`GROUND` | Fuente 5V regulada, **mínimo 1 A** — el pin 5V del Mega da ~500 mA. GND común con el Arduino es obligatorio |
| Banco de montaje | No aplica | 4 protoboards de 830 puntos sobre base rígida. **Son el entregable** (el ingeniero lo aceptó el 2026-09-17) |
| Verificación | Sondas virtuales, instantáneas | Multímetro, indispensable para continuidad y niveles lógicos; pinzas de punta fina; extractor de CI (opcional) |
| Depuración manual de la ALU | No hace falta: se corre y se lee el resultado | Dip switch de 8 + LEDs de depuración, para caracterizar el 74LS181 aislado antes de integrar (recomendado, se saltó una vez y costó una sesión de debug en vivo) |
| Reset / clock manual | `RESET` por comando serial | Pulsador (push button) físico, para pruebas de banco |
| Repuestos | No aplica | 1–2 unidades de cada integrado — los TTL se dañan con polaridad invertida o estática, y descubrirlo sin repuesto días antes de la entrega es el escenario más común |

---

## 4. Lista de materiales completa para el montaje físico

### Integrados (10 TTL + Arduino)

| Cant. | Componente | Función |
|---|---|---|
| 2 | SN74LS181 | ALU en cascada 4+4 bits |
| 2 | 74LS273 | Registros A y B |
| 1 | 74LS273 | Registro de salida (engancha el bus F al ejecutar `OUT`) |
| 2 | 74LS157 | Mux de entrada al registro A |
| 2 | 74LS161 | Contador de programa (PC) de 8 bits en cascada. Ya en existencia (2026-09-25) |
| 1 | 74LS240 (montaje real; el diseño decía 74LS244) | Buffer de corriente de los 8 LEDs de salida. Es el chip que se tenía en físico: mismo pinout que el 244 pero invierte, así que cada LED se cablea de +5 V a la salida (5V → LED → 330 Ω → Y). Con un 74LS244 los LEDs van al revés (salida → 220 Ω → LED → GND) |
| 1 | Arduino Mega 2560 | Unidad de control, memoria (256 B) y reloj. Lee el PC por A8–A15 |
| 1–2 | Repuestos de cada tipo | Los TTL se dañan con estática o polaridad invertida |

### Salida

| Cant. | Componente | Notas |
|---|---|---|
| 8 | LEDs de 3 o 5 mm, **rojos, verdes o amarillos** | Uno por bit, bit 7 a la izquierda. No azules ni blancos |
| 8 | Resistencias 330 Ω | Una por LED, en serie con la salida del 74LS240 (así está en `montaje/netlist.py`). Con un 244 serían 220 Ω (150 Ω si se ven tenues) |
| 8 | Resistencias 330 Ω | Serie del bus F hacia el Mega (ver la sección 3) |

### Alimentación

| Cant. | Componente | Notas |
|---|---|---|
| 1 | Fuente 5V regulada, mínimo 1 A | No alimentar todo desde el Arduino |
| 10 | Capacitores cerámicos 0.1 µF | Desacople, uno por cada integrado TTL |
| 1 | Capacitor electrolítico 10–100 µF | Entrada de alimentación general |

### Banco de pruebas y montaje

| Cant. | Componente | Notas |
|---|---|---|
| 4 | Protoboards de 830 puntos | El entregable. Distribución y cableado en `montaje/` |
| 1 | Base de MDF o acrílico ~35 × 25 cm + 4 separadores M3 de 10 mm | Fija las protoboards y el Mega |
| — | Cable sólido 22 AWG en 10 colores (metros por color en la guía de montaje) | Cableado definitivo, un color por función |
| 20+ | LEDs (varios colores) | Depuración de buses y registros |
| 30+ | Resistencias 220–330 Ω | Limitar corriente en LEDs de depuración (aparte de las 8 + 8 de 330 Ω de arriba) |
| 9 | Resistencias 1 kΩ | Pull-ups del dip switch (8) y del pulsador (1) del banco de pruebas |
| 7 | Resistencias 1 kΩ | Permanentes (fase 5): reposo de CLEAR, SEL, los tres relojes, el reloj del PC y /LOAD del PC |
| 1 | Dip switch de 8 | Caracterización manual de la ALU |
| 1 | Pulsador (push button) | Reset / clock manual |
| — | Dupont macho-macho | **Solo** cables de prueba de las fases 1–4; el cableado final (incluido el del Mega) es 22 AWG sólido |
| 1 | Multímetro | Indispensable |
| — | Pinzas de punta fina, extractor de CI | El extractor es opcional |

Ya **no** hacen falta (eran del diseño anterior; el montaje real no lleva ninguno): 74LS151, 74LS138, displays de 7 segmentos, 8 transistores de dígito, 8 resistencias de base, placa perforada, cautín ni estaño.

---

## 5. Cambio pendiente en Proteus

Para que la simulación vuelva a ser idéntica al montaje (el montaje usa 74LS240; el paso 3 describe el 244 del diseño original, y para igualar el físico se invierte la polaridad de los LEDs como en la sección 3):

1. Respaldar el proyecto.
2. Borrar el 74LS151, el 74LS138, el buffer de segmentos y los dos `7SEG-MPX4`. El 74LS273 de salida **se queda**, con su CLK (pin 7 del Mega) y su CLEAR.
3. Colocar el buffer (74LS244 del diseño; el montaje usa 74LS240, mismo pinout): Q0..Q7 del 273 de salida → 1A1, 1A2, 1A3, 1A4, 2A1, 2A2, 2A3, 2A4 (pines 2, 4, 6, 8, 11, 13, 15, 17). 1G (pin 1) y 2G (pin 19) a GND.
4. Salidas 1Y1, 1Y2, 1Y3, 1Y4, 2Y1, 2Y2, 2Y3, 2Y4 (pines 18, 16, 14, 12, 9, 7, 5, 3) → resistencia 220 Ω → LED → GND, uno por bit.
5. Los pines 3–6 del Mega quedan sin conectar. El `.hex` no cambia.
6. `RUN` del programa de referencia → deben quedar encendidos solo los LEDs de los bits 3 y 2.

---

## 6. Orden de compra sugerido

1. **Para caracterizar la ALU ya** (no depende de nada más): dip switch, LEDs, resistencias, protoboard, fuente. Los 74LS181 ya están comprados.
2. **Para el montaje completo** (el Arduino Mega ya está comprado y en uso desde 2026-10-01): 74LS273 (×3), 74LS157 (×2), 74LS161 (×2), 74LS240 (o 244), 8 LEDs de salida + 8 resistencias de salida (330 Ω con el 240), 8 de 330 Ω del bus F, 7 de 1 kΩ de reposo, capacitores, jumpers, repuestos.

Detalle de cada decisión y su justificación: `proyecto_microprocesador_8bits.md` secciones 12–15 y 21.
