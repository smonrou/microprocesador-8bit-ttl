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
5. Un proyecto entregado en protoboard **no es elegible para exoneración** del examen final. El entregable debe ser un circuito soldado. *(Nota 2026-10: **superado por C.1 (2026-09-17)**: el ingeniero aceptó la entrega en protoboards. Si esa entrega conserva la exoneración sigue **sin confirmar**.)*

## A.2 Hardware

| Componente | Implementación | Estado |
|---|---|---|
| ALU | 2× **SN74LS181** en cascada (4+4 bits) | Comprados |
| Registro A | 1× **74LS273** (8 bits) | Decidido |
| Registro B | 1× **74LS273** (8 bits) | Decidido |
| Mux de entrada a A | 2× **74LS157** | Decidido |
| Contador de programa (PC) | 2× **74LS161** en cascada (8 bits, carga paralela síncrona desde el bus D, clear asíncrono compartido con los 273). Q0–Q7 → Mega A8–A15 (PORTK) | Decidido (2026-09-25, por orden del ingeniero). Montado y probado en la fase 4 del montaje (cuenta, carga paralela y vuelta de 0xFF a 0x00 verificados el 2026-09-30) |
| Unidad de control / memoria / reloj | **Arduino Mega** | Comprado, conectado y funcionando: el procesador funciona completo en hardware (las 6 fases del montaje probadas, 2026-10-02) |
| Registro de salida | 1× **74LS273** (engancha el bus F al ejecutar OUT) | Decidido (2026-09-04) |
| Salida del procesador | **8 LEDs en binario**, uno por bit (bit 7 a la izquierda). Registro de salida → 1× buffer de corriente → 8 LEDs; LED encendido = bit en 1. Diseño: **74LS244** con LEDs rojos/verdes/amarillos y 220 Ω a GND. **Montaje real (2026-09-28): 74LS240**, que es el chip que se tiene en físico: mismo pinout pero invierte, así que cada LED va de +5 V a la salida (+5 V → LED → 330 Ω → Y) y enciende con bit = 1; sirve cualquier color. Sin decodificación: el bit ya es la magnitud. El Arduino no convierte nada | Decidido (2026-09-17, reemplaza los 8 dígitos de 7 segmentos con 74LS151/74LS138); buffer real 74LS240 (2026-09-28) |
| Interfaz de observación | Depurador gráfico en Python/Tkinter vía serial (`depurador/`) | **Entregado** (cierra C.6). Processing queda como extra opcional |

**Camino de datos:** las salidas F de la ALU regresan a las entradas del registro A **a través del mux 74LS157**. El resultado nunca pasa por el Arduino. El mux selecciona entre "bus del Arduino" y "salida de la ALU".

**El PC es hardware** (2× 74LS161): el Arduino no lo calcula, solo pulsa su reloj para contar o lo pulsa con /LOAD en bajo para cargar la dirección de un salto desde el bus D, y lee su valor por PORTK porque la RAM vive en el Arduino. **IR y MAR siguen siendo variables en el Arduino.** *(Cambio a la Parte A del 2026-09-25: el ingeniero no aceptó el PC simulado. Hasta esa fecha decía "PC, IR y MAR son variables en el Arduino". Ver §22 de `proyecto_microprocesador_8bits.md`.)*

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
| `0001` | `MOV A,[dir]` | 2 | Directo | Mem[dir] → A | No |
| `0010` | `MOV B,[dir]` | 2 | Directo | Mem[dir] → B | No |
| `0011` | `MOV A,inm` | 2 | Inmediato | n → A | No |
| `0100` | `MOV B,inm` | 2 | Inmediato | n → B | No |
| `0101` | `MOV [dir],A` | 2 | Directo | A → Mem[dir] | No |
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

**Nemónicos estilo x86 (cambio de sintaxis, 2026-09-28):** las cinco instrucciones de transferencia comparten la palabra `MOV` y se distinguen por la forma de los operandos, como en el 8086: `[dir]` entre corchetes es direccionamiento directo, un valor pelado es inmediato (sin `#`), y `A`/`B` nombran el registro. Solo cambió el texto: opcodes, codificación, longitudes, microciclos y banderas son los mismos. Motivo: otro equipo usaba los mismos nemónicos (`LDA`, `LDB`, `LDI A`, `LDI B`, `STA`). Formas que no existen (`MOV [dir],B`, `MOV A,B`, memoria a memoria...) son error del ensamblador.

**Las 6 funciones aprobadas por el ingeniero son:** ADD, SUB, AND, OR, XOR, OUT. Las demás son infraestructura (transferencia de datos y control de flujo).

**Regla de banderas — crítica:** solo las cinco operaciones de ALU actualizan Z y C. Ningún `MOV` (cargas ni guardado) **las modifica**. Esto es indispensable: el programa de referencia hace `SUB` → `MOV [201],A` → `JNZ`, y ese guardado intermedio no debe destruir la bandera.

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
      MOV A,0
      MOV [200],A    ; resultado = 0
      MOV A,3
      MOV [201],A    ; contador = 3

