# Simulación en Proteus vs. montaje físico

> Actualizado al diseño vigente (2026-09-17): salida en **8 LEDs** (registro de salida 74LS273 → buffer 74LS244 → LEDs), **8 integrados TTL**, entrega **en protoboards**. Ver `contexto_proyecto.md` A.2 y `proyecto_microprocesador_8bits.md` §13.4/§21 para el detalle de cada decisión.

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

⚠️ **Lo que Proteus SÍ modela, y por eso no se puede saltar ni en simulación:** el buffer 74LS244. Una salida LS-TTL del 273 entrega ~0.4 mA en alto — insuficiente para un LED — y Proteus refleja esa corriente real (ya pasó con los segmentos del diseño anterior). Sin el buffer, el LED no enciende en la simulación tampoco.

---

## 2. Qué es idéntico entre simulación y físico

- **Los 8 integrados TTL** (tabla completa en la sección 4) y su cableado punto a punto.
- **El firmware** — el mismo `.hex` compilado de `firmware/microprocesador/` se carga en el Arduino de Proteus y en el Arduino real, sin cambios.
- **El protocolo serial** (`LOAD`, `LOADB`, `RUN`, `STEP`, …) a 115200 baudios.
- **El programa de referencia** (4×3=12) y el resultado esperado: los ocho LEDs deben mostrar `0 0 0 0 1 1 0 0` (encendidos solo los bits 3 y 2).

---

## 3. Diferencias, elemento por elemento

| Elemento | En Proteus | En físico (obligatorio) |
|---|---|---|
| Alimentación de cada chip | Implícita (pines ocultos) | Cable a VCC y a GND en cada uno de los 8 chips. 74LS244: VCC pin 20, GND pin 10 |
| Habilitaciones del 74LS244 | Conviene atarlas igual | 1G (pin 1) y 2G (pin 19) **a GND**. Sueltas se leen como alto y los LEDs quedan apagados |
| LEDs de salida | Parte `LED-RED` (o cualquier color) | **Rojos, verdes o amarillos**. En alto el 244 da 2.4–3.4 V; a un LED azul o blanco (~3 V) no le queda corriente |
| Capacitores de desacople (0.1 µF) | Opcionales (no rompen nada si faltan) | Obligatorios: 1 por cada uno de los 8 chips TTL, lo más cerca posible del pin VCC |
| Capacitor electrolítico de entrada | No aplica | 1× 10–100 µF en la entrada de alimentación general |
| Fuente de alimentación | Terminales ideales `POWER`/`GROUND` | Fuente 5V regulada, **mínimo 1 A** — el pin 5V del Mega da ~500 mA. GND común con el Arduino es obligatorio |
| Banco de montaje | No aplica | 4 protoboards de 830 puntos sobre base rígida. **Son el entregable** (el ingeniero lo aceptó el 2026-09-17) |
| Verificación | Sondas virtuales, instantáneas | Multímetro, indispensable para continuidad y niveles lógicos; pinzas de punta fina; extractor de CI (opcional) |
| Depuración manual de la ALU | No hace falta: se corre y se lee el resultado | Dip switch de 8 + LEDs de depuración, para caracterizar el 74LS181 aislado antes de integrar (recomendado, se saltó una vez y costó una sesión de debug en vivo) |
| Reset / clock manual | `RESET` por comando serial | Pulsador (push button) físico, para pruebas de banco |
| Repuestos | No aplica | 1–2 unidades de cada integrado — los TTL se dañan con polaridad invertida o estática, y descubrirlo sin repuesto días antes de la entrega es el escenario más común |

---

## 4. Lista de materiales completa para el montaje físico

### Integrados (8 TTL + Arduino)

| Cant. | Componente | Función |
|---|---|---|
| 2 | SN74LS181 | ALU en cascada 4+4 bits |
| 2 | 74LS273 | Registros A y B |
| 1 | 74LS273 | Registro de salida (engancha el bus F al ejecutar `OUT`) |
| 2 | 74LS157 | Mux de entrada al registro A |
| 1 | 74LS244 | Buffer de corriente de los 8 LEDs de salida. Sustituto válido: 74LS240 con los LEDs cableados al revés (5V → 330 Ω → LED → salida) |
| 1 | Arduino Mega 2560 | Unidad de control, memoria (256 B) y reloj |
| 1–2 | Repuestos de cada tipo | Los TTL se dañan con estática o polaridad invertida |

