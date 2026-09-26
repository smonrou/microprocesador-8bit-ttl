# Proyecto Microprocesador de 8 bits — Bitácora de diseño

**Curso:** Arquitectura de Computadoras y Ensambladores 1
**Documento vivo:** registro de todas las decisiones tomadas y su justificación.

---

## 1. Contexto y entregables

| Aspecto | Definición |
|---|---|
| Modalidad | Individual, circuito **físico** |
| Plazo | 13/14 semanas |
| Entregables | Circuito funcionando, documentación, código del ensamblador, defensa oral |
| Documentación | Sin formato obligatorio |
| Integrados | Sin lista restringida |
| Defensa | El ingeniero elige los datos a ejecutar en vivo |
| Incentivo | Un proyecto destacado puede exonerar del examen final |

---

## 2. Arquitectura

**Von Neumann** — instrucciones y datos comparten el mismo espacio de direcciones.

| Componente | Implementación |
|---|---|
| Registro A | **Físico** — 74LS273 (1 chip de 8 bits) ✅ decidido |
| Registro B | **Físico** — 74LS273 (1 chip de 8 bits) ✅ decidido |
| ALU | **Físico** — 2× SN74LS181 ✅ comprados y aprobados |
| Multiplexor de entrada a A | **Físico** — 2× 74LS157 (decisión de camino de datos) |
| Contador de programa (PC) | **Físico** — 2× 74LS161 en cascada (§22) |
| IR, MAR | Variables en el Arduino |
| Memoria (matriz) | Arduino — celdas de 1 byte, 256 direcciones |
| Banderas (Z, C) | Calculadas/leídas por el Arduino, mostradas en consola (sin LEDs) |
| Entrada de datos | **Monitor serial** ✅ confirmado |
| Salida del procesador | **8 LEDs en binario** (es lo que ejecuta la instrucción OUT) — §21 |
| Interfaz de observación | **Processing** vía serial — estado interno, no es la salida oficial |
| Microcontrolador | **Arduino Mega** (pendiente de compra) |

El Arduino es **únicamente** unidad de control, memoria y reloj. No ejecuta operaciones.

**Aritmética:** complemento a 2 — el 74LS181 lo implementa nativamente, un solo cero (bandera Z confiable), sin acarreo de retorno.

---

## 3. Decisiones de camino de datos

### 3.1 Retorno del resultado de la ALU al registro A

**Opción elegida: multiplexor 74LS157 en la entrada de A.**

Las salidas F del 181 regresan a las entradas de A a través de un mux que selecciona entre "bus del Arduino" o "salida de la ALU", con una sola línea de selección.

| Alternativa | Por qué se descartó |
|---|---|
| El Arduino lee F y lo reescribe en A | El dato pasaría por el Arduino. Riesgo de evaluación: el ingeniero fue explícito en que el Arduino no debe realizar operaciones. |
| Bus compartido con buffers tri-state (74LS244) | Más integrados y señales de habilitación. En protoboard un bus mal habilitado produce cortocircuitos lógicos difíciles de depurar. Solo se justifica con más registros. |

**Ventaja para la defensa:** el resultado nunca toca el Arduino. Se puede señalar el cable físico y decir "por aquí viaja el resultado, el Arduino solo da la orden".

### 3.2 Presupuesto de pines

| Función | Pines |
|---|---|
| Bus de datos hacia A y B | 8 |
| Lectura de F (resultado) | 8 |
| Clock/Load de A y B | 2 |
| Selección del mux | 1 |
| S0–S3, M, C̄n del 181 | 6 |
| **Total** | **25** |

**Decisión: Arduino Mega** (54 I/O), cableado uno a uno. Se descartó Uno + 74HC595/74HC165 porque cada escritura requeriría desplazamiento serie — más código, más lento, y un punto de falla justo en las señales de control.

### 3.3 Granularidad de microciclos

**Decisión: microciclos variables** — cada instrucción consume solo los pasos que necesita. Como la unidad de control es software, esto es un `switch` con distinto número de pasos por caso. Coherente con el formato de instrucción de longitud variable (argumento CISC).

Se descartó el número fijo de microciclos (estilo SAP-1) porque solo tiene sentido con unidad de control en hardware (contador de anillo).

### 3.4 Reloj

- **RUN** — corre libre hasta HLT, con `delay()` ajustable
- **STEP** — avanza **un microciclo** por comando serial (no una instrucción completa), mostrando el estado

Avanzar por microciclo, no por instrucción, es lo que hace valiosa la ejecución paso a paso y es la mejor herramienta de depuración.

---

## 4. Formato de instrucción — longitud variable

```
Byte 1:  [ OP OP OP OP ][ R R M M ]     ← opcode + nibble bajo
Byte 2:  [ D D D D D D D D ]            ← solo si la instrucción lo requiere
```

- **1 byte:** operaciones de ALU, OUT, HLT, NOP (operandos implícitos)
- **2 bytes:** LDA, LDB, LDI, STA, JMP, JZ, JNZ (requieren dirección o dato)
- **El opcode mide siempre 4 bits.** Lo variable es la longitud total de la instrucción (1 o 2 bytes), no el tamaño del campo de opcode — son conceptos distintos y conviene no confundirlos en la defensa.
- 16 opcodes disponibles, 256 direcciones de memoria (`0x00`–`0xFF`), que es el máximo direccionable con un operando de 1 byte
- **No aumenta el cableado:** el formato vive enteramente en el Arduino

Longitud variable es característica **CISC**, contrastable con RISC (longitud fija) en la defensa.

---

## 5. Tabla de opcodes

| Opcode | Nemónico | Bytes | Modo | Operación | Descripción extendida |
|---|---|---|---|---|---|
| `0000` | `NOP` | 1 | — | — | No hace nada durante un ciclo. Sirve para rellenar espacio, alinear código o depurar. Ocupa el valor `0000`, que es el estado natural de la memoria vacía. |
| `0001` | `LDA dir` | 2 | Directo | Mem[dir] → A | Va a la celda de memoria indicada, lee el valor que hay ahí, y lo copia al registro A. El segundo byte es una **dirección**, no un dato. |
| `0010` | `LDB dir` | 2 | Directo | Mem[dir] → B | Igual que LDA, pero el valor leído se copia al registro B. Necesario para tener dos operandos listos antes de una operación. |
| `0011` | `LDI A,#n` | 2 | Inmediato | n → A | Mete un número escrito literalmente en el programa al registro A. El segundo byte **es el dato mismo**, no una dirección. Es la forma de introducir constantes. |
| `0100` | `LDI B,#n` | 2 | Inmediato | n → B | Igual que el anterior, pero hacia el registro B. |
| `0101` | `STA dir` | 2 | Directo | A → Mem[dir] | Toma el contenido actual de A y lo guarda en la celda de memoria indicada. Permite conservar resultados y encadenar operaciones. |
| `0110` | `ADD` | 1 | Implícito | A + B → A | Suma los dos registros y deja el resultado en A. Los operandos están sobreentendidos: siempre A y B. Actualiza las banderas Z y C. |
| `0111` | `SUB` | 1 | Implícito | A − B → A | Resta B de A usando complemento a 2 y guarda el resultado en A. Actualiza banderas. |
| `1000` | `AND` | 1 | Implícito | A & B → A | Compara bit por bit: el resultado tiene 1 solo donde ambos tenían 1. Se usa para **enmascarar** (apagar bits selectivamente). |
| `1001` | `OR` | 1 | Implícito | A \| B → A | Compara bit por bit: el resultado tiene 1 donde cualquiera de los dos tenía 1. Se usa para **encender** bits específicos. |
| `1010` | `XOR` | 1 | Implícito | A ⊕ B → A | Da 1 solo donde los bits difieren. Detecta diferencias entre operandos. Con `B=0xFF` produce el **complemento a 1** de A, supliendo la ausencia de una instrucción NOT. |
| `1011` | `OUT` | 1 | Implícito | Muestra A | Envía el contenido de A a los 8 LEDs de salida (y a la consola serial). Es la única forma de ver un resultado. |
| `1100` | `HLT` | 1 | — | Detiene | Le indica a la unidad de control que termine el ciclo de ejecución. Sin esto el PC seguiría avanzando por memoria vacía interpretando ceros como instrucciones. |
| `1101` | `JMP dir` | 2 | Directo | dir → PC | Cambia el contador de programa a la dirección indicada: la ejecución continúa desde ahí en vez de la siguiente instrucción. Salto **incondicional**. |
| `1110` | `JZ dir` | 2 | Directo | Si Z=1: dir → PC | Salta solo si la última operación dio cero. Si no, continúa normal. Permite tomar **decisiones** según el resultado de un cálculo. |
| `1111` | `JNZ dir` | 2 | Directo | Si Z=0: dir → PC | Salta solo si la última operación **no** dio cero. Es la base de los **bucles**: repetir hasta que un contador llegue a cero. |