LOOP: MOV A,[200]
      MOV B,[204]    ; el 4 vive en la dirección 204
      ADD
      MOV [200],A    ; resultado += 4

      MOV A,[201]
      MOV B,1
      SUB
      MOV [201],A    ; contador -= 1
      JNZ LOOP

      MOV A,[200]
      OUT            ; muestra 12
      HLT
```

**Precondición:** la dirección 204 debe contener el valor 4 antes de ejecutar.
**Resultado esperado:** `OUT` muestra `12` (`0x0C`).

## A.8 Ciclo fetch–decode–execute

| Fase | Acción | Dónde |
|---|---|---|
| FETCH | `IR ← Mem[PC]`; `PC++` | Arduino (RAM, IR) + PC en hardware (74LS161) |
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

**Ejemplo, instrucción de 2 bytes (MOV A,inm):**
```
T1  FETCH    IR ← Mem[PC];  PC++
T2  DECODE   opcode 0011 → MOV A,inm, 2 bytes
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

## Estado (actualizado 2026-10-01; la versión original de la tabla es del 2026-08-08)

| Tarea | Estado | Dónde | Pruebas |
|---|---|---|---|
| B.0 Mapa de memoria | ✅ Congelado | A.6 de este documento | — |
| B.1 Simulador | ✅ Implementado | `sim/` | 54 |
| B.2 Ensamblador | ✅ Implementado | `asm/` | 265 |
| B.3 Firmware del Arduino | ✅ Implementado; `referencia.load` ya corrió en hardware (2026-10-01) | `firmware/` | 189 |
| Depurador Tkinter | ✅ Entregado | `depurador/` | 270 |
| Montaje físico | ✅ Las 6 fases probadas (2026-10-02) | `montaje/` | 24 |
| B.4 Documentación | 🔄 En curso | los `.md` de la raíz (`contexto_proyecto`, `proyecto_microprocesador_8bits`, `instrucciones`, `simulacion_vs_fisico`, `contexto_montaje`; además `README`, `CLAUDE` y el histórico `progreso-simulacion`) | — |

**Total: 802 pruebas en verde** (sim 54, asm 265, firmware 189, depurador 270, montaje 24). Cómo ejecutarlo todo: `instrucciones.md`. Las cifras anteriores (458 = 54 + 211 + 193, 2026-08-08) son históricas.

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
| MOV [dir],A no toca banderas | SUB (Z=1) → MOV [dir],A → JZ | El salto **sí** ocurre |

---

## B.2 — Ensamblador de dos pasadas ✅

**Depende de:** B.0.
**Bloquea a:** nada.

**Objetivo:** convertir texto fuente en bytes de máquina.

**Sintaxis a soportar:**

```asm
; comentarios con punto y coma
LOOP:  MOV A,[200]      ; etiqueta + instrucción (directo: corchetes)
       MOV A,12         ; inmediato: valor pelado, sin #
       MOV B,0xFF       ; hexadecimal
       MOV [200],A      ; guardar A en memoria
       JNZ LOOP         ; etiqueta como operando
       HLT
```

**Requisitos:**
- **Primera pasada:** recorrer el fuente, calcular la dirección de cada instrucción (recordando que ocupan 1 o 2 bytes) y construir la tabla de símbolos con las etiquetas.
- **Segunda pasada:** generar los bytes, resolviendo las etiquetas a direcciones.
- Aceptar números en decimal (`12`), hexadecimal (`0xFF` o `$FF`) y binario (`0b1010`).
- Elegir el opcode de `MOV` por la forma de los operandos (`MOV A,[dir]`=`0001` … `MOV [dir],A`=`0101`; 2026-09-28, antes `LDA`/`LDB`/`LDI A`/`LDI B`/`STA`).
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
- Variables IR, MAR y banderas (el PC es hardware: 2× 74LS161, el firmware lo cuenta con pulsos de reloj y /LOAD, y lo lee por PORTK).
- Bucle fetch–decode–execute con microciclos variables (A.8).
- `switch` sobre los 16 opcodes.
- Control de los pines: bus de datos (8), lectura de F (8), clocks de A y B (2), select del mux (1), M, S3–S0, C̄n (6). **Total ~25 pines** en el diseño original; con CLEAR, el reloj de salida, C̄n+4 y el PC (reloj, /LOAD y PORTK A8–A15) son 38 de los 70 pines del Mega (los pines 3–6 del antiguo display ya no se manejan).
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
- **Nunca** manejar la salida desde el Arduino. La salida física es binaria: bus F → 74LS273 → buffer (74LS244 en el diseño, 74LS240 en el montaje real) → LEDs, por cable; el firmware solo pulsa el reloj del registro de salida al ejecutar `OUT`. El depurador sí puede mostrar el valor en el formato que sea: es herramienta de observación, no la salida del procesador.
- **Nunca** calcular una operación de ALU en software: siempre configurar el 181 y leer F. La única excepción permitida es `Z = (F == 0)`, que es una lectura del resultado, no un cálculo.

