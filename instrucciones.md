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
├── pytest.ini, requirements.txt, LICENSE
├── sim/          ← B.1: simulador del procesador
├── asm/          ← B.2: ensamblador de dos pasadas
├── firmware/     ← B.3: código del Arduino y sketches de prueba del montaje
├── depurador/    ← depurador gráfico Tkinter (ver depurador/LEEME.md)
├── montaje/      ← netlist, planos, guías por fase y bitácora del montaje físico
├── compañero/    ← sketch de un compañero, externo a este diseño
├── programas/    ← programas fuente .asm y sus salidas (+ diagnostico/)
└── tests/        ← 802 pruebas (sim 54, asm 265, firmware 189, depurador 270, montaje 24)
```

**¿Con prisa?** Salta a la [secuencia de demostración](#secuencia-de-demostración): `python demo.py` recorre todo lo construido en ocho pasos.

### Comprobación rápida de que todo funciona

```
python -m pytest -q
```

Debe terminar sin fallos (`802 passed` a 2026-10-01). Si algo falla, no sigas: el resto de este documento asume una suite verde.

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
memoria.load_bytes([0x30, 0x05,   # MOV A,5
                    0x40, 0x07,   # MOV B,7
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
EXECUTE | instrucción completada: True     ← aquí terminó MOV A,5
FETCH   | instrucción completada: False
...
```

### Cuántos microciclos consume cada instrucción

| Forma | Instrucciones | Pasos |
|---|---|---|
| ALU, 1 byte | ADD, SUB, AND, OR, XOR | **5** — FETCH, DECODE, EXECUTE, WAIT, WRITE |
| Control/salida, 1 byte | NOP, HLT, OUT | **3** — FETCH, DECODE, EXECUTE |
| 2 bytes | los cinco `MOV`, JMP, JZ, JNZ | **4** — FETCH, DECODE, FETCH2, EXECUTE |

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

> ✅ La semántica del carry en SUB quedó **confirmada en el hardware** (Parte C, punto 5, resuelto el 2026-09-29): con los dos 74LS181 en protoboard, C̄n+4 salió en bajo para 5−3 y 5−5 y en alto para 3−5, tal como asume el simulador (bitácora del montaje, fase 2).

## Regla crítica de banderas

**Solo las cinco operaciones de ALU (ADD, SUB, AND, OR, XOR) modifican Z y C.** Los `MOV` (cargas y guardado), los saltos, `NOP`, `OUT` y `HLT` las dejan intactas.

Esto es indispensable: el programa de referencia hace `SUB` → `MOV [201],A` → `JNZ`, y si ese `MOV` borrara la bandera el bucle nunca terminaría. En el código está garantizado por estructura — solo la rama de ALU de `cpu.py` asigna `self.z` / `self.c`.

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

      MOV A,0          ; inmediato: valor suelto, sin #
      MOV [200],A      ; directo: dirección, sin #
LOOP: MOV A,[200]      ; etiqueta seguida de dos puntos
      MOV B,[CUATRO]   ; una etiqueta también sirve como dirección de dato
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
| Espaciado | Libre. `MOV A,12`, `MOV A , 12` y `MOV A,[ 200 ]` son válidos |
| Comas | Opcionales entre operandos (`MOV A 5` equivale a `MOV A,5`) |
| Nombres reservados | Una etiqueta no puede llamarse como un mnemónico (`MOV:`) ni como un registro (`A:`): es error |

### Bases numéricas

| Base | Formatos | Ejemplo |
|---|---|---|
| Decimal | `12` | `MOV A,[200]` |
| Hexadecimal | `0xFF` o `$FF` | `MOV A,0xFF` |
| Binario | `0b1010` | `MOV B,0b1010` |

Rango válido: **0 a 255**. Fuera de ahí es error.

### `MOV` estilo x86: los operandos eligen el opcode