**Las 6 funciones aprobadas:** ADD, SUB, AND, OR, XOR, OUT.

Las demás son instrucciones de **transferencia de datos** (LDA, LDB, LDI, STA) y **control de flujo** (JMP, JZ, JNZ, HLT, NOP) — infraestructura, no funciones de cómputo.

**Modos de direccionamiento representados:** directo, inmediato, implícito.

---

## 6. Caracterización de la ALU — SN74LS181

**Fuente:** datasheet Texas Instruments SDLS136 (dic. 1972, rev. marzo 1988), **página 4, TABLE 2 (ACTIVE-HIGH DATA)**, usada con la Figura 2.

Se eligió la convención **active-high**: un `1` lógico son 5V en las entradas A y B. La Tabla 1 (active-low, pág. 3) NO aplica a este diseño.

### 6.1 Tabla de control verificada

| Operación | M | S3 | S2 | S1 | S0 | C̄n (pin 7) | Función en Table 2 |
|---|---|---|---|---|---|---|---|
| **ADD** | 0 | 1 | 0 | 0 | 1 | **1** | F = A PLUS B |
| **SUB** | 0 | 0 | 1 | 1 | 0 | **0** | F = A MINUS B |
| **AND** | 1 | 1 | 0 | 1 | 1 | — | F = AB |
| **OR** | 1 | 1 | 1 | 1 | 0 | — | F = A + B |
| **XOR** | 1 | 0 | 1 | 1 | 0 | — | F = A ⊕ B |

⚠️ **SUB y XOR comparten S=0110.** Lo único que los diferencia es el pin M. Un error ahí daría un XOR donde se espera una resta.

### 6.2 Funciones extra disponibles sin costo

| Función | M | S3–S0 | Uso potencial |
|---|---|---|---|
| F = Ā (NOT A) | 1 | 0000 | Complemento a 1 sin necesitar B=0xFF |
| F = A (pasar A) | 1 | 1111 | Mover A a través de la ALU sin alterarlo |
| F = B (pasar B) | 1 | 1010 | Copiar B → A por el camino del mux |

### 6.3 Detalles críticos confirmados en el datasheet

**1. C̄n está invertido en modo active-high.** El pin 7 se llama C̄n en la Tabla 2:
- ADD sin acarreo de entrada → pin 7 en **ALTO**
- SUB → pin 7 en **BAJO** (ese nivel bajo es el *forced carry* que aporta el +1)

**2. La resta es literalmente complemento a 2.** El datasheet (pág. 2) explica que el chip genera internamente el complemento a 1 del sustraendo, produciendo A−B−1, y que se requiere un acarreo forzado (*end-around or forced carry*) para obtener A−B. Es decir: `A + (NOT B) + 1`. **Material directo para la defensa.**

**3. C̄n+4 también está invertido.** El pin 16 es C̄n+4 en active-high: cuando hay acarreo de salida, ese pin se pone en **BAJO**. El Arduino debe invertirlo al leerlo.

**4. El pin A=B (14) NO es una bandera de cero.** Solo indica igualdad entre A y B, únicamente en modo resta con C̄n = H, y es de **colector abierto** (necesita pull-up de ~1 kΩ a 5V).

→ **Decisión:** no usar el pin A=B para la bandera Z. Como el Arduino lee el bus F completo, calcular `Z = (resultado == 0)` en software. Es más confiable y funciona para todas las operaciones, no solo la resta.

### 6.4 Cascada de los dos integrados (8 bits)

- **C̄n+4 del chip bajo (bits 0–3) → C̄n del chip alto (bits 4–7)**. Ambos invertidos en active-high, así que la conexión es **directa, sin inversores**.
- **M y S3–S0 van en paralelo a ambos chips.**
- Solo el C̄n del chip bajo recibe la señal del Arduino.
- No se usa el 74LS182 (look-ahead). Con 8 bits el ripple carry basta: el datasheet indica ~40 ns de tiempo de suma para 5–8 bits.

### 6.5 Pinout — encapsulado N (PDIP, 24 pines)

| Pin | Señal | Pin | Señal |
|---|---|---|---|
| 1 | B0 | 13 | F3 |
| 2 | A0 | 14 | A=B |
| 3 | S3 | 15 | X (no usar) |
| 4 | S2 | 16 | **C̄n+4** |
| 5 | S1 | 17 | Y (no usar) |
| 6 | S0 | 18 | B3 |
| 7 | **C̄n** | 19 | A3 |
| 8 | M | 20 | B2 |
| 9 | F0 | 21 | A2 |
| 10 | F1 | 22 | **B1** |
| 11 | F2 | 23 | **A1** |
| 12 | GND | 24 | VCC (5V) |

> ⚠️ **Corregido 2026-09-17:** esta tabla tenía los pines 22 y 23 cruzados (decía 22 = A1, 23 = B1). El datasheet de TI (SDLS136, vista superior del encapsulado N) dice **23 = A1 y 22 = B1**. El cableado de Proteus ya usaba lo correcto, por eso la simulación funcionó. El montaje físico (`montaje/pinouts.py`) sigue el datasheet.

Los pines 15 y 17 (X, Y) son para look-ahead con el 74LS182 — no se usan.

### 6.6 Constantes para el Arduino

```cpp
// ── Modo (pin M) ──
#define ALU_ARITMETICO  LOW
#define ALU_LOGICO      HIGH

// ── Selectores S3 S2 S1 S0 ──
#define ALU_ADD   0b1001
#define ALU_SUB   0b0110
#define ALU_AND   0b1011
#define ALU_OR    0b1110
#define ALU_XOR   0b0110   // mismo S que SUB; los distingue M

// ── Carry de entrada (pin 7, invertido) ──
#define CN_ADD    HIGH     // sin acarreo
#define CN_SUB    LOW      // acarreo forzado → complemento a 2
```

Con ~50 µs de espera tras configurar las entradas se va sobrado: el peor caso del datasheet ronda 38 ns por chip, y con el ripple entre los dos no se pasa de ~80 ns.

---

## 7. Verificación experimental de la ALU (pendiente de ejecutar)

Montar **un solo 74LS181 aislado**, sin registros ni Arduino:

- VCC (24) a 5V, GND (12) a tierra
- A0–A3 y B0–B3 a interruptores DIP o jumpers manuales
- F0–F3 a cuatro LEDs con resistencias de 220–330 Ω
- C̄n+4 (16) a un quinto LED
- M, S3–S0 y C̄n a jumpers manuales

### Casos de prueba

| # | Operación | Entradas | Resultado esperado |
|---|---|---|---|
| 1 | ADD | A=0011 (3), B=0010 (2) | F=0101 (5) |
| 2 | ADD con carry | A=1111 (15), B=0001 (1) | F=0000, C̄n+4 en **bajo** |
| 3 | SUB | A=0101 (5), B=0011 (3) | F=0010 (2) |
| 4 | SUB negativa | A=0011 (3), B=0101 (5) | F=1110 (−2 en compl. 2) |
| 5 | **SUB con A=B** | A=0101, B=0101 | F=0000, C̄n+4 en **bajo** |
| 6 | AND | A=1100, B=1010 | F=1000 |
| 7 | OR | A=1100, B=1010 | F=1110 |
| 8 | XOR | A=1100, B=1010 | F=0110 |

El caso 5 valida de una vez el complemento a 2, el forced carry y la lógica de bandera Z.

**Probar el mismo montaje con 2–3 unidades distintas** para descartar integrados defectuosos antes de armar todo el circuito.

**Documentar con fotos de cada caso.** Es una sección completa de la documentación: "Caracterización experimental de la ALU".

---

