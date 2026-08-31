# CONTEXTO DEL PROYECTO — Microprocesador de 8 bits

> **Propósito de este archivo:** documento de traspaso autocontenido. Contiene todas las especificaciones y decisiones necesarias para ejecutar cualquiera de las cinco tareas descritas en la Parte B, en conversaciones independientes y en paralelo.
>
> **Regla fundamental:** este documento es la fuente de verdad. Ninguna tarea puede cambiar una especificación de la Parte A por su cuenta. Si una tarea encuentra una contradicción o un vacío, debe **detenerse y reportarlo**, no improvisar.

---

# PARTE A — ESPECIFICACIÓN CONGELADA

## A.1 Contexto del curso

Proyecto individual del curso **Arquitectura de Computadoras y Ensambladores 1**. Se construye un microprocesador de 8 bits con lógica TTL real. Plazo: 13–14 semanas.

**Entregables:** circuito físico funcionando, documentación, código del ensamblador, defensa oral.

**Restricciones impuestas por el ingeniero:**

1. El Arduino sirve **únicamente** como unidad de control, memoria RAM simulada y reloj sincronizador. **No debe realizar las operaciones aritméticas ni lógicas.** Estas ocurren en hardware TTL.
2. Arquitectura **von Neumann**: instrucciones y datos comparten el mismo espacio de direcciones.
3. La entrada de datos es por **monitor serial**. Se descartaron botones físicos.
4. En la defensa, el ingeniero elige en vivo qué datos ejecutar. El sistema debe ser genérico, no una demo pregrabada.
5. Un proyecto entregado en protoboard **no es elegible para exoneración** del examen final. El entregable debe ser un circuito soldado.

## A.2 Hardware

| Componente | Implementación | Estado |
|---|---|---|
| ALU | 2× **SN74LS181** en cascada (4+4 bits) | Comprados |
| Registro A | 1× **74LS273** (8 bits) | Decidido |
| Registro B | 1× **74LS273** (8 bits) | Decidido |
| Mux de entrada a A | 2× **74LS157** | Decidido |
| Unidad de control / memoria / reloj | **Arduino Mega** | Por comprar |
| Salida del procesador | Display de 7 segmentos, decodificado por el Arduino | Decidido |
| Interfaz de observación | Processing vía serial | Decidido |

**Camino de datos:** las salidas F de la ALU regresan a las entradas del registro A **a través del mux 74LS157**. El resultado nunca pasa por el Arduino. El mux selecciona entre "bus del Arduino" y "salida de la ALU".

**PC, IR y MAR son variables en el Arduino**, no hardware.

**Precaución con el 74LS273:** captura en cada flanco de subida, sin habilitación. A y B deben tener **líneas de reloj independientes**; nunca compartirlas.

## A.3 Tabla de control de la ALU (SN74LS181)

Verificada contra el datasheet TI SDLS136, **página 4, TABLE 2 (ACTIVE-HIGH DATA)**.

| Operación | M | S3 S2 S1 S0 | C̄n (pin 7) | Función en Table 2 |
|---|---|---|---|---|
| ADD | 0 | `1001` | 1 (HIGH) | F = A PLUS B |
| SUB | 0 | `0110` | 0 (LOW) | F = A MINUS B |
| AND | 1 | `1011` | — | F = AB |
| OR | 1 | `1110` | — | F = A + B |
| XOR | 1 | `0110` | — | F = A ⊕ B |

**Detalles críticos:**

- **C̄n (pin 7) está invertido.** ADD sin acarreo → HIGH. SUB → LOW (ese nivel bajo es el *forced carry* que aporta el +1 del complemento a 2).
- **C̄n+4 (pin 16) está invertido.** Con acarreo de salida, el pin va a **BAJO**. El Arduino debe invertirlo al leerlo.
- **SUB y XOR comparten S=0110.** Solo los distingue el pin M. Error frecuente.
- **El pin A=B (14) NO se usa** como bandera Z: solo funciona en modo resta y es colector abierto.
- La resta es complemento a 2 nativo: el chip genera `A + (NOT B) + 1`.
- Cascada: `C̄n+4` del chip bajo → `C̄n` del chip alto, **conexión directa sin inversores**. M y S3–S0 en paralelo a ambos chips.
- Propagación: <100 ns en el peor caso. Un margen de 50 µs es más que suficiente.

