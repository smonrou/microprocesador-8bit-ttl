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
| PC, IR, MAR | Variables en el Arduino |
| Memoria (matriz) | Arduino — celdas de 1 byte, 256 direcciones |
| Banderas (Z, C) | Calculadas/leídas por el Arduino, mostradas en consola (sin LEDs) |
| Entrada de datos | **Monitor serial** ✅ confirmado |
| Salida del procesador | **7 segmentos** (es lo que ejecuta la instrucción OUT) |
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
| `1011` | `OUT` | 1 | Implícito | Muestra A | Envía el contenido de A al display de 7 segmentos o a la consola serial. Es la única forma de ver un resultado. |
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
| 10 | F1 | 22 | A1 |
| 11 | F2 | 23 | B1 |
| 12 | GND | 24 | VCC (5V) |

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

**3 protoboards de 830 puntos**, unidas por sus rieles de alimentación:

- **Protoboard 1:** los dos 74LS181 + cascada de carry
- **Protoboard 2:** registros A y B + mux
- **Protoboard 3:** salida (7 segmentos) y espacio de pruebas

Con menos espacio el cableado se vuelve una maraña imposible de depurar.

### 13.3 Alimentación

- **Fuente de 5V regulada, mínimo 1A.** No alimentar todo desde el Arduino: el pin de 5V del Mega da ~500 mA, y solo los dos 181 consumen hasta 74 mA típicos según el datasheet, más registros, mux y LEDs. Una fuente externa evita reinicios aleatorios.
- **GND común obligatorio** entre la fuente y el Arduino. Sin esto nada funciona y el síntoma es errático.
- **Capacitores de desacople: 0.1 µF cerámico junto al VCC de cada integrado** (~6 unidades). Los TTL generan picos de corriente al conmutar; sin desacople aparecen fallos intermitentes que parecen errores de lógica.
- 1 capacitor electrolítico de 10–100 µF en la entrada de alimentación general.

### 13.4 Visualización

**Respuesta del ingeniero:** la forma de visualizar es libre.

**Decisión: doble salida con roles separados** (ver sección 17 para el detalle de la interfaz).

- **2 displays de 7 segmentos** (definir ánodo o cátodo común) — es la salida **del procesador**, lo que ejecuta la instrucción OUT
- **7 resistencias de 220–330 Ω**, una por línea de segmento

⚠️ **El 74LS47/48 decodifica BCD, no hexadecimal.** Solo muestra correctamente 0–9; con valores 10–15 muestra patrones sin sentido.

→ **Decisión: el Arduino decodifica los segmentos directamente.** Da hexadecimal completo (0–F), ahorra dos integrados, y es coherente con que el Arduino ya lee el bus F.

### Multiplexado: 9 pines en vez de 14

Los dos dígitos comparten las 7 líneas de segmento y se alternan rápido; la persistencia de la visión hace que se vean ambos encendidos. Son **7 líneas de segmento + 2 de selección = 9 pines**, contra los 14 de dos displays independientes.

Por eso las resistencias son **7 y no 14**: van en las líneas de segmento, que son compartidas.

Mismo criterio que llevó a elegir el 74LS273 sobre el 74LS173 (sección 12): menos pines, menos soldaduras al pasar a la placa definitiva.

### ⚠️ Los comunes NO se conectan directo al Arduino

Al multiplexar, el pin común de un dígito conduce **la corriente de los 7 segmentos a la vez** (el caso del "8").

| Resistencia por segmento | Por segmento | 7 segmentos encendidos |
|---|---|---|
| 220 Ω | ~13,6 mA | **~95 mA** |
| 330 Ω | ~9 mA | **~63 mA** |

El máximo **absoluto** de un pin del Arduino son **40 mA** (20 mA es el valor recomendado). Conectar el común directo al pin lo quema — o peor, lo degrada de forma intermitente, y entonces el síntoma parece un fallo de lógica y se persigue durante horas en el sitio equivocado.

→ **Decisión: un transistor por dígito.** El transistor conmuta la corriente desde la alimentación y el pin del Arduino solo maneja la base (~5 mA, holgadamente dentro de rango).

| Si el display es | Transistor | Resistencia de base |
|---|---|---|
| Ánodo común | 2N3906 (PNP) | 1 kΩ |
| Cátodo común | 2N2222 (NPN) | 1 kΩ |

**Consecuencia en el firmware:** el transistor **invierte** la señal de selección del dígito. Está contemplado en `firmware/microprocesador/display.h` tras `#define DISPLAY_DIGITO_INVERTIDO`. Sin esa inversión el display quedaría siempre apagado o siempre encendido.

### 13.5 Componentes pasivos y de prueba