## 8. Ciclo fetch–decode–execute

| Fase | Qué ocurre | Dónde |
|---|---|---|
| **FETCH** | MAR ← PC; IR ← Mem[MAR]; PC++ | 100% Arduino (software) |
| **DECODE** | Separar opcode del nibble bajo; determinar 1 o 2 bytes; si son 2, leer operando y avanzar PC | 100% Arduino (software) |
| **EXECUTE** | Mover datos a registros, configurar el 181, esperar propagación, capturar resultado | Arduino + protoboard |

### Instrucción de 1 byte (ADD)

```
T1  FETCH    IR ← Mem[PC];  PC++
T2  DECODE   opcode = IR >> 4  →  ADD, 1 byte, implícito
T3  EXECUTE  Configurar M/S/C̄n del 181 para suma
T4           Esperar propagación (~50 µs de margen)
T5  WRITE    Mux → ALU;  pulso de clock en A;  leer F para banderas Z y C
```

### Instrucción de 2 bytes (LDI A,#n)

```
T1  FETCH    IR ← Mem[PC];  PC++
T2  DECODE   opcode → LDI A, 2 bytes
T3  FETCH2   dato ← Mem[PC];  PC++
T4  EXECUTE  Bus ← dato;  Mux → bus;  pulso de clock en A
```

### Salida esperada en modo STEP

```
─── Ciclo 3 ───
FETCH   PC=0x04  →  IR=0x70 (SUB)
DECODE  Opcode 0111 | 1 byte | modo implícito
EXECUTE A=0x0C - B=0x05
        ALU: M=0 S=0110 C̄n=0
RESULT  A=0x07   Z=0  C=1
PC → 0x05
```

---

## 9. Extras de diseño (para destacar)

**Ejecución paso a paso** — modos RUN y STEP (ver 3.4). Convierte la defensa de "mira, suma" a "mira cómo funciona un procesador por dentro".

**Saltos condicionales** — convierten la máquina en **Turing-completa**: con JNZ se pueden construir bucles, lo que permite multiplicación por sumas repetidas y cualquier algoritmo iterativo.

**Ensamblador de dos pasadas** — necesario para resolver etiquetas (`LOOP:`) a direcciones numéricas. Primera pasada registra posiciones, segunda genera bytes. Es cómo funciona un ensamblador real.

---

## 10. Programa de prueba con bucle (4 × 3)

```asm
      LDI A,#0
      STA 200        ; resultado = 0
      LDI A,#3
      STA 201        ; contador = 3

LOOP: LDA 200
      LDB 204
      ADD
      STA 200        ; resultado += 4

      LDA 201
      LDI B,#1
      SUB
      STA 201        ; contador -= 1
      JNZ LOOP

      LDA 200
      OUT            ; muestra 12
      HLT
```

Usa 11 de las 16 instrucciones, memoria de datos real y un bucle condicional.

---

## 11. Argumentos preparados para la defensa

- **Complemento a 2 vs. a 1** — el doble cero del complemento a 1 rompe la bandera Z y obliga a acarreo de retorno
- **La resta en el 74LS181** — el datasheet (pág. 2) documenta `A + (NOT B) + 1`; se puede citar textualmente
- **Longitud variable** — característica CISC, contrastable con RISC
- **Solo A y B en hardware** — separación entre ruta de datos y unidad de control
- **El mux 74LS157** — el resultado nunca pasa por el Arduino; se puede señalar el cable físico
- **`A XOR 0xFF` = complemento a 1** — cómo suplir la ausencia de NOT, igual que arquitecturas RISC reales
- **Por qué no se usa el pin A=B como bandera Z** — solo funciona en modo resta y es colector abierto
- **Tres modos de direccionamiento** en un set de 16 instrucciones
- **Saltos condicionales → Turing-completitud**

---

## 12. Elección de los registros — decidido: 74LS273

**Respuesta del ingeniero:** la división en 2 integrados de 4 bits **no es requisito**, era un ejemplo. La elección es libre.

**Decisión: 74LS273** (un chip de 8 bits por registro).

| Característica | 74LS173 | 74LS273 ✅ |
|---|---|---|
| Bits por chip | 4 | **8** |
| Chips para 8 bits | 2 | **1** |
| Pines | 16 | 20 |
| Salidas | Tri-state | Totem-pole (siempre activas) |
| Habilitación de carga | 2 pines (G1, G2) | Ninguna |
| Clear | Síncrono | **Asíncrono (pin dedicado)** |
| Comportamiento sin load | Retiene el dato | **Carga en cada flanco** |

### Justificación

1. **Un chip por registro en vez de dos** → la mitad de soldaduras al trasladar a la placa definitiva. Esta razón pesa mucho más ahora que el protoboard no es el entregable final (ver sección 14).
2. La ausencia de habilitación no afecta: el Arduino Mega tiene pines de sobra, así que se da **una línea de clock independiente a A y otra a B**. Se controla cuál se carga por **cuál se pulsa**, no por una señal de enable.
3. El **clear asíncrono** permite inicializar los registros a 00000000 al arrancar.
4. Las salidas tri-state del 173 solo sirven con bus compartido, topología ya descartada (ver 3.1).

⚠️ **Precaución de diseño con el 273:** captura en **cada** flanco de subida, sin excepción. Nunca compartir la línea de reloj entre A y B, o ambos se cargarían con el mismo dato.

---

## 13. Lista de materiales para protoboard

### 13.1 Circuitos integrados

| Cant. | Integrado | Función | Estado |
|---|---|---|---|
| 2 | SN74LS181 | ALU (cascada 4+4 bits) | ✅ Comprados |
| 1 | 74LS273 | Registro A (8 bits) | Pendiente de compra |
| 1 | 74LS273 | Registro B (8 bits) | Pendiente de compra |
| 2 | 74LS157 | Mux de entrada a A (cuádruple) | Pendiente |
| 1 | Arduino Mega | Unidad de control, memoria, reloj | Pendiente |
| 1–2 | — | **Repuestos de cada tipo** | Pendiente |

**Los repuestos no son opcionales.** Los TTL se dañan con inversión de polaridad o estática, y descubrirlo sin repuesto días antes de la entrega es el escenario clásico.

### 13.2 Protoboards

> **Actualizado 2026-09-17:** son **4 protoboards** (MUX · registros A/B · ALU · salida), pegadas en una base con el Mega a la izquierda. Plano exacto, fila por fila, en `montaje/` y en las guías de montaje. Lo que sigue es la versión anterior.

**3 protoboards de 830 puntos**, unidas por sus rieles de alimentación:

- **Protoboard 1:** los dos 74LS181 + cascada de carry
- **Protoboard 2:** registros A y B + mux
- **Protoboard 3:** salida (registro de salida + 74LS244 + 8 LEDs) y espacio de pruebas

Con menos espacio el cableado se vuelve una maraña imposible de depurar.

### 13.3 Alimentación

- **Fuente de 5V regulada, mínimo 1A.** No alimentar todo desde el Arduino: el pin de 5V del Mega da ~500 mA, y solo los dos 181 consumen hasta 74 mA típicos según el datasheet, más registros, mux y LEDs. Una fuente externa evita reinicios aleatorios.
- **GND común obligatorio** entre la fuente y el Arduino. Sin esto nada funciona y el síntoma es errático.
- **Capacitores de desacople: 0.1 µF cerámico junto al VCC de cada integrado** (8 unidades, una por TTL; ver §21). Los TTL generan picos de corriente al conmutar; sin desacople aparecen fallos intermitentes que parecen errores de lógica.
- 1 capacitor electrolítico de 10–100 µF en la entrada de alimentación general.

### 13.4 Visualización

**Respuesta del ingeniero:** la forma de visualizar es libre.

**Decisión: doble salida con roles separados** (ver sección 16 para el detalle de la interfaz).

→ **Decisión vigente (2026-09-17, §21): 8 LEDs, uno por bit.** Es la salida **del procesador**, lo que ejecuta la instrucción OUT. LED encendido = bit en 1, bit 7 a la izquierda.

Historia de esta sección, para la defensa: primero el Arduino decodificaba hexadecimal por software (rechazado por el ingeniero, §20); luego 8 dígitos de 7 segmentos en binario con 74LS151 + 74LS138 + buffer + 8 transistores (§20); finalmente 8 LEDs (§21), que muestran lo mismo con 3 integrados, 2 displays y 8 transistores menos.

