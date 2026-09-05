# INSTRUCCIONES DE USO — B.0, B.1, B.2 y B.3

> Manual operativo del software del proyecto. Para las **especificaciones** (opcodes, tabla de la ALU, formato de instrucción) la fuente de verdad sigue siendo `contexto_proyecto.md`; para el **registro de decisiones**, `proyecto_microprocesador_8bits.md`.

---

## Requisitos previos

| Requisito | Comprobación |
|---|---|
| Python 3.8 o superior | `python --version` |
| pytest | `python -m pip install pytest` |

Todos los comandos de este documento se ejecutan **desde la raíz del proyecto** (la carpeta que contiene `sim/`, `asm/`, `firmware/`, `tests/` y `pytest.ini`).

```
progra/
├── contexto_proyecto.md              ← especificación congelada
├── proyecto_microprocesador_8bits.md ← bitácora de decisiones
├── instrucciones.md                  ← este archivo
├── demo.py                           ← secuencia de demostración
├── pytest.ini
├── sim/          ← B.1: simulador del procesador
├── asm/          ← B.2: ensamblador de dos pasadas
├── firmware/     ← B.3: código del Arduino
├── programas/    ← programas fuente .asm y sus salidas
└── tests/        ← 458 pruebas (54 de B.1 + 211 de B.2 + 193 de B.3)
```