Desde 2026-09-28 las cinco transferencias usan la sintaxis del 8086: una sola palabra, `MOV destino,origen`, y el **modo de direccionamiento se lee en el operando**. Corchetes = dirección de memoria; valor pelado = dato inmediato. No se usa `#`.

| Forma | Opcode | Modo | Operación | Ejemplo |
|---|---|---|---|---|
| `MOV A,[dir]` | `0001` | Directo | Mem[dir] → A | `MOV A,[200]`, `MOV A,[DATO]` |
| `MOV B,[dir]` | `0010` | Directo | Mem[dir] → B | `MOV B,[0xCC]` |
| `MOV A,inm` | `0011` | Inmediato | n → A | `MOV A,12` |
| `MOV B,inm` | `0100` | Inmediato | n → B | `MOV B,0xFF` |
| `MOV [dir],A` | `0101` | Directo | A → Mem[dir] | `MOV [200],A` |

| Modo | Instrucciones | Operando |
|---|---|---|
| Directo | los `MOV` con `[ ]` | la dirección va **entre corchetes** |
| Salto | `JMP`, `JZ`, `JNZ` | dirección o etiqueta **sin** corchetes (`JNZ LOOP`) |
| Implícito | `ADD`, `SUB`, `AND`, `OR`, `XOR`, `OUT` | Sin operando |
| Sin operando | `NOP`, `HLT` | Sin operando |

`MOV A,[5]` y `MOV A,5` son **instrucciones distintas** (leer la celda 5 vs cargar el número 5): los corchetes son lo único que las separa, igual que en x86.

> ⚠️ Solo existen esas cinco formas. `MOV [200],B` (no hay "guardar B"), `MOV A,B` (no hay registro a registro), `MOV [200],5` o memoria a memoria son error; el mensaje lista las formas válidas. `#5` también es error, con una pista de cómo escribirlo ahora.

### Directivas

**`.ORG <dirección>`** — mueve el puntero de ensamblado. No emite bytes.

```asm
.ORG 0xC0       ; a partir de aquí se ensambla en la zona de datos
```

Solo admite un literal numérico (no etiquetas, para evitar definiciones circulares). No puede llevar etiqueta delante.

> Nota fechada 2026-09-28: antes de esa fecha el ISA usaba mnemónicos `LDA`/`LDB`/`LDI`/`STA` con `#` para el inmediato. Opcodes y bytes **no cambiaron**; solo la sintaxis del fuente. Los documentos anteriores a esa fecha que mencionan `LDA`, `LDB`, `LDI`, `STA` o `#n` son históricos.

**`.DB <valor>[, <valor>...]`** — emite bytes en la dirección actual.

```asm
.ORG 200
RESULTADO: .DB 0        ; una variable
TABLA:     .DB 1, 2, 3, 0xFF
```

`.DB` también acepta etiquetas como valor (se resuelven en la segunda pasada).

### Etiquetas para saltos y para datos

Una sola tabla de símbolos sirve para ambas cosas:

```asm
LOOP: MOV A,[CONTADOR]  ; CONTADOR es una dirección de dato
      JNZ LOOP          ; LOOP es un destino de salto

.ORG 201
CONTADOR: .DB 3
```

Las **referencias hacia adelante funcionan** — usar una etiqueta antes de definirla es precisamente para lo que existen las dos pasadas.

## Uso desde Python