### Camino del dato

    bus F ─→ 74LS273 (registro de salida) ─→ 74LS244 (buffer) ─→ 220 Ω ─→ LED ─→ GND
                    ↑ CLK (pin 7)                 ↑ 1G, 2G (pines 1 y 19) a GND
                    ↑ CLEAR compartido con A y B

Sin decodificación de ningún tipo: en binario **el bit ya es la magnitud**, y cada LED es un bit. El dato nunca pasa por el Arduino.

### Por qué hacen falta los dos integrados

| Chip | Trabajo | Qué pasa sin él |
|---|---|---|
| 74LS273 | **Memoria.** Engancha el bus F al ejecutar `OUT` y lo retiene hasta el siguiente `OUT` | El bus F cambia en cada ADD/SUB y cuando el firmware pone la ALU en `F=A` para leer registros: los LEDs mostrarían resultados intermedios, no la salida |
| 74LS244 | **Corriente.** Entrega hasta 15 mA por salida en alto (IOH máx, datasheet TI SDLS144D) | El 273 solo entrega 0.4 mA en alto (SDLS090): el LED no enciende. Proteus ya lo mostró con los segmentos |

Descartado: colgar los LEDs de Q0..Q7 del registro A. `OUT` dejaría de tener efecto (A cambia durante todo el bucle) y esas líneas alimentan las entradas de la ALU: cargarlas con LEDs puede bajar el nivel alto hasta leerse mal.

### ⚠️ Color de los LEDs: rojo, verde o amarillo

En alto el 244 no llega a 5 V: VOH mín 2.4 V a −3 mA, típico ~3.4 V sin carga. Lo que queda después de la caída del LED es lo que ve la resistencia:

| LED | Caída | Con 220 Ω | Veredicto |
|---|---|---|---|
| Rojo / verde / amarillo | ~2.0 V | ~5–6 mA típico | ✅ Encienden bien |
| Azul / blanco | ~3.0 V | casi nada | ❌ No comprar |

Si se ven tenues, bajar a 150 Ω: aun en el peor caso (VOH 3.4 V) son ~9 mA, dentro de los 15 mA del chip.

### Alternativa equivalente: 74LS240

Mismo pinout, mismo datasheet, pero invierte. Se cablea al revés (5V → 330 Ω → LED → salida Y): el chip **hunde** la corriente (24 mA a 0.5 V), el LED enciende igual con bit = 1, y funciona con LEDs de cualquier color. Si en la tienda hay 240 y no 244, sirve; solo cambia la orientación de los LEDs.

### Consumo

El 244 consume como máximo 46–54 mA más ~50 mA de los 8 LEDs. La fuente de 1 A de 13.3 sobra.

### 13.5 Componentes pasivos y de prueba

| Cant. | Componente | Uso |
|---|---|---|
| 20+ | LEDs (varios colores) | Depuración: ver estado de buses y registros |
| 30+ | Resistencias 220–330 Ω | Limitar corriente en los LEDs de depuración |
| 9 | Resistencias 1 kΩ | Pull-ups del dip switch (8) y del pulsador (1) del banco de pruebas |
| 8 | Interruptores DIP (o dip switch de 8) | Pruebas manuales de la ALU |
| 1 | Pulsador (push button) | Reset manual / clock manual |

### 13.6 Cableado

- **Kit de jumpers rígidos precortados** (tipo U, de colores). Para esta densidad son muy superiores a los flexibles: quedan planos sobre la protoboard y se puede seguir un cable con la vista.
- **Jumpers macho-macho flexibles** para conexiones Arduino ↔ protoboard.
- **Código de colores disciplinado:** rojo = 5V, negro = GND, un color por bus. Con 60+ cables, esto es la diferencia entre depurar en minutos u horas.

### 13.7 Herramientas

- **Multímetro** — indispensable, para verificar continuidad y niveles lógicos
- Pinzas de punta fina para insertar integrados
- Extractor de CI (opcional, evita doblar pines)

### 13.8 Estimación de cableado

| Tramo | Conexiones |
|---|---|
| Bus del Arduino a los registros | 16 |
| Registros a la ALU | 16 |
| ALU al mux | 8 |
| Mux a registro A | 8 |
| Control (M, S0–S3, C̄n, clocks, select) | ~10 |
| Lectura de F por el Arduino | 8 |
| Alimentación por chip | 12 |
| **Total aproximado** | **~78** |

**Armar y probar por etapas:** primero la ALU sola (sección 7), luego registros sin ALU, luego la integración. Armar todo y encender por primera vez al final es la receta para no encontrar nunca el error.

---

## 14. Montaje definitivo — el protoboard NO es elegible para exoneración

> ✅ **Actualización 2026-09-17 (C.1 resuelto):** el ingeniero acepta la entrega **en protoboards**. No hace falta traslado a placa perforada ni PCB, y las semanas 9–11 del cronograma quedan libres. ⚠️ **Falta confirmar** si la entrega en protoboard conserva la elegibilidad para exonerar, que es lo que esta sección daba por perdido. Lo que sigue se conserva como historia.

⚠️ **Restricción crítica del ingeniero:** un proyecto entregado en protoboard **no puede optar a la exoneración del examen final.** El entregable debe ser un circuito soldado.

### Pregunta pendiente

**¿"No protoboard" significa que exige PCB fabricado, o basta con placa perforada soldada?** Son mundos distintos en tiempo y riesgo. Muchos ingenieros con esa regla solo quieren ver un circuito soldado y estable, no fabricación profesional. **Consultar antes de la semana 6.**

### Plan que funciona con cualquiera de las dos respuestas

**Seguir prototipando en protoboard.** No es contradictorio: el protoboard deja de ser el entregable y pasa a ser el **banco de pruebas**. Nadie diseña un PCB sin validar antes. La diferencia es que ahora hay una etapa final obligatoria de traslado.

### Cronograma (13 semanas)

| Semanas | Actividad |
|---|---|
| 1–2 | Verificación experimental de la ALU (sección 7) + compras |
| 3–5 | Montaje por etapas en protoboard, validación completa del hardware |
| 6–8 | Ensamblador y unidad de control funcionando end-to-end |
| **9–11** | **Traslado a placa definitiva** ← bloque no comprimible |
| 12–13 | Interfaz Processing, documentación, ensayo de defensa |

**Si es PCB fabricado:** la semana 9 es la fecha límite para enviar el diseño (2–4 semanas de fabricación y envío a Guatemala). Empezar a aprender KiCad **en paralelo desde ya**, en ratos muertos — no esperar a la semana 9.

**Si acepta placa perforada (veroboard):** es la opción claramente conveniente. Sin software, sin espera de fabricación, modificable si algo falla, y sigue siendo un circuito soldado y presentable. Se sueldan los integrados y se hacen las conexiones con alambre por debajo.

### Nota sobre el 74LS273

La decisión de usar un chip de 8 bits en vez de dos de 4 bits (sección 12) reduce a la mitad las soldaduras del traslado. Con ~78 conexiones estimadas, cada integrado que se elimina cuenta.

---

## 15. Estado de compras

Con el firmware terminado (sección 19) las cantidades ya no son estimaciones: la asignación de pines está cerrada y se sabe exactamente qué hace falta.

### Integrados

| Cant. | Componente | Estado |
|---|---|---|
| 2 | SN74LS181 — ALU en cascada | ✅ Comprados |
| 1 | **Arduino Mega 2560** — unidad de control | ⬜ Pendiente ← **bloquea todo** |
| 2 | 74LS273 — registros A y B | ⬜ Pendiente |
| 1 | 74LS273 — registro de salida (engancha el bus F al ejecutar OUT) | ⬜ Pendiente |
| 2 | 74LS157 — mux de entrada a A | ⬜ Pendiente |
| 1 | 74LS244 — buffer de corriente de los LEDs de salida (§21). Vale también un 74LS240 cableando los LEDs al revés (13.4) | ⬜ Pendiente |
| 1–2 | **Repuestos de cada tipo** | ⬜ Pendiente |

**Los repuestos no son opcionales.** Los TTL se dañan con inversión de polaridad o estática, y descubrirlo sin repuesto días antes de la entrega es el escenario clásico.