**Protocolo serial** (los seis comandos mínimos se pidieron así; el firmware implementa además `LOADB`, `BORRAR`, `VEL` y `HELP`):

| Comando | Función |
|---|---|
| `LOAD <dir> <byte>` | Escribe un byte en memoria |
| `LOADB <dir> <hex...>` | Escribe un bloque de bytes en una línea (lo que genera el `.load`) |
| `RUN` | Ejecuta hasta HLT |
| `STEP` | Avanza un microciclo |
| `RESET` | PC=0, registros y banderas a 0 (conserva la memoria) |
| `BORRAR` | Borra toda la memoria |
| `DUMP [ini [fin]]` | Vuelca memoria |
| `STATE` | Imprime el estado actual |
| `VEL <ms>` | Retardo entre instrucciones en `RUN` (0–5000) |
| `HELP` | Lista los comandos |

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
- **PC en hardware (2× 74LS161), IR y MAR en el Arduino:** incrementar el PC es una suma, y el Arduino no calcula; por eso el PC lo cuenta un contador físico. El Arduino hace de RAM, así que lee el PC por PORTK igual que una RAM recibe sus líneas de dirección. *(Hasta el 2026-09-25 el argumento era "solo A y B en hardware"; el ingeniero lo rechazó para el PC.)*
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

1. ~~**¿PCB fabricado o basta placa perforada soldada?**~~ ✅ **RESUELTO (2026-09-17).** El ingeniero acepta la entrega **en protoboards**: no hace falta PCB ni placa perforada soldada. ⚠️ **Sin confirmar:** si la entrega en protoboard conserva la elegibilidad para exonerar el examen final (antes había dicho que no; ver §14 del registro de diseño). Preguntarlo explícitamente.

2. ~~**Mapa de memoria definitivo**~~ ✅ **RESUELTO (2026-08-08, B.0).** Split 192/64 confirmado, sin zona reservada. Ver A.6.

3. ~~**Mecanismo de carga de constantes iniciales**~~ ✅ **RESUELTO (2026-08-08, B.0).** Ambos mecanismos, no excluyentes: directiva `.DB` en el ensamblador para lo reproducible, y comando serial `LOAD`/`LOADB` para los datos que el ingeniero elija en vivo. Ver A.6.

4. ~~**Display de 7 segmentos: ánodo o cátodo común**~~ ✅ **RESUELTO POR ELIMINACIÓN (2026-09-17).** La salida pasó a 8 LEDs (A.2); ya no hay display de 7 segmentos. El buffer quedó fijo en **74LS244** con LEDs que encienden en alto. Único requisito heredado: LEDs rojos, verdes o amarillos (caída ~2 V), porque en alto el 244 entrega 2.4–3.4 V y no alcanza para azul o blanco (~3 V). *(Montaje real, 2026-09-28: se usó un **74LS240**, que invierte; con los LEDs de +5 V a la salida y 330 Ω enciende igual con bit = 1 y sirve cualquier color.)*

5. ~~**Semántica exacta del carry en SUB**~~ ✅ **RESUELTO (2026-09-29, fase 2 del montaje).** Medido en protoboard, C̄n+4 de la ALU ALTA (pin 16) con C̄n=0: 5−3 → 0.12 V (bajo), 3−5 → 4.26 V (alto), 5−5 → 0.12 V (bajo). Confirma el supuesto del diseño: C̄n+4 en bajo = no hubo préstamo (A≥B). `#define CARRY_SUB_INVERTIDO 0` en `firmware/microprocesador/isa.h` queda como está.

6. ~~**Interfaz de observación**~~ ✅ **RESUELTO.** Se entregó como depurador gráfico en Python/Tkinter (`depurador/`, manual en `depurador/LEEME.md`): registros en cuatro formatos, banderas, líneas de control de la ALU, memoria, desensamblado y ejecución microciclo a microciclo, contra el Arduino real o contra un servidor serie de prueba. Una interfaz en **Processing** queda solo como extra opcional.

---

# PARTE D — REGLAS PARA QUIEN EJECUTE UNA TAREA

1. **La Parte A es inmutable.** No cambiar opcodes, formato, tabla de la ALU ni semántica de banderas.
2. **El programa de A.7 es el caso de prueba canónico.** Todo entregable que pueda ejecutarlo debe producir 12.
3. **El Arduino no calcula.** Cualquier propuesta que resuelva una operación aritmética o lógica en software viola el requisito central del proyecto.
4. **Ante un vacío, preguntar.** Es preferible detenerse a inventar una especificación que luego contradiga a otra tarea.
5. **Ante una contradicción entre este documento y una idea nueva**, este documento gana hasta que se actualice explícitamente.