## A.4 Formato de instrucción

Longitud variable, 1 o 2 bytes:

```
Byte 1:  [ OP OP OP OP ][ 0 0 0 0 ]   ← opcode en el nibble alto; nibble bajo reservado
Byte 2:  [ D D D D D D D D ]          ← solo en instrucciones de 2 bytes
```

- El **opcode mide siempre 4 bits**, sin excepción, y se extrae como `IR >> 4`.
- El nibble bajo del byte 1 es **siempre `0000`** en esta versión (reservado para expansión).
- El PC avanza 1 o 2 según la instrucción.

### ⚠️ Aclaración: longitud variable ≠ opcode variable

Esta arquitectura usa **instrucciones de longitud variable**, NO opcodes de longitud variable. Son cosas distintas:

| Concepto | En este diseño |
|---|---|
| Tamaño del campo de opcode | **Fijo: 4 bits siempre** |
| Tamaño total de la instrucción | **Variable: 1 o 2 bytes** |

El decodificador siempre lee los mismos 4 bits para identificar la instrucción; lo único que cambia es cuántos bytes ocupa en memoria. Un opcode de longitud variable (como en x86) obligaría a determinar cuántos bits leer antes de saber de qué instrucción se trata, y no se usa aquí.

### Por qué 256 bytes de memoria

El tamaño de la memoria es **consecuencia directa** del formato: el operando de las instrucciones de 2 bytes ocupa un byte completo, por lo que puede expresar direcciones `0x00`–`0xFF`. Ese es el máximo direccionable con este diseño.

**Comparación para la defensa:** si la instrucción cupiera en 1 byte fijo, con 4 bits de opcode quedarían solo 4 bits de operando = **16 direcciones**. La longitud variable lleva ese espacio de 16 a 256.

## A.5 Set de instrucciones (16 opcodes)

| Opcode | Nemónico | Bytes | Modo | Operación | Afecta banderas |
|---|---|---|---|---|---|
| `0000` | `NOP` | 1 | — | Ninguna | No |
| `0001` | `LDA dir` | 2 | Directo | Mem[dir] → A | No |
| `0010` | `LDB dir` | 2 | Directo | Mem[dir] → B | No |
| `0011` | `LDI A,#n` | 2 | Inmediato | n → A | No |
| `0100` | `LDI B,#n` | 2 | Inmediato | n → B | No |
| `0101` | `STA dir` | 2 | Directo | A → Mem[dir] | No |
| `0110` | `ADD` | 1 | Implícito | A + B → A | **Sí** |
| `0111` | `SUB` | 1 | Implícito | A − B → A | **Sí** |
| `1000` | `AND` | 1 | Implícito | A & B → A | **Sí** |
| `1001` | `OR` | 1 | Implícito | A \| B → A | **Sí** |
| `1010` | `XOR` | 1 | Implícito | A ⊕ B → A | **Sí** |
| `1011` | `OUT` | 1 | Implícito | Muestra A | No |
| `1100` | `HLT` | 1 | — | Detiene ejecución | No |
| `1101` | `JMP dir` | 2 | Directo | dir → PC | No |
| `1110` | `JZ dir` | 2 | Directo | Si Z=1: dir → PC | No |
| `1111` | `JNZ dir` | 2 | Directo | Si Z=0: dir → PC | No |

**Las 6 funciones aprobadas por el ingeniero son:** ADD, SUB, AND, OR, XOR, OUT. Las demás son infraestructura (transferencia de datos y control de flujo).

**Regla de banderas — crítica:** solo las cinco operaciones de ALU actualizan Z y C. `STA`, `LDA`, `LDB`, `LDI` **no las modifican**. Esto es indispensable: el programa de referencia hace `SUB` → `STA` → `JNZ`, y el `STA` intermedio no debe destruir la bandera.

**Semántica de banderas:**
- `Z = 1` si el resultado de la última operación de ALU fue `0x00`.
- `C` proviene de C̄n+4 invertido. En operaciones lógicas (M=1) el carry no es significativo; se define como `0`.

## A.6 Mapa de memoria (CONGELADO — decisión B.0, 2026-08-08)

Espacio único de 256 bytes (`0x00`–`0xFF`), von Neumann.

| Rango | Tamaño | Uso |
|---|---|---|
| `0x00`–`0xBF` | 192 bytes | **Programa.** La ejecución siempre arranca en `0x00`. |
| `0xC0`–`0xFF` | 64 bytes | **Datos.** Variables y constantes. |