### Visualización

| Cant. | Componente | Notas |
|---|---|---|
| 8 | LEDs de 3 o 5 mm **rojos, verdes o amarillos** | ⬜ La salida del procesador (§21). **No azules ni blancos**: el 244 en alto no da voltaje suficiente (13.4) |
| 8 | Resistencias 220 Ω | Una por LED. 150 Ω si se ven tenues |

Ya no hacen falta displays de 7 segmentos, transistores de dígito ni resistencias de base (eran del diseño de §20).

### Alimentación

| Cant. | Componente | Notas |
|---|---|---|
| 1 | Fuente 5V regulada, mínimo 1A | No alimentar todo desde el Arduino |
| 8 | Capacitores 0,1 µF cerámicos | Desacople, uno junto al VCC de cada integrado TTL |
| 1 | Capacitor electrolítico 10–100 µF | Entrada de alimentación general |

### Banco de pruebas y montaje

| Cant. | Componente | Notas |
|---|---|---|
| 4 | Protoboards de 830 puntos | **Son el entregable** (C.1 resuelto, 2026-09-17); distribución en `montaje/` |
| 1 | Base de MDF o acrílico ~35 × 25 cm + 4 separadores M3 de 10 mm | Fija las protoboards y el Mega |
| 20+ | LEDs y 30+ resistencias 220–330 Ω | Depuración de buses y registros |
| 1 | Dip switch de 8 | Caracterización de la ALU (sección 7) |
| 1 | Pulsador | Reset / clock manual |
| — | Dupont macho-macho | **Solo** cables de prueba de las fases 1–4; el cableado final (incluido el del Mega) es 22 AWG sólido |
| 1 | Multímetro | Indispensable |

### Orden de compra sugerido

1. **Para caracterizar la ALU ya** (sección 7, no depende de nada más): dip switch, LEDs, resistencias, protoboard, fuente. Los 181 ya están.
2. **Para el montaje completo:** Arduino Mega, 74LS273 (×3), 74LS157 (×2), 74LS244, 8 LEDs + 8 resistencias de 220 Ω, capacitores, jumpers, repuestos.

Detalle completo en la sección 13.

---

## 16. Interfaz de observación en Processing

### Rol y justificación

⚠️ **Riesgo a evitar:** el ingeniero listó "Salida → Visualizar Resultados" como una función **del microprocesador**. Si la única salida vive en una ventana de la PC, un examinador estricto puede objetar que la salida no es del procesador sino de un programa externo.

**Solución: roles separados.**

| Elemento | Rol |
|---|---|
| **8 LEDs de salida** | La salida del procesador. Es lo que ejecuta la instrucción OUT. Física, demostrable, cumple el requisito literal. |
| **Interfaz en Processing** | Herramienta de observación del estado interno. No es la salida oficial. |

**Argumento para la defensa:** *"los LEDs son la salida del procesador; la interfaz es mi herramienta de depuración, equivalente a un debugger."*

### Qué debe mostrar

Concebida como el panel frontal de un procesador real:

- Registros A y B en **binario, hexadecimal y decimal** simultáneamente
- PC e IR, con la instrucción decodificada en texto
- Banderas Z y C
- Mapa de memoria en cuadrícula, resaltando la celda que apunta el PC
- El programa desensamblado, con la línea actual marcada
- Botones RUN / STEP / RESET y campo para cargar programas

### Tecnología

**Processing** — la librería `processing.serial` lee del Arduino sin complicaciones y es rápido de arrancar.

Alternativas si se prefiere otro stack:

| Opción | Ventaja |
|---|---|
| Python + PySerial + Tkinter/PyQt | Más versátil si ya se domina Python |
| HTML + Web Serial API | Interfaz más moderna con menos esfuerzo; requiere Chrome |

### ⚠️ Advertencia de prioridad

**Processing es lo último que debe construirse.** Es la parte más vistosa y la más tentadora de empezar, pero llegar a la semana 12 con una interfaz preciosa y un circuito a medio soldar es el peor escenario posible. **Semanas 12–13**, cuando el hardware ya funcione.

---

## 17. Pendientes

**Todo el software está terminado.** Lo que queda es hardware, más la documentación que avanza en paralelo.

### 🔴 Pregunta al ingeniero

| # | Pendiente | Impacto |
|---|---|---|
| 1 | **¿La entrega en protoboard conserva la elegibilidad para exoneración?** | Ya aceptó la protoboard como entrega (C.1 resuelto, 2026-09-17), pero antes había dicho que la protoboard no exonera (§14). Si no exonera y se busca la exoneración, vuelve el traslado a placa soldada |

### 🟡 Acciones propias, en orden

| # | Acción | Depende de | Desbloquea |
|---|---|---|---|
| 2 | **Caracterizar la ALU en protoboard** (sección 7) | Nada — se puede hacer **hoy**, los 181 ya están comprados | Resuelve el pendiente C.5 del carry en SUB |
| 3 | Comprar componentes (sección 15) | Nada | Todo lo demás |
| 4 | Pasar la salida de Proteus a LEDs (273 → 244 → LEDs, §21) | Nada | Que la simulación siga siendo idéntica al montaje |
| 5 | Montaje por etapas en protoboard (es el entregable) | Compras | Primera prueba real del firmware |
| 6 | ~~Aprender KiCad~~ | — | Ya no hace falta salvo que el punto 1 lo exija |
| 7 | ~~Traslado a placa definitiva~~ | — | Solo si el punto 1 lo exige |
| 8 | Interfaz Processing (semanas 12–13) | Punto 5 | — |
| 9 | Documentación y ensayo de la defensa | Continuo | — |

⚠️ **El punto 2 es el cuello de botella real.** No debe subirse el firmware a la placa antes de haber caracterizado la ALU: la semántica del carry en `SUB` que el firmware asume está sin verificar.

⚠️ **Processing es lo último.** Llegar a la semana 12 con una interfaz preciosa y un circuito a medio soldar es el peor escenario posible.

### ✅ Resueltos

| Pendiente | Resolución |
|---|---|
| ~~74LS173 vs 74LS273~~ | Libre elección → **74LS273** (sección 12) |
| ~~Forma de visualizar~~ | Libre → **8 LEDs + Processing**, con roles separados (secciones 16 y 21) |
| ~~¿Paso a paso?~~ | No es requisito, pero suma para exoneración → **implementado** |
| ~~B.0: mapa de memoria~~ | Congelado 2026-08-08. Split 192/64, sin zona reservada, constantes vía `.DB` + `LOAD` serial, binario único de 256 bytes. Ver A.6 de `contexto_proyecto.md` |
| ~~B.1: simulador~~ | 2026-08-08, en `sim/`. **54 pruebas.** Referencia de verdad para depurar el hardware |
| ~~B.2: ensamblador~~ | 2026-08-08, en `asm/`. **211 pruebas.** Sección 18 |
| ~~B.3: firmware~~ | 2026-08-08, en `firmware/`. **193 pruebas.** Sección 19. **Sin probar en hardware** |
| ~~Driver del display~~ | Obsoleto: ya no hay display (§21). El driver de los LEDs es el 74LS244 |
| ~~C.1: PCB o placa perforada~~ | 2026-09-17: el ingeniero acepta la entrega en protoboards |
| ~~C.4: ánodo o cátodo común~~ | 2026-09-17: resuelto por eliminación, la salida son LEDs (§21) |

**Total: 458 pruebas en verde.** Cómo ejecutarlo todo: `instrucciones.md`.

---

## 18. Ensamblador de dos pasadas (B.2) — implementado

**Ubicación:** `asm/`. Entrada: texto `.asm`. Salida: imagen de 256 bytes, listado de ensamblado y script de carga serial.

### Sintaxis

```asm
; comentarios con punto y coma
LOOP:  LDA 200          ; etiqueta + instrucción
       LDI A,#12        ; inmediato con #
       LDI B,#0xFF      ; hexadecimal (también $FF y 0b1010)
       JNZ LOOP         ; etiqueta como operando
       HLT

.ORG 204                ; mueve el puntero de ensamblado
CUATRO: .DB 4           ; emite bytes ahí
```