```python
from asm import assemble

resultado = assemble("""
    MOV A,5
    MOV B,7
    ADD
    OUT
    HLT
""")

print(list(resultado.binary[:7]))   # [48, 5, 64, 7, 96, 176, 192]
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
    assemble("LDX 5\nMOV A,[300]\n")
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
| Operando fuera de rango | `MOV A,[256]`, `MOV A,[-1]` |
| Instrucción de 2 bytes sin operando | `MOV` o `JMP` solos |
| Instrucción de 1 byte con operando | `ADD 5` |
| Excede la zona de programa | Instrucción por encima de `0xBF` |
| Forma de operando incorrecta | `MOV [200],B`, `MOV A,B`, `MOV A,#5`, `JMP [10]`, `MOV A,[A]` (el mensaje lista las formas válidas) |
| Etiqueta con nombre reservado | `MOV:` (mnemónico) o `A:` (registro) |
| `.ORG` mal usado | `.ORG LOOP` (no admite etiquetas) o `X: .ORG 5` (no admite etiqueta delante) |
| Literal mal formado | `MOV A,[0xZZ]` |
| Desborde de memoria | Pasarse de `0xFF` |
| Solape | Dos sentencias escriben la misma dirección |

Ejemplo de salida:

```
2 errores de ensamblado
línea 1: nemónico desconocido: 'LDX'
    LDX 5
línea 2: operando fuera de rango: 300 (válido 0–255)
    MOV A,[300]
```

## Advertencias (no detienen el ensamblado)

- **`.DB` en la zona de programa** (por debajo de `0xC0`) — legal, pero probablemente no es lo que querías.
- **Nada emitido en `0x00`** — la ejecución arranca ahí y encontrará `NOP`s.

## Formato del listado

Fragmento real de `python -m asm programas/referencia.asm --listing-only` (las líneas de solo comentario o vacías salen sin dirección ni bytes):

```
DIR  BYTES        LÍN  FUENTE
---  -----------  ---  --------------------------------------------
00   30 00         12        MOV A,0
02   50 C8         13        MOV [200],A    ; resultado = 0
04   30 03         14        MOV A,3
06   50 C9         15        MOV [201],A    ; contador = 3

08   10 C8         17  LOOP: MOV A,[200]
...
CC   04            34        .DB 4          ; precondición de A.7

TABLA DE SÍMBOLOS
LOOP = 0x08 (8)
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

Debe terminar sin fallos (`802 passed`). Es lo primero que conviene enseñar: la suite completa en verde antes de tocar nada.

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
00   30 00         12        MOV A,0
02   50 C8         13        MOV [200],A    ; resultado = 0
04   30 03         14        MOV A,3
06   50 C9         15        MOV [201],A    ; contador = 3
                   16
08   10 C8         17  LOOP: MOV A,[200]
0A   20 CC         18        MOV B,[204]    ; el 4 vive en la dirección 204
0C   60            19        ADD
...
LOOP = 0x08 (8)
```

**Qué señalar:** cada instrucción con su dirección y sus bytes. Se ve que `ADD` ocupa 1 byte (`60`) y `MOV A,[200]` ocupa 2 (`10 C8`) — la longitud variable en acción. El nibble bajo del primer byte siempre es `0`, como manda el formato.

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
| Multiplicador | `0x05` | El byte inmediato de la instrucción `MOV A,n` |
| Multiplicando | `0xCC` | La constante declarada con `.DB` |

Cambiar la multiplicación son **dos comandos `LOAD`**, sin reensamblar y sin recompilar nada. En el hardware es literalmente teclear esas dos líneas en el monitor serial y escribir `RUN`.

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

## Demostración con el hardware

La secuencia de arriba es íntegramente software. Con el circuito montado (el programa de referencia ya corrió en la placa el 2026-10-01), el guion se amplía:

```
1. python -m asm programas/demo_multiplicacion.asm --run
   → anota el resultado que da el simulador

2. Abre programas/demo_multiplicacion.load
3. Pega esas líneas en el monitor serial
4. Escribe RUN

5. Los 8 LEDs deben mostrar EL MISMO número, en binario
```

Y para los datos en vivo, sin reensamblar:

```
6. El ingeniero dice un número, por ejemplo 9 × 7
7. LOAD 0xCC 0x09      ← multiplicando
8. LOAD 0x05 0x07      ← multiplicador
9. RUN
10. Los LEDs muestran 63 en binario: 0 0 1 1 1 1 1 1
```