**Notas:**
- La separación es una **convención**, no una restricción de hardware. Al ser von Neumann, nada impide que una instrucción escriba en la zona de programa; la división existe para que los programas sean legibles y para poder explicar el mapa en la defensa.
- Toda la memoria se inicializa en `0x00` (que decodifica como `NOP`).
- El programa de referencia usa las direcciones 200 (`0xC8`), 201 (`0xC9`) y 204 (`0xCC`), todas dentro de la zona de datos.
- Direcciones válidas: `0x00`–`0xFF`. El ensamblador debe rechazar cualquier operando fuera de rango.
- **Sin zona especial reservada.** No hay vector de arranque (el PC siempre inicia en `0x00` por regla fija de A.7/A.9) ni E/S mapeada a memoria (`OUT` lee el registro A directamente, no una celda de memoria). Reservar espacio sin uso real no aporta nada al diseño.

**Carga de constantes iniciales — decisión B.0:** se soportan **ambos mecanismos, no son excluyentes**:
1. **Directiva `.DB`** en el ensamblador — coloca constantes conocidas en su dirección dentro del mismo binario ensamblado. Es como el programa de referencia fija el valor 4 en `0xCC` de forma reproducible y documentable.
2. **Comando serial `LOAD <dir> <byte>`** (ya definido en el protocolo de B.3) — obligatorio de todos modos, porque A.1 exige que el ingeniero pueda cargar datos en vivo durante la defensa. `.DB` cubre el caso de prueba reproducible; `LOAD` cubre la entrada en vivo.

**Formato de salida del ensamblador — decisión B.0:** **un solo binario de 256 bytes**, no programa y datos por separado. Coherente con von Neumann (A.2): un único espacio de direcciones, una sola carga en el simulador o en la memoria del Arduino.

## A.7 Programa de referencia (multiplicación 4 × 3)

Este programa es el **caso de prueba canónico**. Debe funcionar idénticamente en el simulador, el ensamblador y el hardware.

```asm
      LDI A,#0
      STA 200        ; resultado = 0
      LDI A,#3
      STA 201        ; contador = 3

LOOP: LDA 200
      LDB 204        ; el 4 vive en la dirección 204
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

**Precondición:** la dirección 204 debe contener el valor 4 antes de ejecutar.
**Resultado esperado:** `OUT` muestra `12` (`0x0C`).

## A.8 Ciclo fetch–decode–execute

| Fase | Acción | Dónde |
|---|---|---|
| FETCH | `IR ← Mem[PC]`; `PC++` | Arduino |
| DECODE | `opcode = IR >> 4`; determinar longitud; si son 2 bytes: `operando ← Mem[PC]`, `PC++` | Arduino |
| EXECUTE | Cargar registros, configurar la ALU, esperar propagación, capturar resultado vía mux | Arduino + hardware |

**Microciclos variables:** cada instrucción consume solo los pasos que necesita.

**Ejemplo, instrucción de 1 byte (ADD):**
```
T1  FETCH    IR ← Mem[PC];  PC++
T2  DECODE   opcode 0110 → ADD, 1 byte, implícito
T3  EXECUTE  Configurar M=0, S=1001, C̄n=1
T4           Esperar propagación (50 µs)
T5  WRITE    Mux → ALU;  pulso de clock en A;  leer F y C̄n+4 para banderas
```

**Ejemplo, instrucción de 2 bytes (LDI A,#n):**
```
T1  FETCH    IR ← Mem[PC];  PC++
T2  DECODE   opcode 0011 → LDI A, 2 bytes
T3  FETCH2   dato ← Mem[PC];  PC++
T4  EXECUTE  Bus ← dato;  Mux → bus;  pulso de clock en A
```

## A.9 Modos de ejecución

- **RUN** — ejecuta hasta `HLT`, con retardo ajustable entre instrucciones.
- **STEP** — avanza **un microciclo** por comando (no una instrucción completa), imprimiendo el estado.

Formato de estado en modo STEP:

```
─── Ciclo 3 ───
FETCH   PC=0x04  →  IR=0x70 (SUB)
DECODE  Opcode 0111 | 1 byte | modo implícito
EXECUTE A=0x0C - B=0x05
        ALU: M=0 S=0110 Cn=0