- Nemónicos insensibles a mayúsculas. Etiquetas también (se normalizan a mayúsculas).
- Números en decimal (`12`), hexadecimal (`0xFF` o `$FF`) y binario (`0b1010`).
- **Etiquetas válidas para saltos y para datos**: `CUATRO: .DB 4` + `LDB CUATRO`.
- `#` estricto: obligatorio en modo inmediato, prohibido en directo. Atrapa la confusión clásica.

### Decisión de diseño: una sola fuente de verdad del ISA

`asm/mnemonics.py` **invierte `sim/isa.py::OPCODE_TABLE`** — es el único archivo de `asm/` que importa `sim.isa`, y no contiene ni un literal de opcode. Dos tablas de opcodes que puedan divergir violarían la regla "Parte A es inmutable"; `tests/test_asm_mnemonics.py` lo vigila. **Material de defensa:** el ensamblador y el simulador no pueden desincronizarse por construcción.

### Regla de zona de programa (asimétrica)

| Caso | Trato |
|---|---|
| Instrucción por encima de `0xBF` | **Error duro** |
| `.DB` en cualquier dirección | Legal (advertencia si cae bajo `0xC0`) |
| Puntero pasa de `0xFF` | **Error duro** |
| Dos sentencias escriben la misma dirección | **Error duro** (solape) |

La asimetría se justifica citando A.6: *"la separación es una convención, no una restricción de hardware"*. Las instrucciones sí se restringen porque la convención existe para que el mapa de memoria sea explicable. La detección de solape es el único peligro real que introduce `.ORG` (código que crece hasta pisar su propia constante).

### Errores detectados, todos con número de línea

Las 6 categorías que exige B.2 (nemónico desconocido, etiqueta no definida, etiqueta duplicada, operando fuera de rango, conteo de operandos incorrecto, zona de programa excedida) más 4 propias: forma de operando, literal mal formado, desbordamiento de memoria y solape.

Los errores se **acumulan dentro de cada fase** (parseo → pasada 1 → pasada 2) y se reportan juntos, pero se aborta en el límite de fase: un nemónico desconocido tiene longitud desconocida, así que seguir a la pasada 1 produciría errores de dirección fantasma.

### Uso

```
python -m asm programas/referencia.asm          # → .bin, .lst, .load
python -m asm programas/referencia.asm --run    # ensambla y ejecuta en el simulador
python -m asm prog.asm --listing-only           # listado por pantalla
```

### Programas canónicos

- `programas/referencia.asm` — copia fiel de A.7, con direcciones numéricas como en el documento.
- `programas/referencia_etiquetas.asm` — misma lógica con etiquetas de datos.

Un test verifica que **ambos producen bytes idénticos**: las etiquetas son azúcar sintáctico puro, resuelto en la primera pasada.

### Validación cruzada con B.1

El test de aceptación compara los bytes del ensamblador contra los que se ensamblaron **a mano** en `sim/programs.py`, y ejecuta el resultado en el simulador esperando `OUT=12`. Si algún día discrepan, uno de los dos está mal y el test lo dice antes que el hardware.
---

## 19. Firmware del Arduino (B.3) — implementado

**Ubicación:** `firmware/microprocesador/` (el sketch) y `firmware/pruebas/` (lo que solo sirve para verificar).

### Restricción que dominó el diseño

El Arduino Mega **aún no se ha comprado**, así que el firmware se escribió sin poder probarlo en hardware. Toda la estructura responde a eso: el ciclo fetch–decode–execute vive en `nucleo.cpp`, que **no toca ni un pin**, y toda la E/S pasa por la interfaz `hal.h`. Hay dos implementaciones de esa interfaz:

| Implementación | Dónde | Para qué |
|---|---|---|
| `hal_arduino.cpp` | Sketch | Puertos reales del Mega |
| `firmware/pruebas/hal_falso.cpp` | Pruebas | Emula el 74LS181, los 74LS273 y el 74LS157 |

Se enlazan en tiempo de compilación, sin clases virtuales. El **mismo código de control** corre en la placa y en la PC.

### La emulación que hace valiosas las pruebas

`hal_falso.cpp` decide qué operación hacer **leyendo las líneas M / S3–S0 / C̄n que el núcleo puso**, no el nemónico de la instrucción. Si el núcleo configurara `S=0110` con `M=1` creyendo que resta, saldría un XOR y la prueba fallaría.

Eso caza justo la clase de error que de otro modo solo aparecería con el circuito ya soldado: la confusión SUB/XOR (comparten `S=0110`), el C̄n invertido, un pulso de reloj en el registro equivocado, o leer F después de pulsar en vez de antes.

**Lo que la emulación NO puede cazar**, y por eso la caracterización de la sección 7 sigue siendo obligatoria: errores de cableado, tiempos reales, chips defectuosos, ruido de alimentación, y si la semántica del carry en resta que asume el diseño es la que de verdad tiene el chip.

### Verificación en lockstep contra el simulador

`tests/test_firmware_nucleo.py` ensambla cada programa de `programas/`, lo ejecuta en el núcleo del firmware y **recorre `sim/cpu.py` en paralelo**, comparando A, B, PC, IR, Z y C instrucción por instrucción. Al primer desacuerdo el mensaje dice en cuál y con qué valores.

El 74LS181 emulado se contrastó además contra `sim/alu.py` en un **barrido exhaustivo de los 65536 pares (A, B) por operación**.

### Dos bugs del simulador que esto destapó

La comparación byte a byte del volcado A.9 encontró dos fallos en B.1 que llevaban ahí desde su implementación:

1. **Las banderas no llegaban a la traza salvo en operaciones de ALU.** Todo `JZ`/`JNZ` informaba `Z=0` en el volcado, fuera cual fuera el valor real — justo el dato que explica por qué saltó o no.
2. **`Cn` se reportaba como `None` en las operaciones lógicas.** El acarreo no es significativo con `M=1`, pero el pin igual tiene que estar a algún nivel: una entrada real no puede quedar flotando. Ahora dice `1`, que es lo que un multímetro leería en el pin 7.

Ambos corregidos en `sim/cpu.py`. Es exactamente para lo que sirve tener dos implementaciones independientes de la misma especificación.

### Decisión: A y B se leen a través de la ALU

El Arduino **no puede leer los 74LS273**: sus salidas van al 181, no al Arduino. Pero `STA`, `OUT` y el volcado de estado necesitan el valor de A.

En vez de llevar copias en software, el núcleo usa las funciones del 181 que la sección 6.2 ya había documentado como disponibles sin costo:

| Función | M | S3–S0 |
|---|---|---|
| `F = A` | 1 | `1111` |
| `F = B` | 1 | `1010` |

**Argumento de defensa:** la salida muestra lo que de verdad hay en el registro físico, no una copia que el Arduino guarde aparte. Si una soldadura fría o un pulso perdido corrompen el registro, se ve al instante en lugar de quedar oculto tras una variable.

### El orden de la fase de escritura

```
uint8_t f = hal::leerF();     // ANTES de pulsar
z_ = (f == 0);                 // única operación en software permitida
c_ = hal::huboAcarreo();
hal::seleccionarMux(MUX_ALU);
hal::pulsoClockA();            // ahora A cambia
```

Leer F antes del pulso no es opcional: el 181 es combinacional, así que en cuanto el pulso engancha F en el registro A, F pasa a valer `(A nuevo) OP B`. Un test verifica que ese orden se respeta.

### Asignación de pines — el aviso que más importa

En el Mega, **PORTA asciende** con el número de pin pero **PORTC y PORTL DESCIENDEN**. Cablear F0 al pin 30 daría el bit 7 en vez del bit 0, y el procesador entregaría resultados con los bits invertidos sin ningún síntoma evidente.

| Grupo | Pines | Señales |
|---|---|---|
| PORTA (asc.) | 22–29 | Bus de datos D0–D7 |
| PORTC (**desc.**) | 37→30 | Lectura de F0–F7 |
| PORTL bits 0–5 (**desc.**) | 49→44 | S0, S1, S2, S3, M, C̄n |
| Sueltos | 41, 40, 39, 38, 2 | CLK A, CLK B, MUX, CLEAR, C̄n+4 |
| Salida | 7 (3–6 sin conectar) | CLK del registro de salida. Desde §21 los pines 3–6 (SEL0–SEL2, BLANK) no van a ningún lado: el firmware los sigue manejando, sin efecto |