**Si el hardware y el simulador discrepan, el hardware está mal.** Ese es el propósito de haber construido B.1 primero.

---

# B.3 — Firmware del Arduino

Es la unidad de control real: convierte los bytes que produce B.2 en señales sobre el 74LS181 físico. El Arduino Mega ya está comprado y conectado a las protoboards: `programas/referencia.load` corrió correctamente en el hardware el 2026-10-01, y desde el 2026-10-02 el procesador funciona completo (las 6 fases del montaje probadas). El firmware se desarrolla y verifica primero en la PC.

## Estructura

```
firmware/
  unidad_control/           ← la carpeta del sketch (esto sube al Arduino)
    unidad_control.ino      setup() / loop(), delgado
    isa.h / isa.cpp         opcodes y constantes de ALU (espeja sim/isa.py)
    pines.h                 asignación de pines y tablas de cableado
    hal.h                   interfaz de E/S — la frontera
    hal_arduino.cpp         implementación real (puertos del Mega)
    nucleo.h / nucleo.cpp   fetch-decode-execute. No toca ni un pin
    formato.h / formato.cpp bloque A.9 + líneas clave=valor
    consola.h / consola.cpp protocolo serial
    display.h / display.cpp salida: pulsa el reloj del registro de salida
  prueba_fase4/             ← sketch de banco (mux y PC con relojes limpios del Mega)
  prueba_fase5/             ← sketch de banco (cada línea Mega ↔ placa, comando T)
  diagnostico_display/      ← sketch de la salida de 7 segmentos anterior (obsoleto)
  pruebas/                  ← NO sube al Arduino, solo verifica
    hal_falso.*             emula el 74LS181, los 74LS273, el 74LS157 y los 74LS161 (PC)
    arnes.cpp               ejecuta el núcleo en la PC
    prueba_alu.cpp          barrido exhaustivo de la ALU
    stub_arduino/           Arduino.h mínimo, para comprobar que compila
```

## Por qué está partido así

El ciclo fetch–decode–execute vive en `nucleo.cpp`, que **no toca ni un pin**: toda la E/S pasa por `hal.h`. Hay dos implementaciones de esa interfaz y solo una se enlaza en cada build:

| Build | HAL | Para qué |
|---|---|---|
| Sketch de Arduino | `hal_arduino.cpp` | Puertos reales del Mega |
| Pruebas en la PC | `pruebas/hal_falso.cpp` | Emula los cuatro tipos de integrado (181, 273, 157, 161) |

Así el **mismo código de control** corre en la placa y en la PC, y se puede contrastar contra el simulador antes de tener el circuito.

## Verificarlo sin hardware

```
python -m pytest -k firmware -v
```

Compila el firmware con `g++` y lo ejecuta contra el circuito emulado. Seis archivos de prueba:

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

La tabla completa está en `firmware/unidad_control/pines.h`, comentada señal por señal.

> ⚠️ **El aviso que más importa.** En el Mega, **PORTA asciende** con el número de pin, pero **PORTC y PORTL DESCIENDEN**. Cablear F0 al pin 30 daría el bit 7 en vez del bit 0, y el procesador entregaría resultados con los bits invertidos **sin ningún síntoma evidente**.

| Grupo | Pines | Señales |
|---|---|---|
| PORTA (asc.) | 22 → 29 | Bus de datos D0 → D7 |
| PORTC (**desc.**) | 37 → 30 | Lectura de F0 → F7 |
| PORTL bits 0–5 (**desc.**) | 49 → 44 | S0, S1, S2, S3, M, C̄n |
| Sueltos | 41, 40, 39, 38, 2 | CLK A, CLK B, MUX, CLEAR, C̄n+4 |
| Salida | 7 | CLK del registro de salida (los pines 3–6 del antiguo display ya no se usan) |
| PC (2× 74LS161) | 42, 43 | CLK del PC y /LOAD del PC (activo en bajo) |
| PORTK (asc.) | A8 → A15 | Lectura del PC (Q0 → Q7 de los dos 161) |