RESULT  A=0x07   Z=0  C=1
PC → 0x05
```

---

# PARTE B — TAREAS

Orden recomendado: **B.0 → B.1 → B.2 → B.3**, con **B.4 en paralelo** durante todo el proceso.

Cada tarea indica sus dependencias. Las tareas sin dependencias entre sí pueden ejecutarse en conversaciones separadas.

## Estado (2026-08-08)

| Tarea | Estado | Dónde | Pruebas |
|---|---|---|---|
| B.0 Mapa de memoria | ✅ Congelado | A.6 de este documento | — |
| B.1 Simulador | ✅ Implementado | `sim/` | 54 |
| B.2 Ensamblador | ✅ Implementado | `asm/` | 211 |
| B.3 Firmware del Arduino | ✅ Implementado, **sin probar en hardware** | `firmware/` | 193 |
| B.4 Documentación | 🔄 En curso | los tres `.md` de la raíz | — |

**Total: 458 pruebas en verde.** Cómo ejecutarlo todo: `instrucciones.md`.

Las descripciones de abajo se conservan como especificación de cada tarea: son lo que se pidió, y sirven para verificar que lo entregado lo cumple.

---

## B.0 — Mapa de memoria (decisión de diseño) ✅

**Depende de:** nada.
**Bloquea a:** B.1, B.2.

**Objetivo:** confirmar o ajustar la propuesta de A.6 y dejarla congelada.

**Puntos a resolver:**
1. ¿La división 192/64 es adecuada, o conviene otro reparto?
2. ¿Se reserva alguna zona especial (vector de arranque, zona de E/S mapeada)?
3. ¿Cómo se cargan las constantes iniciales en la zona de datos? (El programa de referencia asume que el 4 ya está en la dirección 204.) Opciones: directiva del ensamblador tipo `.DB`, o comando serial de escritura directa.
4. ¿El ensamblador emite un solo binario de 256 bytes, o programa y datos por separado?

**Entregable:** sección de mapa de memoria lista para reemplazar A.6, con la decisión sobre carga de constantes.

---

## B.1 — Simulador del procesador ✅

**Depende de:** B.0.
**Bloquea a:** nada (pero facilita B.2 y B.3).

**Objetivo:** emular el CPU completo en software, en la PC. Es la **referencia de verdad** para depurar el hardware después.

**Requisitos:**
- Memoria de 256 bytes, inicializada en `0x00`.
- Registros A, B (8 bits), PC (8 bits), IR (8 bits), banderas Z y C.
- Las 16 instrucciones de A.5, con la semántica exacta de la tabla.
- **Aritmética en complemento a 2**, con truncado a 8 bits.
- **Solo las 5 operaciones de ALU actualizan banderas** (regla de A.5).
- Ejecución paso a paso y continua.
- Volcado de estado en el formato de A.9.
- Detección de bucles infinitos (límite de ciclos configurable).

**Criterio de aceptación:** el programa de referencia de A.7 produce `OUT = 12` y termina en `HLT`.

**Pruebas adicionales obligatorias:**

| Caso | Entrada | Esperado |
|---|---|---|
| Suma simple | A=3, B=2, ADD | A=5, Z=0 |
| Overflow de suma | A=255, B=1, ADD | A=0, Z=1, C=1 |
| Resta positiva | A=5, B=3, SUB | A=2, Z=0 |
| Resta negativa | A=3, B=5, SUB | A=254 (−2), Z=0 |
| Resta a cero | A=5, B=5, SUB | A=0, **Z=1** |
| AND | A=0xCC, B=0xAA | A=0x88 |
| OR | A=0xCC, B=0xAA | A=0xEE |
| XOR | A=0xCC, B=0xAA | A=0x66 |
| NOT vía XOR | A=0x0F, B=0xFF, XOR | A=0xF0 |
| STA no toca banderas | SUB (Z=1) → STA → JZ | El salto **sí** ocurre |

---

## B.2 — Ensamblador de dos pasadas ✅

**Depende de:** B.0.
**Bloquea a:** nada.

**Objetivo:** convertir texto fuente en bytes de máquina.

**Sintaxis a soportar:**

```asm
; comentarios con punto y coma
LOOP:  LDA 200          ; etiqueta + instrucción
       LDI A,#12        ; inmediato con #
       LDI B,#0xFF      ; hexadecimal
       JNZ LOOP         ; etiqueta como operando
       HLT