| Cant. | Componente | Uso |
|---|---|---|
| 20+ | LEDs (varios colores) | Depuración: ver estado de buses y registros |
| 30+ | Resistencias 220–330 Ω | Limitar corriente en LEDs y en las 7 líneas de segmento |
| 5 | Resistencias 1 kΩ | Pull-ups |
| **2** | **Resistencias 1 kΩ** | **Base de los transistores del display** (ver 13.4) |
| **2** | **Transistores 2N3906 (PNP) o 2N2222 (NPN)** | **Driver de dígito del display** — según ánodo o cátodo común |
| 8 | Interruptores DIP (o dip switch de 8) | Pruebas manuales de la ALU |
| 1 | Pulsador (push button) | Reset manual / clock manual |

⚠️ **Los transistores no son opcionales.** Sin ellos, el pin que selecciona un dígito conduciría ~95 mA contra un máximo absoluto de 40 mA. Ver el cálculo en 13.4.

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
| 2 | 74LS157 — mux de entrada a A | ⬜ Pendiente |
| 1–2 | **Repuestos de cada tipo** | ⬜ Pendiente |

**Los repuestos no son opcionales.** Los TTL se dañan con inversión de polaridad o estática, y descubrirlo sin repuesto días antes de la entrega es el escenario clásico.

### Visualización

| Cant. | Componente | Notas |
|---|---|---|
| 2 | Displays de 7 segmentos | ⬜ **Definir ánodo o cátodo común al comprar** (pendiente C.4) |
| 7 | Resistencias 220–330 Ω | Una por línea de segmento. Son 7, no 14: las líneas se comparten |
| 2 | Transistores 2N3906 (PNP) **o** 2N2222 (NPN) | Según el tipo de display. **Obligatorios** — ver 13.4 |
| 2 | Resistencias 1 kΩ | Base de los transistores |

El tipo de transistor depende del display: **PNP si es ánodo común, NPN si es cátodo común**. Conviene decidir el display primero y comprar ambos en el mismo viaje.

### Alimentación

| Cant. | Componente | Notas |
|---|---|---|
| 1 | Fuente 5V regulada, mínimo 1A | No alimentar todo desde el Arduino |
| ~8 | Capacitores 0,1 µF cerámicos | Desacople, uno junto al VCC de cada integrado |
| 1 | Capacitor electrolítico 10–100 µF | Entrada de alimentación general |

### Banco de pruebas y montaje

| Cant. | Componente | Notas |
|---|---|---|
| 3 | Protoboards de 830 puntos | Banco de pruebas, no el entregable |
| — | Placa perforada o PCB | ⬜ **Bloqueado** por la respuesta del ingeniero (pendiente C.1) |
| 20+ | LEDs y 30+ resistencias 220–330 Ω | Depuración de buses y registros |
| 1 | Dip switch de 8 | Caracterización de la ALU (sección 7) |
| 1 | Pulsador | Reset / clock manual |
| — | Kit de jumpers rígidos precortados | Muy superiores a los flexibles con esta densidad |
| — | Jumpers macho-macho flexibles | Arduino ↔ protoboard |
| 1 | Multímetro | Indispensable |
| — | Cautín, estaño, extractor de estaño | Para el traslado a placa definitiva |

### Orden de compra sugerido

1. **Para caracterizar la ALU ya** (sección 7, no depende de nada más): dip switch, LEDs, resistencias, protoboard, fuente. Los 181 ya están.
2. **Para el montaje completo:** Arduino Mega, 74LS273, 74LS157, capacitores, jumpers, repuestos.
3. **Cuando se sepa el tipo de display:** displays + transistores a juego.
4. **Cuando el ingeniero responda sobre PCB:** placa perforada o envío del diseño.

Detalle completo en la sección 13.

---

## 16. Interfaz de observación en Processing

### Rol y justificación

⚠️ **Riesgo a evitar:** el ingeniero listó "Salida → Visualizar Resultados" como una función **del microprocesador**. Si la única salida vive en una ventana de la PC, un examinador estricto puede objetar que la salida no es del procesador sino de un programa externo.

**Solución: roles separados.**

| Elemento | Rol |
|---|---|
| **Display de 7 segmentos** | La salida del procesador. Es lo que ejecuta la instrucción OUT. Física, demostrable, cumple el requisito literal. |
| **Interfaz en Processing** | Herramienta de observación del estado interno. No es la salida oficial. |

**Argumento para la defensa:** *"el display es la salida del procesador; la interfaz es mi herramienta de depuración, equivalente a un debugger."*

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

### 🔴 Bloqueado por respuesta del ingeniero

| # | Pendiente | Impacto |
|---|---|---|
| 1 | **¿PCB fabricado o basta placa perforada soldada?** | Define las semanas 9–11 enteras. **Consultar antes de la semana 6.** Si es PCB, la semana 9 es la fecha límite para enviar el diseño (2–4 semanas de fabricación y envío) y hay que aprender KiCad desde ya |

### 🟡 Acciones propias, en orden