Total: 38 pines de los 70 del Mega (los pines 3–6 del antiguo display están comentados en `pines.h`). Los bits 6 y 7 de PORTL quedan reservados (`MASCARA_NO_ALU 0xC0`).

## La salida son 8 LEDs, uno por bit

El Arduino **no toca** el resultado. El byte va del bus F a un tercer 74LS273 (registro de salida), que lo engancha cuando se ejecuta `OUT`, y de ahí a un buffer que da la corriente a los 8 LEDs. El diseño original usaba un 74LS244; el **montaje real usa un 74LS240** (2026-09-28, es el chip que se tiene en físico):

    montaje real:    bus F → 74LS273 (registro de salida) → 74LS240 → LED → 330 Ω → +5 V
    diseño con 244:  bus F → 74LS273 (registro de salida) → 74LS244 → 220 Ω → LED → GND

LED encendido = bit en 1, bit 7 a la izquierda. No hay decodificación: en binario el bit ya es la magnitud. El Arduino solo pulsa el reloj del registro de salida (pin 7). El 240 **invierte**, así que cada LED se cablea de +5 V a la salida del chip (+5 V → LED → 330 Ω → Y): el 240 hunde la corriente y el LED enciende con bit = 1. Sirve cualquier color de LED.

El 240 tiene el mismo pinout que el 244, así que la tabla vale para ambos:

| Bit | Q del 273 → buffer | buffer → resistencia → LED |
|---|---|---|
| 0 | pin 2 (1A1) | pin 18 (1Y1) |
| 1 | pin 4 (1A2) | pin 16 (1Y2) |
| 2 | pin 6 (1A3) | pin 14 (1Y3) |
| 3 | pin 8 (1A4) | pin 12 (1Y4) |
| 4 | pin 11 (2A1) | pin 9 (2Y1) |
| 5 | pin 13 (2A2) | pin 7 (2Y2) |
| 6 | pin 15 (2A3) | pin 5 (2Y3) |
| 7 | pin 17 (2A4) | pin 3 (2Y4) |

## ⚠️ Tres cosas que hacen que los LEDs no enciendan

1. **1G (pin 1) y 2G (pin 19) del buffer (240 o 244) van a GND.** Son habilitaciones activas en bajo: sueltas se leen como alto y las salidas quedan desconectadas.
2. **Sin el buffer no encienden.** El 273 solo entrega 0.4 mA en alto; el 244/240 manejan hasta 15 mA.
3. **Con un 74LS244 (no es el caso del montaje real), LEDs rojos, verdes o amarillos.** En alto el 244 da 2.4–3.4 V; a un LED azul o blanco (~3 V) no le queda corriente. Si se ven tenues, 150 Ω en lugar de 220 Ω. Con el 240 cableado desde +5 V no hay esa limitación.

Los pines 3–6 del Arduino (antes SEL0–SEL2 y BLANK del display) quedan **sin conectar**, y el firmware ya no los maneja (código comentado).

## Antes de subirlo a la placa

| Punto | Dónde | Estado |
|---|---|---|
| ¿Carry en SUB? | `isa.h` | ✅ Resuelto el 2026-09-29 (C.5): se midió el 181 en la fase 2 y coincide con el diseño; `#define CARRY_SUB_INVERTIDO 0` se queda en 0 |

Regla del montaje: **después de tocar la placa, sube `firmware/prueba_fase5/` y corre `T`** (debe responder TODO OK, idealmente dos veces seguidas) antes de cargar cualquier programa. Los sketches `prueba_fase4` y `prueba_fase5` están descritos en `montaje/bitacora_montaje.md`.

## Subirlo