```

**Requisitos:**
- **Primera pasada:** recorrer el fuente, calcular la dirección de cada instrucción (recordando que ocupan 1 o 2 bytes) y construir la tabla de símbolos con las etiquetas.
- **Segunda pasada:** generar los bytes, resolviendo las etiquetas a direcciones.
- Aceptar números en decimal (`12`), hexadecimal (`0xFF` o `$FF`) y binario (`0b1010`).
- Distinguir `LDI A` de `LDI B` (opcodes distintos, `0011` y `0100`).
- Ignorar mayúsculas/minúsculas en nemónicos.
- Directiva para datos iniciales (según lo decidido en B.0).

**Errores que debe detectar y reportar con número de línea:**
- Nemónico desconocido
- Etiqueta no definida
- Etiqueta duplicada
- Operando fuera de rango (>255 o negativo)
- Instrucción de 2 bytes sin operando, o de 1 byte con operando
- Programa que excede la zona de programa

**Salida:** arreglo de bytes + listado de ensamblado (dirección, bytes, fuente) para incluir en la documentación.

**Criterio de aceptación:** ensamblar el programa de A.7 y que su salida, ejecutada en el simulador de B.1, dé 12.

---

## B.3 — Código del Arduino (unidad de control) ✅

**Depende de:** B.0. Idealmente después de B.1 (misma lógica, ya validada).

**Objetivo:** el firmware completo del Arduino Mega.

**Requisitos:**
- Matriz de memoria de 256 bytes.
- Variables PC, IR, MAR, banderas.
- Bucle fetch–decode–execute con microciclos variables (A.8).
- `switch` sobre los 16 opcodes.
- Control de los pines: bus de datos (8), lectura de F (8), clocks de A y B (2), select del mux (1), M, S3–S0, C̄n (6). **Total ~25 pines.**
- Constantes de la ALU según A.3:

```cpp
#define ALU_ARITMETICO  LOW
#define ALU_LOGICO      HIGH
#define ALU_ADD   0b1001
#define ALU_SUB   0b0110
#define ALU_AND   0b1011
#define ALU_OR    0b1110
#define ALU_XOR   0b0110   // mismo S que SUB; los distingue M
#define CN_ADD    HIGH
#define CN_SUB    LOW
```

- Modos RUN y STEP (A.9).
- Decodificación de 7 segmentos en software, hexadecimal completo (0–F).
- **Nunca** calcular una operación de ALU en software: siempre configurar el 181 y leer F. La única excepción permitida es `Z = (F == 0)`, que es una lectura del resultado, no un cálculo.

**Protocolo serial a definir** (comandos mínimos):

| Comando | Función |
|---|---|
| `LOAD <dir> <byte>` | Escribe un byte en memoria |
| `RUN` | Ejecuta hasta HLT |
| `STEP` | Avanza un microciclo |
| `RESET` | PC=0, registros y banderas a 0 |
| `DUMP <ini> <fin>` | Vuelca memoria |
| `STATE` | Imprime el estado actual |

La salida debe ser **legible por humanos y parseable por Processing** a la vez (por ejemplo, líneas `clave=valor` además del formato bonito).

---

## B.4 — Documentación (en paralelo) 🔄

**Depende de:** nada. Se avanza continuamente.

**Secciones que ya pueden escribirse por completo con este documento:**

1. Introducción y objetivos
2. Arquitectura general (von Neumann, diagrama de bloques)
3. Diseño de la ALU y caracterización del 74LS181
4. Formato de instrucción y modos de direccionamiento
5. Set de instrucciones completo
6. Mapa de memoria
7. Ciclo de instrucción
8. **Justificación de decisiones de diseño** ← la sección diferenciadora

**Argumentos ya preparados para la sección 8 y para la defensa:**

- **Complemento a 2 vs. complemento a 1:** el complemento a 1 tiene doble representación del cero (`00000000` y `11111111`), lo que rompe la bandera Z y obliga a un acarreo de retorno (*end-around carry*). Además el 74LS181 implementa complemento a 2 de forma nativa.
- **La resta en el 74LS181:** el datasheet (pág. 2) documenta que el chip genera internamente el complemento a 1 del sustraendo, produciendo A−B−1, y que se requiere un acarreo forzado para obtener A−B. Es decir, `A + (NOT B) + 1`. **Se puede citar el datasheet directamente.**
- **Instrucción de longitud variable:** característica CISC. Contrastar con RISC (longitud fija, más opcodes desperdiciados o menos espacio de direcciones). Con 4 bits de opcode y 1 byte fijo solo habría 16 direcciones de memoria; la longitud variable da 256.
- **Solo A y B en hardware:** separación entre ruta de datos (física) y unidad de control (software). PC, IR y MAR no necesitan existir físicamente porque el Arduino ya es la unidad de control.
- **El mux 74LS157:** el resultado de la ALU nunca pasa por el Arduino. Se puede señalar el cable físico. Responde directamente al requisito de que el Arduino no realice operaciones.
- **`A XOR 0xFF` = complemento a 1:** cómo suplir la ausencia de una instrucción NOT, igual que hacen arquitecturas RISC reales que no tienen NOT dedicado.
- **Por qué no se usa el pin A=B como bandera Z:** solo funciona en modo resta con C̄n=H, y es de colector abierto. Calcular `Z` leyendo el bus F es más confiable y funciona para todas las operaciones.
- **Tres modos de direccionamiento** (directo, inmediato, implícito) en un set de 16 instrucciones.
- **Saltos condicionales → Turing-completitud:** con JNZ se construyen bucles, lo que permite algoritmos iterativos como la multiplicación por sumas repetidas.

**Lecturas pendientes exigidas por el ingeniero:** capítulos 11 y 12 de *Fundamentos de diseño lógico y de computadoras* (Morris Mano), y el tema RISC vs CISC.

---

# PARTE C — LO QUE NO ESTÁ DECIDIDO

Ninguna tarea debe asumir una respuesta a los puntos **abiertos**. Si una tarea los necesita, debe **reportarlo** en lugar de improvisar.

> ⚠️ **La numeración de esta lista es estable.** Los puntos 4 y 5 se citan por número desde `firmware/microprocesador/display.h`, `isa.h`, `nucleo.cpp`, `instrucciones.md` y dos archivos de pruebas. Al resolver un punto se marca en su sitio; **nunca se renumera la lista**.

1. **¿PCB fabricado o basta placa perforada soldada?** 🔴 **ABIERTO.** Pregunta al ingeniero. Define el cronograma de las semanas 9–11. Consultar antes de la semana 6.

2. ~~**Mapa de memoria definitivo**~~ ✅ **RESUELTO (2026-08-08, B.0).** Split 192/64 confirmado, sin zona reservada. Ver A.6.

3. ~~**Mecanismo de carga de constantes iniciales**~~ ✅ **RESUELTO (2026-08-08, B.0).** Ambos mecanismos, no excluyentes: directiva `.DB` en el ensamblador para lo reproducible, y comando serial `LOAD`/`LOADB` para los datos que el ingeniero elija en vivo. Ver A.6.

4. **Display de 7 segmentos: ánodo o cátodo común** 🔴 **ABIERTO.** Pendiente de compra. Aislado en `firmware/microprocesador/display.h` tras `#define DISPLAY_ANODO_COMUN`: resolverlo es cambiar un 1 por un 0.

5. **Semántica exacta del carry en SUB** 🔴 **ABIERTO.** El diseño asume que C̄n+4 en bajo indica que no hubo préstamo (A≥B). **Debe verificarse experimentalmente** con el 181 en protoboard antes de darlo por cierto. Aislado tras `#define CARRY_SUB_INVERTIDO` en `firmware/microprocesador/isa.h`.

6. **Interfaz Processing** 🔴 **ABIERTO.** Diseñada pero no especificada en detalle. Es la última prioridad (semanas 12–13); no debe adelantarse al hardware.

---

# PARTE D — REGLAS PARA QUIEN EJECUTE UNA TAREA

1. **La Parte A es inmutable.** No cambiar opcodes, formato, tabla de la ALU ni semántica de banderas.
2. **El programa de A.7 es el caso de prueba canónico.** Todo entregable que pueda ejecutarlo debe producir 12.
3. **El Arduino no calcula.** Cualquier propuesta que resuelva una operación aritmética o lógica en software viola el requisito central del proyecto.
4. **Ante un vacío, preguntar.** Es preferible detenerse a inventar una especificación que luego contradiga a otra tarea.
5. **Ante una contradicción entre este documento y una idea nueva**, este documento gana hasta que se actualice explícitamente.