Tabla completa y comentada en `firmware/microprocesador/pines.h`. Total: 32 pines de 54.

Los seis bits de control de la ALU caben en un puerto, así que **configurarla entera es una sola escritura**: las seis líneas cambian a la vez, sin estados intermedios que el 181 pudiera llegar a ver.

### Pendientes de Parte C, aislados

| Pendiente | Dónde | Cómo se resuelve |
|---|---|---|
| ~~Display ánodo o cátodo común (C.4)~~ | — | Resuelto por eliminación (§21): la salida son LEDs |
| Semántica del carry en SUB (C.5) | `isa.h` | `#define CARRY_SUB_INVERTIDO 0` → cambiar a `1` |

C.5 sigue abierto. C.4 dejó de tocar código al pasar la decodificación a hardware (§20) y desapareció con los LEDs (§21).

### Protocolo serial

`LOAD`, `LOADB`, `RUN`, `STEP`, `RESET`, `BORRAR`, `DUMP`, `STATE`, `VEL`, `HELP`.

Cada `LOAD` responde `OK dir=0xCC val=0x04`. El buffer de recepción del Arduino son 64 bytes y el archivo `.load` que genera el ensamblador tiene ~29 líneas: sin confirmación por línea, pegarlo de golpe podría perder comandos **en silencio**. `LOADB <dir> <hex...>` reduce esas 29 líneas a dos o tres.

Toda la salida sale por duplicado: el bloque legible de A.9 —idéntico byte a byte al del simulador, hay un test que lo comprueba— y una línea `#clave=valor` en **ASCII puro** que es la que parseará Processing. El prefijo `#` deja que la interfaz filtre esas líneas sin confundirlas con el texto bonito.

### 7 segmentos (reemplazado por LEDs, §21)

Ocho dígitos en binario, **sin ninguna tabla en el firmware**: el 74LS151 entrega `Y` (el bit) y `W` (su complemento), y con eso quedan dibujados el "0" y el "1" (detalle en 13.4). El Arduino solo pulsa el reloj del registro de salida y cuenta 0..7 para multiplexar; el refresco vive en `loop()`, independiente del ciclo de instrucción.

Se descartó el 74LS47/48: decodifica BCD y con valores de 10 a 15 muestra patrones sin sentido — irrelevante ya, porque no se muestra hexadecimal.

### Memoria en el Mega

~620 bytes de los 8192 de SRAM (≈8 %), de los cuales 256 son la matriz de memoria. Holgado. La matriz va en SRAM y no en PROGMEM porque tiene que ser escribible: es una máquina von Neumann.

---

## 20. Salida física en binario — la decodificación baja a hardware (2026-09-04)

> ⚠️ **Reemplazado por §21 (2026-09-17).** El criterio de esta sección sigue vigente (la conversión, si existe, ocurre en hardware); lo que cambió es el medio: 8 LEDs en lugar de 8 dígitos de 7 segmentos.

### Qué pasó

Al mostrarle al ingeniero el display doble de 7 segmentos, señaló: *"ahí lo estarías mostrando en hexa, y no veo que tengas hardware en donde estés realizando la conversión"*. Su criterio, ya aplicado a la ALU, se extiende a la visualización: **la salida física puede verse en binario o en hexadecimal, pero si es hexadecimal la conversión tiene que ocurrir en el circuito**, no en el Arduino, porque el Arduino es el controlador y no realiza operaciones. La visualización en el depurador queda libre — eso es una herramienta de depuración, no la salida del procesador.

Esto invalidó la decisión de 13.4 (tabla de 16 patrones en `display.cpp`).

### Qué se evaluó

| Alternativa | Veredicto |
|---|---|
| 8 LEDs sobre el bus F | Viable, cero conversión. Se mantiene como opción de respaldo |
| **8 dígitos de 7 segmentos mostrando "0"/"1"** | **Elegida.** Binario, conversión trivial y física |
| Decodificador hex 4→7 con compuertas / matriz de diodos / ROM | Viable pero caro en tiempo: hay que diseñarlo y depurarlo. Queda como mejora opcional |
| LCD 16×2 I2C | Descartado: el protocolo I2C y el HD44780 obligan a que el Arduino formatee texto — es exactamente la conversión por software que se rechazó |
| Displays cuádruples en decimal | Descartado: exigiría un conversor binario→BCD en hardware, desproporcionado |

### Por qué el binario no necesita decodificador

`"0"` son los segmentos a,b,c,d,e,f y `"1"` son b,c. Los segmentos b y c están en los dos símbolos (nivel fijo); a,d,e,f encienden con el bit en 0 (complemento del bit); g enciende con el bit en 1 (el bit tal cual). El **74LS151** ya publica `Y` y `W` (el bit y su complemento), así que la conversión es cablear esas dos señales. No hay tabla, ni ROM, ni compuertas de decodificación.

### Camino del dato

    bus F ─→ 74LS273 (registro de salida) ─→ 74LS151 (mux 8:1) ─→ buffer ─→ segmentos
                    ↑ CLK (pin 7)                ↑ A,B,C (pines 3,4,5)
                    ↑ CLEAR compartido           74LS138 ─→ 8 transistores ─→ comunes
                      con A y B                     ↑ A,B,C (los mismos) + E3 (pin 6)

El byte **nunca entra al Arduino** para mostrarse: viaja del bus F al registro de salida por cable. El Arduino pulsa el reloj cuando ejecuta `OUT` (la ALU sigue en F=A, que es como la dejó `leerRegistroA()`) y cuenta 0..7 en las tres líneas de selección, que van a la vez al 151 y al 138 — mismo número, imposible que el bit mostrado y el dígito encendido se desincronicen.

### Efecto en el firmware

- `display.cpp` perdió la tabla `PATRONES[16]` y las 7 líneas de segmento. Quedó en contar 0..7 y pulsar un reloj.
- `hal::mostrarByte(valor)` **ignora** `valor` en la placa real (`(void)valor;`): el parámetro sobrevive porque el HAL falso lo registra y las pruebas verifican qué sacó cada `OUT`.
- Desaparecieron `#define DISPLAY_ANODO_COMUN` y `#define DISPLAY_DIGITO_INVERTIDO`: la polaridad la resuelven el buffer (74LS240 vs 74LS244) y el transistor (PNP vs NPN). El pendiente C.4 sigue abierto pero ya no toca código.
- Pines del display: de 9 (3–11) a 5 (3–7). Total del proyecto: 32 de 54.
- Pruebas nuevas en `tests/test_firmware_sketch.py`: `display.cpp` no puede volver a mencionar `PATRONES` ni `PIN_SEGMENTO`, y `mostrarByte()` tiene que descartar el valor.

### Argumento para la defensa

*"El resultado sale del 74LS181, se engancha en un 74LS273 y lo dibuja un 74LS151. El Arduino no toca ese dato: solo dice cuándo capturarlo y qué dígito iluminar."*

Demostración concreta si la piden: parar el Arduino después de un `OUT` y fijar a mano las tres líneas de selección. El byte sigue en el registro de salida y cada dígito muestra su bit correcto conforme se cambian esas líneas — sin el controlador funcionando. (Con el Arduino detenido se pierde el barrido, así que se ve un dígito a la vez, no los ocho.)

---

## 21. Salida en 8 LEDs (2026-09-17)

### Qué pasó

El ingeniero aceptó la entrega en protoboards (C.1). Con eso se revisó la salida de §20 pensando en el montaje real: 2 displays cuádruples, 74LS151, 74LS138, buffer, 8 transistores con sus resistencias de base y multiplexado a ~480 Hz, todo para dibujar "0" o "1" en cada dígito. Muestra la misma información que 8 LEDs.

### Qué se evaluó

| Alternativa | Veredicto |
|---|---|
| **273 + 74LS244 + 8 LEDs** | **Elegida.** Partes comunes en Guatemala, LED encendido = 1 |
| 273 + 74LS240 + 8 LEDs a 5V | Equivalente (mismo pinout, invierte, el chip hunde corriente). Aceptada como sustituto si no hay 244 |
| 74LS534 / 74LS564 solo (registro con salidas invertidas que hunden 24 mA) | Un chip menos, pero muy difícil de conseguir en Guatemala. Descartado |
| 273 solo, LEDs a 5V (hunde 8 mA) | Dentro de especificación pero LED encendido = 0: 12 se vería `11110011`. Descartado para la defensa |
| LEDs directo sobre el bus F | Muestran resultados intermedios, no lo que ejecuta `OUT`. Descartado |
| LEDs sobre Q del registro A | `OUT` dejaría de tener efecto y cargaría las entradas de la ALU. Descartado |