1. Abrir `firmware/unidad_control/unidad_control.ino` en el IDE de Arduino.
2. Herramientas → Placa → **Arduino Mega or Mega 2560**.
3. Seleccionar el puerto.
4. Subir.
5. Monitor Serie a **115200 baudios**, con final de línea **Nueva línea**.

El IDE compila todo lo que hay en la carpeta del sketch. `firmware/pruebas/` está fuera a propósito para que no intente subir el arnés.

## Comandos del monitor serial

| Comando | Función |
|---|---|
| `LOAD <dir> <byte>` | Escribe un byte. Responde `OK dir=0xCC val=0x04` |
| `LOADB <dir> <hex...>` | Carga varios bytes en una línea. Responde `OK dir=0x.. n=N` (una confirmación **por línea**, no por byte) |
| `RUN` | Ejecuta hasta `HLT` (límite de 10000 instrucciones: `ERR limite de instrucciones; posible bucle infinito`) |
| `STEP` | Avanza **un microciclo**. Imprime `paso: <nombre>`; el bloque y `#paso=` salen al terminar la instrucción |
| `RESET` | PC=0, banderas a 0. **Conserva la memoria**. Responde `OK reset` y el estado |
| `BORRAR` | Borra toda la memoria. Responde `OK memoria borrada` |
| `DUMP [ini [fin]]` | Vuelca memoria en filas de 16 |
| `STATE` | Estado actual |
| `VEL <ms>` | Retardo entre instrucciones en `RUN`, 0–5000. Responde `OK vel=N` |
| `HELP` | Lista los comandos |

Cada línea termina en `\r` o `\n`. Errores típicos: `ERR comando desconocido: ...`, `ERR valor fuera de rango (0-255)`, `ERR byte invalido: ...`, `ERR el bloque excede la memoria`, `ERR la CPU esta detenida; usa RESET` y `linea demasiado larga` (más de 96 caracteres). Al arrancar, el firmware imprime un banner de 3 líneas.

Cada `LOAD` y cada `LOADB` confirma. No es adorno: el buffer de recepción del Arduino son **64 bytes**, así que un pegado largo podría perder comandos **en silencio**. Si ves menos confirmaciones que líneas enviadas, faltan bytes.

Por eso el archivo `.load` usa `LOADB` con 8 bytes por línea: 5 líneas de 50 caracteres para el programa de referencia, en vez de 29 líneas sueltas.

## Cargar un programa en el hardware

```
1. python -m asm programas/referencia.asm
2. Abrir programas/referencia.load
3. Pegar sus 5 líneas en el Monitor Serie (o cargar el `.load` con el depurador)
4. Comprobar que salieron 5 respuestas "OK dir=... n=..."
5. STATE      ← verificar PC=0x00
6. RUN
```

Los LEDs deben mostrar `0 0 0 0 1 1 0 0` — 12 en binario, bit 7 a la izquierda (encendidos solo los bits 3 y 2).

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

La línea `#clave=valor` es **ASCII puro** y es la que parsea el depurador Tkinter (y la que parsearía una interfaz en Processing). El prefijo `#` deja filtrarla sin confundirla con el texto bonito.

## Un detalle que conviene saber explicar

El Arduino **no puede leer los registros A y B**: las salidas de los 74LS273 van al 181, no al Arduino. Para `MOV [dir],A`, `OUT` y el volcado de estado, el firmware hace pasar el registro por la ALU sin alterarlo (`F=A` con M=0, S=0000, C̄n=1: A más 0 en modo aritmético) y lee el bus F.

Es decir: **los LEDs muestran lo que de verdad hay en el registro físico**, no una copia que el Arduino guarde aparte. Si una soldadura fría corrompe el registro, se ve al instante. Y el byte llega a los LEDs por el mismo camino físico: del bus F al registro de salida, sin entrar nunca al Arduino.

---

# Flujo de trabajo completo

## Escribir y probar un programa nuevo