**¿Con prisa?** Salta a la [secuencia de demostración](#secuencia-de-demostración): `python demo.py` recorre todo lo construido en ocho pasos.

### Comprobación rápida de que todo funciona

```
python -m pytest -q
```

Debe terminar en `458 passed`. Si algo falla, no sigas: el resto de este documento asume una suite verde.

> Las pruebas de B.3 compilan C++ con `g++`. Si no lo tienes en el `PATH`, esas pruebas se **saltan** con un aviso en vez de fallar, y el resto sigue funcionando.

---

# B.0 — Mapa de memoria

B.0 no es software, es una **decisión de diseño congelada**. No se "ejecuta"; se respeta. Esta sección explica cómo aplicarla al escribir programas.

## El mapa

Espacio único de 256 bytes (`0x00`–`0xFF`), von Neumann: instrucciones y datos comparten direcciones.

| Rango | Tamaño | Uso |
|---|---|---|
| `0x00`–`0xBF` | 192 bytes | **Programa.** La ejecución siempre arranca en `0x00`. |
| `0xC0`–`0xFF` | 64 bytes | **Datos.** Variables y constantes. |

**La separación es una convención, no una restricción de hardware.** Al ser von Neumann, nada impide físicamente que una instrucción escriba en la zona de programa. La división existe para que los programas sean legibles y para poder explicar el mapa en la defensa.

Cómo lo hace cumplir el ensamblador (B.2):

| Caso | Trato |
|---|---|
| Instrucción por encima de `0xBF` | **Error duro** |
| `.DB` en cualquier dirección | Legal, con advertencia si cae bajo `0xC0` |
| Puntero de ensamblado pasa de `0xFF` | **Error duro** |
| Dos sentencias escriben la misma dirección | **Error duro** (solape) |

## Reglas al escribir un programa

1. **Empieza en `0x00`.** No hace falta escribir `.ORG 0x00`: es el valor inicial del puntero. Si tu programa no emite nada en `0x00`, el ensamblador te avisa (la CPU arrancaría leyendo `NOP`s).
2. **Pon los datos a partir de `0xC0`** (192 decimal), con `.ORG`.
3. **Toda la memoria vale `0x00` al arrancar**, y `0x00` decodifica como `NOP`. Una variable que empieza en cero no necesita `.DB` — pero declararla igual documenta su existencia.

## Cargar constantes iniciales — dos mecanismos, no excluyentes

| Mecanismo | Cuándo | Dónde |
|---|---|---|
| Directiva `.DB` | Constantes conocidas al ensamblar. Reproducible y documentable. | En el `.asm` |
| Comando serial `LOAD <dir> <byte>` | Datos que el ingeniero elige **en vivo** durante la defensa. | Monitor serial (B.3) |

`.DB` cubre el caso de prueba reproducible; `LOAD` cubre la entrada en vivo que exige el requisito A.1. El ensamblador genera además un archivo `.load` con los comandos ya listos para pegar en el monitor serial.

## Formato de salida

El ensamblador emite **un solo binario de 256 bytes**, no programa y datos por separado. Coherente con von Neumann: un único espacio de direcciones, una sola carga.

---

# B.1 — Simulador del procesador

Emula el CPU completo en software. Es la **referencia de verdad** para depurar el hardware después: si el circuito físico y el simulador discrepan ejecutando el mismo programa, el circuito está mal.

El simulador se usa **como biblioteca de Python** (no tiene CLI propio). Para ejecutar un programa de principio a fin desde la terminal, usa `python -m asm ... --run` (ver B.2).

## Módulos

| Archivo | Qué contiene |
|---|---|
| `sim/isa.py` | `OPCODE_TABLE` — las 16 instrucciones. **Fuente única de verdad del ISA.** |
| `sim/alu.py` | Funciones puras de la ALU: `add`, `sub`, `bit_and`, `bit_or`, `bit_xor` |
| `sim/memory.py` | `Memory` — 256 bytes |
| `sim/cpu.py` | `CPU` — registros, banderas, ciclo fetch/decode/execute |
| `sim/trace.py` | Formato de volcado de estado de A.9 |
| `sim/programs.py` | Programa de referencia A.7 en bytes crudos |
| `sim/exceptions.py` | `CpuHaltedError`, `CycleLimitExceeded` |

## Ejecutar un programa (modo RUN)

```python
from sim.cpu import CPU
from sim.memory import Memory

memoria = Memory()
memoria.load_bytes([0x30, 0x05,   # LDI A,#5
                    0x40, 0x07,   # LDI B,#7
                    0x60,          # ADD
                    0xB0,          # OUT
                    0xC0])         # HLT

cpu = CPU(memoria)
cpu.run()

print(cpu.output)   # [12]
print(cpu.a)        # 12
```

`run()` ejecuta hasta `HLT`. Devuelve el número de instrucciones ejecutadas.

### Estado accesible tras ejecutar

| Atributo | Contenido |
|---|---|
| `cpu.a`, `cpu.b` | Registros A y B (0–255) |
| `cpu.pc`, `cpu.ir` | Contador de programa e instrucción actual |
| `cpu.z`, `cpu.c` | Banderas cero y acarreo (0 o 1) |
| `cpu.halted` | `True` si se ejecutó `HLT` |
| `cpu.output` | Lista de valores emitidos por `OUT` |
| `cpu.instruction_count` | Instrucciones completadas |
| `cpu.memory.read(dir)` | Contenido de una celda |

## Modo STEP — un microciclo por llamada

`step()` avanza **un microciclo**, no una instrucción completa. Es la herramienta de depuración que más valor da en la defensa.

```python
cpu = CPU(memoria)

while not cpu.halted:
    resultado = cpu.step()
    print(resultado.label, "| instrucción completada:", resultado.completed)
```

Salida (primeras llamadas):

```
FETCH   | instrucción completada: False
DECODE  | instrucción completada: False
FETCH2  | instrucción completada: False
EXECUTE | instrucción completada: True     ← aquí terminó LDI A,#5
FETCH   | instrucción completada: False
...
```

### Cuántos microciclos consume cada instrucción

| Forma | Instrucciones | Pasos |
|---|---|---|
| ALU, 1 byte | ADD, SUB, AND, OR, XOR | **5** — FETCH, DECODE, EXECUTE, WAIT, WRITE |
| Control/salida, 1 byte | NOP, HLT, OUT | **3** — FETCH, DECODE, EXECUTE |
| 2 bytes | LDA, LDB, LDI A, LDI B, STA, JMP, JZ, JNZ | **4** — FETCH, DECODE, FETCH2, EXECUTE |

Las operaciones de ALU gastan dos pasos más porque el hardware real necesita esperar la propagación del 74LS181 (`WAIT`) y luego capturar el resultado por el mux (`WRITE`).

**`step()` después de `HLT` lanza `CpuHaltedError`** — es deliberado: un `step()` que no hace nada se confunde con un bug.

## Volcado de estado en formato A.9

```python
dumps = cpu.run_to_completion_with_trace()
print(dumps[6])
```

```
─── Ciclo 7 ───
FETCH   PC=0x0C  →  IR=0x60 (ADD)
DECODE  Opcode 0110 | 1 byte | modo implícito
EXECUTE A=0x00 + B=0x04
        ALU: M=0 S=1001 Cn=1
RESULT  A=0x04   Z=0  C=0
PC → 0x0D
```

**"Ciclo N" numera instrucciones completadas**, no microciclos. La línea `ALU:` muestra la configuración exacta de pines que el Arduino enviará al 74LS181 — sirve para contrastar simulador contra hardware con el multímetro en la mano.

Para volcar un solo ciclo desde `step()`:

```python
from sim.trace import format_cycle

resultado = cpu.step()
if resultado.completed:
    print(format_cycle(resultado.trace))
```

## Detección de bucles infinitos

```python
cpu.run(max_cycles=200)   # por defecto 10000
```

Si se supera el límite sin llegar a `HLT`, lanza `CycleLimitExceeded` con el PC y el conteo. **Nunca se cuelga.**

```python
from sim.exceptions import CycleLimitExceeded

try:
    cpu.run(max_cycles=200)
except CycleLimitExceeded as error:
    print(f"bucle infinito en PC=0x{error.pc:02X}")
```

## Probar la ALU aislada

Útil para contrastar contra el 74LS181 real en protoboard (sección 7 de la bitácora):

```python
from sim import alu

resultado, z, c = alu.sub(5, 3)
print(resultado, z, c)   # 2 0 1
```

Todas devuelven `(resultado, z, c)`. Convención del carry:

- **ADD** — `c=1` si hubo desbordamiento por encima de 255.
- **SUB** — `c=1` significa que **no** hubo préstamo (A ≥ B). `c=0` significa préstamo (A < B).
- **AND / OR / XOR** — `c=0` siempre. En modo lógico (M=1) el acarreo no es significativo.

> ⚠️ La semántica del carry en SUB está **pendiente de verificación experimental** con el 181 en protoboard (Parte C, punto 5). El simulador asume la convención de arriba; confírmala antes de darla por cierta.

## Regla crítica de banderas

**Solo las cinco operaciones de ALU (ADD, SUB, AND, OR, XOR) modifican Z y C.** `LDA`, `LDB`, `LDI`, `STA`, los saltos, `NOP`, `OUT` y `HLT` las dejan intactas.

Esto es indispensable: el programa de referencia hace `SUB` → `STA` → `JNZ`, y si el `STA` borrara la bandera el bucle nunca terminaría. En el código está garantizado por estructura — solo la rama de ALU de `cpu.py` asigna `self.z` / `self.c`.

---

# B.2 — Ensamblador de dos pasadas

Convierte texto fuente `.asm` en bytes de máquina. Primera pasada: calcula direcciones y construye la tabla de símbolos. Segunda pasada: emite bytes resolviendo las etiquetas.

## Uso por línea de comandos

```
python -m asm programas/referencia.asm
```

Genera tres archivos junto al fuente:

| Archivo | Contenido | Para qué |
|---|---|---|
| `referencia.bin` | 256 bytes crudos | Cargar en el simulador |
| `referencia.lst` | Listado + tabla de símbolos | **Documentación** (B.4) |
| `referencia.load` | Comandos `LOADB <dir> <hex...>` | Pegar en el monitor serial (B.3) |

### Opciones

| Opción | Efecto |
|---|---|
| `-o CARPETA` | Escribe las salidas en otra carpeta |
| `--listing-only` | Imprime el listado por pantalla, no escribe nada |
| `--run` | Ensambla **y ejecuta** en el simulador B.1 |

### Ensamblar y ejecutar de una vez

```
python -m asm programas/referencia.asm --run
```

```
29 bytes emitidos (0x00–0x1B, 0xCC–0xCC)
  programas\referencia.bin
  programas\referencia.lst
  programas\referencia.load

Salida (OUT): [12]
Estado final: A=0x0C  B=0x01  PC=0x1C  Z=1  C=1
```

Es la demostración end-to-end más corta: fuente → bytes → ejecución → resultado.

## Sintaxis del lenguaje

```asm
; los comentarios empiezan con punto y coma

      LDI A,#0         ; inmediato: el # es obligatorio
      STA 200          ; directo: dirección, sin #
LOOP: LDA 200          ; etiqueta seguida de dos puntos
      LDB CUATRO       ; una etiqueta también sirve como dirección de dato
      ADD              ; implícito: sin operandos
      JNZ LOOP         ; etiqueta como destino de salto
      HLT

.ORG 204               ; mueve el puntero de ensamblado
CUATRO: .DB 4          ; emite bytes en la dirección actual
```

### Reglas

| Aspecto | Regla |
|---|---|
| Mayúsculas | Indiferentes, tanto en nemónicos como en etiquetas |
| Comentarios | Desde `;` hasta el final de la línea |
| Etiquetas | `NOMBRE:` — letras, dígitos y `_`, no empiezan por dígito |
| Espaciado | Libre. `LDI A,#12`, `LDI A , #12` y `LDI A #12` son equivalentes |

### Bases numéricas

| Base | Formatos | Ejemplo |
|---|---|---|
| Decimal | `12` | `LDA 200` |
| Hexadecimal | `0xFF` o `$FF` | `LDI A,#0xFF` |
| Binario | `0b1010` | `LDI B,#0b1010` |

Rango válido: **0 a 255**. Fuera de ahí es error.

### El `#` es estricto

| Modo | Instrucciones | Operando |
|---|---|---|
| Inmediato | `LDI A`, `LDI B` | **Requiere** `#` — el byte es el dato |
| Directo | `LDA`, `LDB`, `STA`, `JMP`, `JZ`, `JNZ` | **Prohibido** `#` — el byte es una dirección |
| Implícito | `ADD`, `SUB`, `AND`, `OR`, `XOR`, `OUT` | Sin operando |
| Sin operando | `NOP`, `HLT` | Sin operando |

`LDI A,5` (falta `#`) y `LDA #5` (sobra `#`) son errores. Es deliberado: atrapa la confusión clásica entre inmediato y directo.

> ⚠️ `LDI A` y `LDI B` son **opcodes distintos** (`0011` y `0100`). Escribir `LDI` a secas es error; el mensaje te recuerda las dos formas válidas.

### Directivas

**`.ORG <dirección>`** — mueve el puntero de ensamblado. No emite bytes.

```asm
.ORG 0xC0       ; a partir de aquí se ensambla en la zona de datos
```

Solo admite un literal numérico (no etiquetas, para evitar definiciones circulares). No puede llevar etiqueta delante.

**`.DB <valor>[, <valor>...]`** — emite bytes en la dirección actual.

```asm
.ORG 200
RESULTADO: .DB 0        ; una variable
TABLA:     .DB 1, 2, 3, 0xFF
```

### Etiquetas para saltos y para datos

Una sola tabla de símbolos sirve para ambas cosas:

```asm
LOOP: LDA CONTADOR      ; CONTADOR es una dirección de dato
      JNZ LOOP          ; LOOP es un destino de salto

.ORG 201
CONTADOR: .DB 3
```

Las **referencias hacia adelante funcionan** — usar una etiqueta antes de definirla es precisamente para lo que existen las dos pasadas.

## Uso desde Python

```python
from asm import assemble

resultado = assemble("""
    LDI A,#5
    LDI B,#7
    ADD
    OUT
    HLT
""")

print(list(resultado.binary[:5]))   # [48, 5, 64, 7, 96]
print(resultado.symbols)             # {}
```

### Qué devuelve `assemble()`

| Atributo | Contenido |
|---|---|
| `.binary` | 256 bytes (`bytes`), relleno de ceros |
| `.symbols` | `dict` de etiqueta → dirección |
| `.listing` | Listado de ensamblado, texto |
| `.load_script_bloques` | Comandos `LOADB`, varios bytes por línea. Es lo que escribe el CLI |
| `.load_script` | Comandos `LOAD`, un byte por línea. Disponible como respaldo |
| `.warnings` | Tupla de advertencias |
| `.spans` | Rangos `(inicio, fin)` de direcciones escritas |
| `.rows` | Filas del listado, estructuradas |

### Encadenar con el simulador

```python
from asm import assemble
from asm.examples import read_reference_source
from sim.cpu import CPU
from sim.memory import Memory

resultado = assemble(read_reference_source())

memoria = Memory()
memoria.load_bytes(resultado.binary)   # el binario se basta solo
cpu = CPU(memoria)
cpu.run()

print(cpu.output)   # [12]
```

No hace falta escribir constantes a mano: la directiva `.DB` ya las puso en el binario.

### Capturar errores

```python
from asm import assemble, AssemblyFailed

try:
    assemble("LDX 5\nLDA 300\n")
except AssemblyFailed as fallo:
    for error in fallo.errors:
        print(f"línea {error.line_number}: {error.message}")
```

## Errores que detecta

Todos se reportan **con número de línea** y eco de la línea culpable. Los errores se **acumulan dentro de cada fase** (parseo → pasada 1 → pasada 2) y se muestran juntos, pero se aborta al cambiar de fase: un nemónico desconocido tiene longitud desconocida, así que seguir produciría errores de dirección falsos.

| Error | Ejemplo que lo dispara |
|---|---|
| Nemónico desconocido | `LDX 5` |
| Etiqueta no definida | `JNZ NOEXISTE` |
| Etiqueta duplicada | `LOOP:` dos veces |
| Operando fuera de rango | `LDA 256`, `LDA -1` |
| Instrucción de 2 bytes sin operando | `LDA` solo |
| Instrucción de 1 byte con operando | `ADD 5` |
| Excede la zona de programa | Instrucción por encima de `0xBF` |
| Forma de operando incorrecta | `LDA #5`, `LDI A,5` |
| Literal mal formado | `LDA 0xZZ` |
| Desborde de memoria | Pasarse de `0xFF` |
| Solape | Dos sentencias escriben la misma dirección |

Ejemplo de salida:

```
2 errores de ensamblado
línea 1: nemónico desconocido: 'LDX'
    LDX 5
línea 2: operando fuera de rango: 300 (válido 0–255)
    LDA 300
```

## Advertencias (no detienen el ensamblado)

- **`.DB` en la zona de programa** — legal, pero probablemente no es lo que querías.
- **Nada emitido en `0x00`** — la ejecución arranca ahí y encontrará `NOP`s.

## Formato del listado

```
DIR  BYTES        LÍN  FUENTE
---  -----------  ---  --------------------------------------------
00   30 00          1        LDI A,#0
02   50 C8          2        STA 200        ; resultado = 0
04   10 C8          3  LOOP: LDA 200
...
CC   04            10  CUATRO: .DB 4

TABLA DE SÍMBOLOS
LOOP   = 0x04 (4)
CUATRO = 0xCC (204)
```

La columna `FUENTE` reproduce la línea **tal como se escribió**, con su sangría y sus comentarios. Un listado que embellece el fuente esconde lo que realmente tecleaste. La tabla de símbolos va ordenada por dirección, que es lo útil al leer un mapa de memoria.

---

# SECUENCIA DE DEMOSTRACIÓN

Ocho pasos que recorren todo lo construido, en el orden en que conviene enseñarlo. Pensada para la defensa, pero sirve igual como verificación completa después de tocar código.

## Ejecutarla

```
python demo.py             # los 8 pasos seguidos
python demo.py 4           # solo el paso 4
python demo.py 3 5 6       # varios pasos sueltos
python demo.py --lista     # ver los pasos disponibles
```

Cada paso es independiente. Si el ingeniero pregunta por algo concreto, se lanza ese paso solo sin volver a pasar por los anteriores.

## Antes de empezar

```
python -m pytest -q
```

Debe decir `265 passed`. Es lo primero que conviene enseñar: la suite completa en verde antes de tocar nada.

## Qué muestra cada paso

| # | Paso | Qué demuestra |
|---|---|---|
| 1 | Ensamblar el programa canónico | Las dos pasadas resuelven `LOOP` a `0x08` |
| 2 | Listado de ensamblado | Direcciones, bytes y fuente lado a lado |
| 3 | Ejecutar en el simulador | `4 × 3 = 12`, el binario se basta solo |
| 4 | Ejecución paso a paso | El ciclo fetch–decode–execute por dentro |
| 5 | Las 6 funciones aprobadas | ADD, SUB, AND, OR, XOR, OUT verificadas |
| 6 | **Datos elegidos en vivo** | El sistema es genérico, no una demo pregrabada |
| 7 | Detección de errores | El ensamblador reporta con número de línea |
| 8 | Script de carga serial | El puente hacia el Arduino (B.3) |

---

## Paso 1 — Ensamblar el programa canónico

```
python demo.py 1
```

```
Bytes emitidos: 29
Rangos:         0x00–0x1B, 0xCC–0xCC
Etiquetas:      {'LOOP': 8}
```

**Qué señalar:** la etiqueta `LOOP` se resolvió a `0x08` sin que nadie contara bytes a mano. Los dos rangos muestran la separación del mapa de memoria: el programa en la zona baja, la constante en la zona de datos.

---

## Paso 2 — Listado de ensamblado

```
python demo.py 2
```

```
DIR  BYTES        LÍN  FUENTE
---  -----------  ---  --------------------------------------------
00   30 00         12        LDI A,#0
02   50 C8         13        STA 200        ; resultado = 0
04   30 03         14        LDI A,#3
06   50 C9         15        STA 201        ; contador = 3
                   16
08   10 C8         17  LOOP: LDA 200
0A   20 CC         18        LDB 204        ; el 4 vive en la dirección 204
0C   60            19        ADD
...
LOOP = 0x08 (8)
```

**Qué señalar:** cada instrucción con su dirección y sus bytes. Se ve que `ADD` ocupa 1 byte (`60`) y `LDA` ocupa 2 (`10 C8`) — la longitud variable en acción. El nibble bajo del primer byte siempre es `0`, como manda el formato.

---

## Paso 3 — Ejecutar en el simulador

```
python demo.py 3
```

```
Salida (OUT):  [12]      ← 4 × 3 = 12
Instrucciones: 34
Estado final:  A=0x0C  B=0x01  PC=0x1C  Z=1  C=1
Memoria:       Mem[0xC8]=12 (resultado)  Mem[0xC9]=0 (contador agotado)
```

**Qué señalar:** el contador llegó a cero (`Mem[0xC9]=0`) y por eso el bucle terminó. La multiplicación se hizo por sumas repetidas, que es lo que permiten los saltos condicionales.

---

## Paso 4 — Ejecución paso a paso

```
python demo.py 4
```

```
─── Ciclo 7 ───
FETCH   PC=0x0C  →  IR=0x60 (ADD)
DECODE  Opcode 0110 | 1 byte | modo implícito
EXECUTE A=0x00 + B=0x04
        ALU: M=0 S=1001 Cn=1
RESULT  A=0x04   Z=0  C=0
PC → 0x0D
```

**Qué señalar — es el paso de más valor:**

- La línea `ALU: M=0 S=1001 Cn=1` es **la configuración exacta de pines** que el Arduino pondrá en el 74LS181 para sumar. Se puede contrastar con el multímetro en el circuito real.
- `Cn=1` para ADD parece contraintuitivo: el pin está **invertido** en modo active-high. Para `SUB` vale `0`, y ese nivel bajo es el *forced carry* que aporta el `+1` del complemento a 2.
- Cada llamada avanza **un microciclo**, no una instrucción. El bloque se imprime cuando la instrucción termina.

Para ver más ciclos, edita `ciclos=8` en `paso_4_paso_a_paso()` dentro de `demo.py`.

---

## Paso 5 — Las 6 funciones aprobadas

```
python demo.py 5
```

```
OP    OPERACIÓN        ESPERADO    OBTENIDO
---------------------------------------------
ADD   5 + 3             8 (0x08)     8 (0x08)  OK
SUB   5 - 3             2 (0x02)     2 (0x02)  OK
AND   0xCC & 0xAA     136 (0x88)   136 (0x88)  OK
OR    0xCC | 0xAA     238 (0xEE)   238 (0xEE)  OK
XOR   0xCC ^ 0xAA     102 (0x66)   102 (0x66)  OK
NOT   0x0F ^ 0xFF     240 (0xF0)   240 (0xF0)  OK
```

**Qué señalar:** las cinco operaciones de la ALU más `OUT`, que son exactamente las seis funciones que aprobó el ingeniero. La última fila suple la ausencia de una instrucción `NOT`: `XOR` contra `0xFF` da el complemento a 1, igual que en arquitecturas RISC reales que tampoco tienen `NOT` dedicada.

Fuente: `programas/demo_alu.asm`.

---

## Paso 6 — Datos elegidos en vivo ⭐

```
python demo.py 6
```

```
MULTIPLICACIÓN     LOAD equivalentes                  RESULTADO
----------------------------------------------------------------------
  4 × 3            LOAD 0xCC 0x04 / LOAD 0x05 0x03     12
  7 × 6            LOAD 0xCC 0x07 / LOAD 0x05 0x06     42
  9 × 9            LOAD 0xCC 0x09 / LOAD 0x05 0x09     81
 12 × 20           LOAD 0xCC 0x0C / LOAD 0x05 0x14    240
 16 × 16           LOAD 0xCC 0x10 / LOAD 0x05 0x10      0  ← desborda 8 bits
```

**Este es el paso que responde al requisito A.1** («el ingeniero elige en vivo qué datos ejecutar; el sistema debe ser genérico, no una demo pregrabada»).

Los dos operandos viven en direcciones fijas y conocidas:

| Operando | Dirección | Qué es |
|---|---|---|
| Multiplicador | `0x05` | El byte inmediato de la instrucción `LDI A,#n` |
| Multiplicando | `0xCC` | La constante declarada con `.DB` |

Cambiar la multiplicación son **dos comandos `LOAD`**, sin reensamblar y sin recompilar nada. En el hardware será literalmente teclear esas dos líneas en el monitor serial y escribir `RUN`.

El último caso es honesto a propósito: `16 × 16 = 256` no cabe en 8 bits, así que da `0` con el acarreo encendido. Conviene enseñarlo antes de que lo pregunten.

Fuente: `programas/demo_multiplicacion.asm` — los dos operandos están marcados con `<<<<` para editarlos también desde el fuente.

---

## Paso 7 — Detección de errores

```
python demo.py 7
```

```
3 errores detectados de una sola vez:
  línea 2: nemónico desconocido: 'LDX'
  línea 3: operando fuera de rango: 300 (válido 0–255)
  línea 4: instrucción de 1 byte con operando: 'ADD' no lleva operandos
```

**Qué señalar:** los errores se acumulan y se reportan juntos, no de uno en uno.

El fuente de prueba tiene **cuatro** errores, pero solo salen tres. Es deliberado y vale la pena explicarlo: el cuarto es una etiqueta indefinida, que solo se detecta en la **segunda pasada**, y el ensamblador aborta al terminar una fase con errores. Seguir adelante con un fuente roto produciría errores fantasma — un nemónico desconocido tiene longitud desconocida, así que todas las direcciones calculadas después serían basura. Al arreglar los tres primeros, el siguiente intento sí reporta el de la etiqueta.

---

## Paso 8 — Script de carga serial

```
python demo.py 8
```

```
  LOADB 0x00 0x30 0x00 0x50 0xC8 0x30 0x03 0x50 0xC9
  LOADB 0x08 0x10 0xC8 0x20 0xCC 0x60 0x50 0xC8 0x10
  LOADB 0x10 0xC9 0x40 0x01 0x70 0x50 0xC9 0xF0 0x08
  LOADB 0x18 0x10 0xC8 0xB0 0xC0
  LOADB 0xCC 0x04
```

**Qué señalar:** es el puente hacia el hardware. Estas cinco líneas se pegan tal cual en el monitor serial del Arduino.

El script es **disperso** — solo las direcciones realmente escritas, no los 256 bytes de la imagen completa — y va **en bloques de 8 bytes**: ninguna línea pasa de 50 caracteres, holgadamente por debajo del buffer de recepción de 64 bytes del Arduino. La última línea carga la constante en `0xCC`, que es la precondición que exige A.7.

---

## Demostración con el hardware (cuando B.3 exista)

La secuencia de arriba es íntegramente software. Con el circuito montado, el guion se amplía:

```
1. python -m asm programas/demo_multiplicacion.asm --run
   → anota el resultado que da el simulador

2. Abre programas/demo_multiplicacion.load
3. Pega esas líneas en el monitor serial
4. Escribe RUN

5. Los 8 dígitos deben mostrar EL MISMO número, en binario
```

Y para los datos en vivo, sin reensamblar:

```
6. El ingeniero dice un número, por ejemplo 9 × 7
7. LOAD 0xCC 0x09      ← multiplicando
8. LOAD 0x05 0x07      ← multiplicador
9. RUN
10. El display muestra 63 en binario: 0 0 1 1 1 1 1 1
```

**Si el hardware y el simulador discrepan, el hardware está mal.** Ese es el propósito de haber construido B.1 primero.

---

# B.3 — Firmware del Arduino

Es la unidad de control real: convierte los bytes que produce B.2 en señales sobre el 74LS181 físico. **El Arduino Mega todavía no se ha comprado**, así que el firmware está escrito y verificado en la PC, pero aún no probado en hardware.

## Estructura

```
firmware/
  microprocesador/          ← la carpeta del sketch (esto sube al Arduino)
    microprocesador.ino     setup() / loop(), delgado
    isa.h / isa.cpp         opcodes y constantes de ALU (espeja sim/isa.py)
    pines.h                 asignación de pines y tablas de cableado
    hal.h                   interfaz de E/S — la frontera
    hal_arduino.cpp         implementación real (puertos del Mega)
    nucleo.h / nucleo.cpp   fetch-decode-execute. No toca ni un pin
    formato.h / formato.cpp bloque A.9 + líneas clave=valor
    consola.h / consola.cpp protocolo serial
    display.h / display.cpp salida binaria: cuenta 0..7 y pulsa el reloj
  pruebas/                  ← NO sube al Arduino, solo verifica
    hal_falso.*             emula el 74LS181, los 74LS273 y el 74LS157
    arnes.cpp               ejecuta el núcleo en la PC
    prueba_alu.cpp          barrido exhaustivo de la ALU
    stub_arduino/           Arduino.h mínimo, para comprobar que compila
```

## Por qué está partido así

El ciclo fetch–decode–execute vive en `nucleo.cpp`, que **no toca ni un pin**: toda la E/S pasa por `hal.h`. Hay dos implementaciones de esa interfaz y solo una se enlaza en cada build:

| Build | HAL | Para qué |
|---|---|---|
| Sketch de Arduino | `hal_arduino.cpp` | Puertos reales del Mega |
| Pruebas en la PC | `pruebas/hal_falso.cpp` | Emula los tres integrados |

Así el **mismo código de control** corre en la placa y en la PC, y se puede contrastar contra el simulador antes de tener el circuito.

## Verificarlo sin hardware

```
python -m pytest -k firmware -v
```

Compila el firmware con `g++` y lo ejecuta contra el circuito emulado. Cinco archivos de prueba:

| Prueba | Qué comprueba |
|---|---|
| `test_firmware_isa.py` | Que `isa.h` coincide con `sim/isa.py` |
| `test_firmware_alu.py` | El 181 emulado contra `sim/alu.py`, los 65536 pares |
| `test_firmware_nucleo.py` | **Lockstep** contra el simulador, instrucción por instrucción |
| `test_firmware_microciclos.py` | 5/3/4 pasos por forma, igual que B.1 |
| `test_firmware_formato.py` | El bloque A.9 byte a byte contra `sim/trace.py` |
| `test_firmware_sketch.py` | Que el sketch entero compila y respeta las reglas del diseño |

### La emulación no es decorado

`hal_falso.cpp` decide qué operación hacer **leyendo las líneas M / S3–S0 / C̄n que el núcleo puso**, no el nemónico de la instrucción. Si el núcleo configurara `S=0110` con `M=1` creyendo que resta, saldría un XOR y la prueba fallaría.

Eso caza justo lo que de otro modo solo aparecería con el circuito soldado: la confusión SUB/XOR (comparten `S=0110`), el C̄n invertido, un pulso de reloj en el registro equivocado.

**Lo que NO puede cazar:** errores de cableado, tiempos reales, chips defectuosos, ruido de alimentación. Por eso la caracterización de la ALU en protoboard sigue siendo obligatoria.

## Cableado

La tabla completa está en `firmware/microprocesador/pines.h`, comentada señal por señal.

> ⚠️ **El aviso que más importa.** En el Mega, **PORTA asciende** con el número de pin, pero **PORTC y PORTL DESCIENDEN**. Cablear F0 al pin 30 daría el bit 7 en vez del bit 0, y el procesador entregaría resultados con los bits invertidos **sin ningún síntoma evidente**.

| Grupo | Pines | Señales |
|---|---|---|
| PORTA (asc.) | 22 → 29 | Bus de datos D0 → D7 |
| PORTC (**desc.**) | 37 → 30 | Lectura de F0 → F7 |
| PORTL bits 0–5 (**desc.**) | 49 → 44 | S0, S1, S2, S3, M, C̄n |
| Sueltos | 41, 40, 39, 38, 2 | CLK A, CLK B, MUX, CLEAR, C̄n+4 |
| Salida | 3, 4, 5, 6, 7 | SEL0, SEL1, SEL2 (74LS151 + 74LS138), BLANK (E3 del 138), CLK del registro de salida |

Total: 32 pines de los 54 del Mega.

## La salida es binaria y la dibuja el hardware

El Arduino **no decodifica** el resultado. El byte va del bus F a un tercer 74LS273 (registro de salida) y de ahí al 74LS151, que entrega el bit seleccionado (`Y`) y su complemento (`W`). Con esas dos señales se dibuja "0" o "1" en cada dígito:

| Segmentos | Encienden | Se conectan a |
|---|---|---|
| b, c | siempre | nivel fijo de "encendido" |
| a, d, e, f | si el bit es 0 | `W` del 74LS151 (a través del buffer) |
| g | si el bit es 1 | `Y` del 74LS151 (a través del buffer) |

El 74LS138 recibe **las mismas** tres líneas de selección y enciende el dígito correspondiente. El Arduino solo cuenta 0..7 y pulsa el reloj del registro de salida cuando ejecuta `OUT`.

## ⚠️ El display necesita transistores

**No conectes los comunes del display directo a los pines del Arduino ni a las salidas del 74LS138.**

Al multiplexar, el común de un dígito conduce la corriente de todos sus segmentos encendidos (hasta 6, el patrón "0"): unos **82 mA** con resistencias de 220 Ω. El máximo **absoluto** de un pin del Arduino son 40 mA y una salida del 74LS138 hunde 8 mA. Conectarlo directo lo quema, o lo degrada de forma intermitente — que es peor, porque entonces el síntoma parece un fallo de lógica.

Son **ocho** transistores, uno por dígito, con la base al 74LS138:

| Si el display es | Transistor | Base | Buffer de segmento |
|---|---|---|---|
| Ánodo común | 2N3906 (PNP) | 1 kΩ a la salida del 74LS138 | 74LS240 (inversor) |
| Cátodo común | 2N2222 (NPN) | 1 kΩ a la salida del 74LS138 | 74LS244 (directo) |

Las 7 resistencias de segmento (220–330 Ω) van en las líneas compartidas, **una por segmento, no una por dígito**. Con 8 dígitos cada uno enciende 1/8 del tiempo: si se ve tenue, usa 220 Ω.

## Antes de subirlo a la placa

| Pendiente | Dónde | Qué cambiar |
|---|---|---|
| ¿Display de ánodo o cátodo común? | **Hardware, no firmware** | 74LS240 + PNP si es ánodo común; 74LS244 + NPN si es cátodo. El código no cambia |
| ¿Carry en SUB? | `isa.h` | `#define CARRY_SUB_INVERTIDO 0` → `1` si la prueba lo contradice |

El segundo depende de **ejecutar primero la caracterización de la ALU** (sección 7 de la bitácora) con un 181 aislado en protoboard. No subas el firmware antes de haberla hecho.

## Subirlo

1. Abrir `firmware/microprocesador/microprocesador.ino` en el IDE de Arduino.
2. Herramientas → Placa → **Arduino Mega or Mega 2560**.
3. Seleccionar el puerto.
4. Subir.
5. Monitor Serie a **115200 baudios**, con final de línea **Nueva línea**.

El IDE compila todo lo que hay en la carpeta del sketch. `firmware/pruebas/` está fuera a propósito para que no intente subir el arnés.

## Comandos del monitor serial

| Comando | Función |
|---|---|
| `LOAD <dir> <byte>` | Escribe un byte. Responde `OK dir=0xCC val=0x04` |
| `LOADB <dir> <hex...>` | Carga varios bytes en una línea |
| `RUN` | Ejecuta hasta `HLT` |
| `STEP` | Avanza **un microciclo** |
| `RESET` | PC=0, banderas a 0. **Conserva la memoria** |
| `BORRAR` | Borra toda la memoria |
| `DUMP <ini> [fin]` | Vuelca memoria en filas de 16 |
| `STATE` | Estado actual |
| `VEL <ms>` | Retardo entre instrucciones en `RUN` |
| `HELP` | Lista los comandos |

Cada `LOAD` y cada `LOADB` confirma. No es adorno: el buffer de recepción del Arduino son **64 bytes**, así que un pegado largo podría perder comandos **en silencio**. Si ves menos confirmaciones que líneas enviadas, faltan bytes.

Por eso el archivo `.load` usa `LOADB` con 8 bytes por línea: 5 líneas de 50 caracteres para el programa de referencia, en vez de 29 líneas sueltas.

## Cargar un programa en el hardware

```
1. python -m asm programas/referencia.asm
2. Abrir programas/referencia.load
3. Pegar sus 5 líneas en el Monitor Serie
4. Comprobar que salieron 5 respuestas "OK dir=... n=..."
5. STATE      ← verificar PC=0x00
6. RUN
```

El display debe mostrar `0 0 0 0 1 1 0 0` — 12 en binario, bit 7 a la izquierda.

## Salida por duplicado

Cada instrucción produce dos cosas:

```
─── Ciclo 7 ───
FETCH   PC=0x0C  →  IR=0x60 (ADD)
DECODE  Opcode 0110 | 1 byte | modo implícito
EXECUTE A=0x00 + B=0x04
        ALU: M=0 S=1001 Cn=1
RESULT  A=0x04   Z=0  C=0
PC → 0x0D
#ciclo=7 pc=0x0D ir=0x60 op=ADD a=0x04 b=0x04 z=0 c=0 halted=0
```

El bloque es **idéntico byte a byte** al que produce el simulador — hay un test que lo verifica — así que los volcados de ambos se pueden comparar directamente al depurar.

La línea `#clave=valor` es **ASCII puro** y es la que parseará Processing. El prefijo `#` deja filtrarla sin confundirla con el texto bonito.

## Un detalle que conviene saber explicar

El Arduino **no puede leer los registros A y B**: las salidas de los 74LS273 van al 181, no al Arduino. Para `STA`, `OUT` y el volcado de estado, el firmware hace pasar el registro por la ALU sin alterarlo (`F=A` con M=1, S=1111) y lee el bus F.

Es decir: **el display muestra lo que de verdad hay en el registro físico**, no una copia que el Arduino guarde aparte. Si una soldadura fría corrompe el registro, se ve al instante. Y el byte llega al display por el mismo camino físico: del bus F al registro de salida, sin entrar nunca al Arduino.

---

# Flujo de trabajo completo

## Escribir y probar un programa nuevo

```
1. Escribe programas/mi_programa.asm
2. python -m asm programas/mi_programa.asm --run
3. ¿Da el resultado esperado?  → sigue
   ¿No?                        → depura con el modo STEP del simulador
4. Abre programas/mi_programa.load
5. Pega esas líneas en el monitor serial del Arduino  (cuando B.3 exista)
6. Escribe RUN en el monitor serial
7. El display de 7 segmentos debe mostrar lo mismo que el simulador
```

**Si el hardware y el simulador discrepan, el hardware está mal.** Ese es el propósito de B.1.

## Programas ya incluidos

| Archivo | Qué es |
|---|---|
| `programas/referencia.asm` | El programa canónico de A.7 (multiplicación 4×3), copia fiel del documento |
| `programas/referencia_etiquetas.asm` | El mismo, escrito con etiquetas de datos |
| `programas/demo_alu.asm` | Las 6 funciones aprobadas, cada una con su `OUT` |
| `programas/demo_multiplicacion.asm` | Multiplicación genérica, con los operandos marcados para cambiarlos en vivo |

Los dos primeros ensamblan a **bytes idénticos** — hay un test que lo verifica. Demuestra que las etiquetas son azúcar sintáctico puro, resuelto en la primera pasada.

Salidas esperadas:

| Programa | Salida |
|---|---|
| `referencia.asm` | `[12]` |
| `referencia_etiquetas.asm` | `[12]` |
| `demo_alu.asm` | `[8, 2, 136, 238, 102, 240]` |
| `demo_multiplicacion.asm` | `[12]` con los valores por defecto |

## Ejecutar las pruebas

```
python -m pytest -q                                  # todo (265)
python -m pytest tests/test_asm_errors.py -v         # un archivo, detallado
python -m pytest -k "reference" -v                   # por nombre
```

| Archivo de prueba | Qué cubre |
|---|---|
| `test_alu.py`, `test_cpu_instructions.py` | Las 9 operaciones de la tabla de aceptación de B.1 |
| `test_flags_isolation.py` | La regla crítica: solo la ALU toca Z y C |
| `test_step_mode.py`, `test_run_mode.py` | Microciclos, límite de ciclos |
| `test_reference_program.py` | A.7 en el simulador → 12 |
| `test_asm_mnemonics.py` | **Guardián**: que `asm/` no duplique la tabla de opcodes |
| `test_asm_errors.py` | Las 11 categorías de error |
| `test_asm_reference_program.py` | A.7 ensamblado → ejecutado → 12 |

---

# Notas de diseño relevantes al usar el software

## Una sola tabla de opcodes

`asm/mnemonics.py` **invierte** `sim/isa.py::OPCODE_TABLE`. Es el único archivo de `asm/` que importa `sim.isa`, y no contiene ni un literal de opcode.

Consecuencia práctica: **ensamblador y simulador no pueden desincronizarse.** Si alguna vez hubiera que cambiar el ISA (no debería: Parte A es inmutable), se toca `sim/isa.py` y ambos se enteran. `tests/test_asm_mnemonics.py` vigila que nadie codifique una segunda tabla.

## El binario se basta solo

`assemble()` siempre devuelve 256 bytes: el programa, los datos declarados con `.DB`, y ceros en el resto. Cargarlo en una `Memory()` recién creada reproduce el estado exacto de arranque. No hay que escribir constantes a mano después.

## Codificación de archivos en Windows

Todos los archivos de texto se leen y escriben con **UTF-8 explícito**, y el CLI reconfigura la consola a UTF-8 al arrancar. El valor por defecto de Windows es cp1252 y tanto los fuentes como los listados llevan acentos. Si editas un `.asm` con un editor externo, **guárdalo en UTF-8**.

---

# Qué falta (B.3 en adelante)

| Tarea | Estado |
|---|---|
| B.0 mapa de memoria | ✅ Congelado |
| B.1 simulador | ✅ 54 pruebas en verde |
| B.2 ensamblador | ✅ 211 pruebas en verde |
| B.3 firmware del Arduino | ✅ 193 pruebas en verde — **sin probar en hardware** |
| B.4 documentación | 🔄 En paralelo |

**Total: 458 pruebas.**

## Lo que bloquea el avance

| Bloqueo | Consecuencia |
|---|---|
| **Comprar el Arduino Mega**, los 74LS273, los 74LS157 y los displays | Sin la placa no hay nada que probar en hardware |
| **Caracterizar la ALU en protoboard** (sección 7 de la bitácora) | Resuelve el pendiente C.5 del carry en `SUB` |
| **¿Ánodo o cátodo común?** (pendiente C.4) | Depende de qué displays se compren |
| **¿PCB fabricado o placa perforada?** | Pregunta abierta al ingeniero; define el cronograma de las semanas 9–11 |

Los dos primeros pendientes ya están aislados en el firmware tras un `#define` cada uno, así que resolverlos es un cambio de una línea.

**Siguiente tarea de software:** la interfaz de observación en Processing — pero es lo **último** que debe construirse (semanas 12–13). Llegar a la semana 12 con una interfaz preciosa y un circuito a medio soldar es el peor escenario posible.