### Salida

| Cant. | Componente | Notas |
|---|---|---|
| 8 | LEDs de 3 o 5 mm, **rojos, verdes o amarillos** | Uno por bit, bit 7 a la izquierda. No azules ni blancos |
| 8 | Resistencias 220 Ω | Una por LED, entre la salida del 244 y el ánodo. 150 Ω si se ven tenues |

### Alimentación

| Cant. | Componente | Notas |
|---|---|---|
| 1 | Fuente 5V regulada, mínimo 1 A | No alimentar todo desde el Arduino |
| 8 | Capacitores cerámicos 0.1 µF | Desacople, uno por cada integrado TTL |
| 1 | Capacitor electrolítico 10–100 µF | Entrada de alimentación general |

### Banco de pruebas y montaje

| Cant. | Componente | Notas |
|---|---|---|
| 4 | Protoboards de 830 puntos | El entregable. Distribución y cableado en `montaje/` |
| 1 | Base de MDF o acrílico ~35 × 25 cm + 4 separadores M3 de 10 mm | Fija las protoboards y el Mega |
| — | Cable sólido 22 AWG en 10 colores (metros por color en la guía de montaje) | Cableado definitivo, un color por función |
| 20+ | LEDs (varios colores) | Depuración de buses y registros |
| 30+ | Resistencias 220–330 Ω | Limitar corriente en LEDs de depuración |
| 9 | Resistencias 1 kΩ | Pull-ups del dip switch (8) y del pulsador (1) del banco de pruebas |
| 1 | Dip switch de 8 | Caracterización manual de la ALU |
| 1 | Pulsador (push button) | Reset / clock manual |
| — | Dupont macho-macho | **Solo** cables de prueba de las fases 1–4; el cableado final (incluido el del Mega) es 22 AWG sólido |
| 1 | Multímetro | Indispensable |
| — | Pinzas de punta fina, extractor de CI | El extractor es opcional |

Ya **no** hacen falta (eran del diseño anterior): 74LS151, 74LS138, displays de 7 segmentos, 8 transistores de dígito, 8 resistencias de base, placa perforada, cautín ni estaño.

---

## 5. Cambio pendiente en Proteus

Para que la simulación vuelva a ser idéntica al montaje:

1. Respaldar el proyecto.
2. Borrar el 74LS151, el 74LS138, el buffer de segmentos y los dos `7SEG-MPX4`. El 74LS273 de salida **se queda**, con su CLK (pin 7 del Mega) y su CLEAR.
3. Colocar un 74LS244: Q0..Q7 del 273 de salida → 1A1, 1A2, 1A3, 1A4, 2A1, 2A2, 2A3, 2A4 (pines 2, 4, 6, 8, 11, 13, 15, 17). 1G (pin 1) y 2G (pin 19) a GND.
4. Salidas 1Y1, 1Y2, 1Y3, 1Y4, 2Y1, 2Y2, 2Y3, 2Y4 (pines 18, 16, 14, 12, 9, 7, 5, 3) → resistencia 220 Ω → LED → GND, uno por bit.
5. Los pines 3–6 del Mega quedan sin conectar. El `.hex` no cambia.
6. `RUN` del programa de referencia → deben quedar encendidos solo los LEDs de los bits 3 y 2.

---

## 6. Orden de compra sugerido

1. **Para caracterizar la ALU ya** (no depende de nada más): dip switch, LEDs, resistencias, protoboard, fuente. Los 74LS181 ya están comprados.
2. **Para el montaje completo:** Arduino Mega, 74LS273 (×3), 74LS157 (×2), 74LS244, 8 LEDs de salida + 8 resistencias de 220 Ω, capacitores, jumpers, repuestos.

Detalle de cada decisión y su justificación: `proyecto_microprocesador_8bits.md` secciones 12–15 y 21.