```
1. Escribe programas/mi_programa.asm
2. python -m asm programas/mi_programa.asm --run
3. ¿Da el resultado esperado?  → sigue
   ¿No?                        → depura con el modo STEP del simulador
4. Abre programas/mi_programa.load
5. Pega esas líneas en el monitor serial del Arduino
6. Escribe RUN en el monitor serial
7. Los 8 LEDs deben mostrar lo mismo que el simulador
```

**Si el hardware y el simulador discrepan, el hardware está mal.** Ese es el propósito de B.1.

## Programas ya incluidos

| Archivo | Qué es |
|---|---|
| `programas/referencia.asm` | El programa canónico de A.7 (multiplicación 4×3), copia fiel del documento |
| `programas/referencia_etiquetas.asm` | El mismo, escrito con etiquetas de datos |
| `programas/demo_alu.asm` | Las 6 funciones aprobadas, cada una con su `OUT` |
| `programas/demo_multiplicacion.asm` | Multiplicación genérica, con los operandos marcados para cambiarlos en vivo |
| `programas/diagnostico/diag1_salida.asm` … `diag4_acarreo.asm` | Diagnóstico del cableado en la protoboard (ver abajo) |

Los dos primeros ensamblan a **bytes idénticos** — hay un test que lo verifica. Demuestra que las etiquetas son azúcar sintáctico puro, resuelto en la primera pasada.

Salidas esperadas:

| Programa | Salida |
|---|---|
| `referencia.asm` | `[12]` |
| `referencia_etiquetas.asm` | `[12]` |
| `demo_alu.asm` | `[8, 2, 136, 238, 102, 240]` |
| `demo_multiplicacion.asm` | `[12]` con los valores por defecto |
| `diagnostico/diag1_salida.asm` | `[85]` (LEDs 01010101: etapa de salida) |
| `diagnostico/diag2_bits_A.asm` | `[1, 2, 4, 8, 16, 32, 64, 128]` (un bit a la vez por A) |
| `diagnostico/diag3_bits_B.asm` | `[1, 2, 4, 8, 16, 32, 64, 128]` (un bit a la vez por B) |
| `diagnostico/diag4_acarreo.asm` | `[16]` (acarreo entre los dos 181; si sale 0 falla C̄n+4 → C̄n) |

## Ejecutar las pruebas

```
python -m pytest -q                                  # todo (802)
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
| `test_asm_errors.py` | Las 10 categorías de error |
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
| B.2 ensamblador | ✅ 265 pruebas en verde |
| B.3 firmware del Arduino | ✅ 189 pruebas en verde — `referencia.load` ya corrió en hardware (2026-10-01) |
| Depurador Tkinter | ✅ 270 pruebas en verde (entregado) |
| Montaje (`montaje/`) | ✅ 24 pruebas en verde; montaje físico completo, las 6 fases probadas (2026-10-02) |
| B.4 documentación | 🔄 En paralelo |

**Total: 802 pruebas** (sim 54, asm 265, firmware 189, depurador 270, montaje 24).

## Lo que bloquea el avance

| Bloqueo | Consecuencia |
|---|---|
| ~~Terminar el montaje físico y sus pruebas~~ | ✅ Hecho (2026-10-02): fases 5 y 6 completas |
| **¿La entrega en protoboard conserva la exoneración?** | El ingeniero ya aceptó la protoboard como entrega (C.1, 2026-09-17), lo que supera la duda A.1.5 de la exoneración; sin confirmar por escrito |

Ya resueltos: la compra del Arduino Mega y de los chips (el Mega ya corre el firmware) y el pendiente C.5 del carry en `SUB` (2026-09-29, `CARRY_SUB_INVERTIDO` queda en 0).

**Software de observación:** el depurador gráfico en Python/Tkinter ya está entregado (`depurador/`, ver `depurador/LEEME.md`; cierra C.6). Una interfaz en Processing queda solo como **extra opcional**.