| # | Acción | Depende de | Desbloquea |
|---|---|---|---|
| 2 | **Caracterizar la ALU en protoboard** (sección 7) | Nada — se puede hacer **hoy**, los 181 ya están comprados | Resuelve el pendiente C.5 del carry en SUB |
| 3 | Comprar componentes (sección 15) | Nada | Todo lo demás |
| 4 | Decidir tipo de display al comprarlo | Compra | Resuelve C.4; determina qué transistores comprar |
| 5 | Montaje por etapas en protoboard | Compras | Primera prueba real del firmware |
| 6 | Aprender KiCad en ratos muertos | Nada | Seguro por si la respuesta al punto 1 es PCB |
| 7 | Traslado a placa definitiva (semanas 9–11) | Puntos 1 y 5 | Elegibilidad para exoneración |
| 8 | Interfaz Processing (semanas 12–13) | Punto 7 | — |
| 9 | Documentación y ensayo de la defensa | Continuo | — |

⚠️ **El punto 2 es el cuello de botella real.** No debe subirse el firmware a la placa antes de haber caracterizado la ALU: la semántica del carry en `SUB` que el firmware asume está sin verificar.

⚠️ **Processing es lo último.** Llegar a la semana 12 con una interfaz preciosa y un circuito a medio soldar es el peor escenario posible.

### ✅ Resueltos

| Pendiente | Resolución |
|---|---|
| ~~74LS173 vs 74LS273~~ | Libre elección → **74LS273** (sección 12) |
| ~~Forma de visualizar~~ | Libre → **7 segmentos + Processing**, con roles separados (sección 16) |
| ~~¿Paso a paso?~~ | No es requisito, pero suma para exoneración → **implementado** |
| ~~B.0: mapa de memoria~~ | Congelado 2026-08-08. Split 192/64, sin zona reservada, constantes vía `.DB` + `LOAD` serial, binario único de 256 bytes. Ver A.6 de `contexto_proyecto.md` |
| ~~B.1: simulador~~ | 2026-08-08, en `sim/`. **54 pruebas.** Referencia de verdad para depurar el hardware |
| ~~B.2: ensamblador~~ | 2026-08-08, en `asm/`. **211 pruebas.** Sección 18 |
| ~~B.3: firmware~~ | 2026-08-08, en `firmware/`. **193 pruebas.** Sección 19. **Sin probar en hardware** |
| ~~Driver del display~~ | Hallazgo: los comunes necesitan transistor. Añadido a la lista de compras y contemplado en el firmware. Ver 13.4 |

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

**Argumento de defensa:** el display muestra lo que de verdad hay en el registro físico, no una copia que el Arduino guarde aparte. Si una soldadura fría o un pulso perdido corrompen el registro, se ve al instante en lugar de quedar oculto tras una variable.

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
| Display | 3–9, 10, 11 | Segmentos a–g, dos comunes |

Tabla completa y comentada en `firmware/microprocesador/pines.h`. Total: 36 pines de 54.

Los seis bits de control de la ALU caben en un puerto, así que **configurarla entera es una sola escritura**: las seis líneas cambian a la vez, sin estados intermedios que el 181 pudiera llegar a ver.

### Pendientes de Parte C, aislados

| Pendiente | Dónde | Cómo se resuelve |
|---|---|---|
| Display ánodo o cátodo común (C.4) | `display.h` | `#define DISPLAY_ANODO_COMUN 1` → cambiar a `0` |
| Semántica del carry en SUB (C.5) | `isa.h` | `#define CARRY_SUB_INVERTIDO 0` → cambiar a `1` |

Un cambio de una línea en cada caso. Ninguno de los dos se da por resuelto.

### Protocolo serial

`LOAD`, `LOADB`, `RUN`, `STEP`, `RESET`, `BORRAR`, `DUMP`, `STATE`, `VEL`, `HELP`.

Cada `LOAD` responde `OK dir=0xCC val=0x04`. El buffer de recepción del Arduino son 64 bytes y el archivo `.load` que genera el ensamblador tiene ~29 líneas: sin confirmación por línea, pegarlo de golpe podría perder comandos **en silencio**. `LOADB <dir> <hex...>` reduce esas 29 líneas a dos o tres.

Toda la salida sale por duplicado: el bloque legible de A.9 —idéntico byte a byte al del simulador, hay un test que lo comprueba— y una línea `#clave=valor` en **ASCII puro** que es la que parseará Processing. El prefijo `#` deja que la interfaz filtre esas líneas sin confundirlas con el texto bonito.

### 7 segmentos

Tabla de 16 patrones en software, hexadecimal completo. **No** se usa un 74LS47/48: decodifica BCD y con valores de 10 a 15 muestra patrones sin sentido. Hacerlo por software ahorra dos integrados y es coherente con que el Arduino ya lee el bus F.

Los dos dígitos se multiplexan sobre las mismas 7 líneas de segmento (9 pines en vez de 14, la mitad de soldaduras al pasar a placa definitiva). El refresco vive en `loop()`, independiente del ciclo de instrucción.

### Memoria en el Mega

~620 bytes de los 8192 de SRAM (≈8 %), de los cuales 256 son la matriz de memoria. Holgado. La matriz va en SRAM y no en PROGMEM porque tiene que ser escribible: es una máquina von Neumann.