### Verificación contra datasheet (TI)

| Parámetro | 74LS273 (SDLS090) | 74LS244 (SDLS144D) |
|---|---|---|
| IOH máx (entrega en alto) | −0.4 mA | −15 mA |
| IOL máx (hunde en bajo) | 8 mA | 24 mA |
| VOH mín | 2.7 V a −0.4 mA | 2.4 V a −3 mA; 2.0 V a −15 mA |
| Entradas | — | IIL −0.2 mA, IIH 20 µA, histéresis 0.2 V típ |
| Habilitación | — | 1G (pin 1) y 2G (pin 19) activas en bajo: *"When G is low, the device passes data from the A inputs to the Y outputs"* |

El 273 alimenta al 244 sin problema (una carga LS por salida). **1G y 2G van a GND**: sueltas se leen como alto y las salidas quedan en alta impedancia, con los LEDs apagados aunque todo lo demás esté bien.

### Conexión

| Bit | Q del 273 → entrada del 244 | Salida del 244 → 220 Ω → LED → GND |
|---|---|---|
| 0 | 1A1 (pin 2) | 1Y1 (pin 18) |
| 1 | 1A2 (pin 4) | 1Y2 (pin 16) |
| 2 | 1A3 (pin 6) | 1Y3 (pin 14) |
| 3 | 1A4 (pin 8) | 1Y4 (pin 12) |
| 4 | 2A1 (pin 11) | 2Y1 (pin 9) |
| 5 | 2A2 (pin 13) | 2Y2 (pin 7) |
| 6 | 2A3 (pin 15) | 2Y3 (pin 5) |
| 7 | 2A4 (pin 17) | 2Y4 (pin 3) |

VCC pin 20, GND pin 10, 0.1 µF pegado al chip. LEDs rojos, verdes o amarillos (13.4).

### Balance

| | §20 (7 segmentos) | §21 (LEDs) |
|---|---|---|
| Integrados TTL | 10 | **8** (2×181, 3×273, 2×157, 1×244) |
| Visualización | 2 displays cuádruples, 7 resistencias, 8 transistores, 8 resistencias de base | 8 LEDs, 8 resistencias |
| Pines del Arduino para la salida | 5 (3–7) | **1** (7) |
| Multiplexado | Obligatorio, ~480 Hz | Ninguno: los LEDs se quedan fijos |
| Pendiente C.4 | Abierto | Desaparece |

### Efecto en el firmware

**Ninguno por ahora.** `display::enganchar()` sigue pulsando el reloj del registro de salida (pin 7), que es lo único que la salida necesita. `display::refrescar()` sigue contando 0..7 en los pines 3–5 y manejando BLANK en el 6, que ya no van a ningún lado: es inofensivo. Limpiar `display.cpp`, `display.h`, `pines.h`, el sketch `diagnostico_display/` (barre dígitos que ya no existen) y las pruebas de `tests/test_firmware_sketch.py` que exigen mencionar el 74LS138 y la Parte C queda como tarea aparte.

### Argumento para la defensa

*"El resultado sale del 74LS181, se engancha en un 74LS273 cuando se ejecuta `OUT`, y el 74LS244 le da la corriente a los LEDs. Cada LED es un bit: no hay nada que convertir, y el Arduino nunca toca el dato; solo dice cuándo capturarlo."*

Demostración concreta si la piden: detener el Arduino después de un `OUT`. Los LEDs siguen mostrando el valor, porque vive en el registro físico y no en el controlador.

## 22. Contador de programa físico (2026-09-25)

### Qué pasó

El ingeniero rechazó el PC simulado. Hasta aquí era `uint8_t pc_` en `nucleo.h`, con `pc_++` en FETCH/FETCH2 y `pc_ = operando_` en los saltos. Es la misma objeción que en §20: `pc_++` es una suma, y el Arduino no calcula. IR y MAR se quedan como variables (el ingeniero solo pidió el PC).

### Qué se evaluó

Criterio principal: cuánto cambia el montaje ya diseñado.

| Alternativa | Chips | Cambia el montaje existente | Veredicto |
|---|---|---|---|
| **2× 74LS161** (contador síncrono, carga síncrona, clear asíncrono) | 2 | Nada: se agregan en BB1 y toman el bus D que ya existe | **Elegida.** Es el PC de libro (SAP-1, Mano), y ya estaban en existencia |
| 2× 74LS193 (up/down, carga asíncrona) | 2 | Nada | Sirve, pero su CLR es activo en alto (no comparte el CLEAR sin inversor) y la carga no espera al reloj |
| 74LS273 + 2× 74LS283 (+1) + 2× 74LS157 (cargar o incrementar) | 5 | Nada, pero ~60 cables | Muy didáctico, demasiado cableado |
| 74LS273 y el +1 con la ALU 181 | 1–3 | Mucho: multiplexar la entrada A de la ALU y rehacer las fases 2–4 | Descartado |
| Contador ripple 74LS393 (sin carga paralela) | 1 | Nada | Descartado: un salto sería CLEAR + N pulsos, que es el Arduino calculando |
| PC → RAM/EEPROM física con bus de direcciones | 3+ | Saca la RAM del Arduino | Fuera de alcance: la RAM simulada está aprobada |

### Conexión

| Señal | 74LS161 | Va a |
|---|---|---|
| P0–P3 (pines 3–6) | PC BAJO / PC ALTO | Bus D (entradas A del mux, amarillo): la dirección del salto |
| Q0–Q3 (pines 14, 13, 12, 11) | PC BAJO → A8–A11, PC ALTO → A12–A15 | PORTK del Mega, ascendente (gris) |
| CLK (pin 2) | Los dos | Mega pin 42, con 1 kΩ a GND |
| /LOAD (pin 9) | Los dos | Mega pin 43, con 1 kΩ a +5 V (en reposo cuenta) |
| /CLR (pin 1) | Los dos | CLEAR, Mega pin 38 (el mismo de los 273) |
| ENP (pin 7) | Los dos | +5 V |
| ENT (pin 10) | PC BAJO: +5 V · PC ALTO: RCO (pin 15) de PC BAJO | Cascada: el alto cuenta solo cuando el bajo pasa de 1111 a 0000 |

Pines 42 y 43 son PL7 y PL6. `configurarALU()` escribe PORTL entero pero preserva esos dos bits (`MASCARA_NO_ALU`), así que no pisa el control del PC.

### Efecto en el firmware

- `pc_` desaparece. `Nucleo::pc()` devuelve `hal::leerPC()` (PINK): no hay copia en software, igual que con A y B (§19).
- FETCH/FETCH2 llaman `hal::incrementarPC()` (un flanco con /LOAD en alto). JMP/JZ/JNZ llaman `hal::cargarPC(operando_)`: pone la dirección en el bus D, baja /LOAD, pulsa el reloj y sube /LOAD.
- RESET: `hal::limpiarRegistros()` ya pulsaba CLEAR, y ahora también pone el PC en 0x00. Un `static_assert` exige `DIRECCION_INICIO == 0x00`, que es lo que deja el CLEAR.
- `hal_falso.cpp` emula el 161, incluida la vuelta 0xFF → 0x00, y cuenta los flancos. Las pruebas comprueban que cada byte leído produce exactamente una cuenta y cada salto tomado exactamente una carga. El lockstep contra `sim/cpu.py` sigue comparando el PC después de cada instrucción.

### Argumento para la defensa

*"El PC son dos 74LS161. El Arduino no suma nada: pulsa el reloj y el contador avanza, o baja /LOAD y el contador carga la dirección del salto desde el bus. La RAM está simulada en el Arduino, así que el Arduino lee el PC por A8–A15: esas son las patas de dirección de su RAM."*

Demostración si la piden: `STEP` por el monitor serial con el multímetro en las Q de los 161. El `PC=` del monitor es lo que marcan los chips, porque el firmware no guarda otro.

