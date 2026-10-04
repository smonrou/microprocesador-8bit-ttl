# Ensamblar a mano — tabla de opcodes y cómo escribir un `.load` sin `python -m asm`

Hoja de referencia para traducir un programa a bytes con lápiz y papel y
cargarlo en la placa directamente por el monitor serial. Todo lo que hay aquí
sale del ISA congelado (`contexto_proyecto.md` A.4–A.6) y del firmware
(`firmware/microprocesador/consola.cpp`).

---

## 1. Tabla de opcodes

El opcode va en el **nibble alto** del primer byte; el nibble bajo es siempre `0`.
Las instrucciones de 2 bytes llevan el operando en el segundo byte.

| Hex (byte 1) | Binario | Instrucción | Bytes | Byte 2 | Operación | Toca Z/C |
|---|---|---|---|---|---|---|
| `00` | `0000 0000` | `NOP` | 1 | — | nada | No |
| `10` | `0001 0000` | `MOV A,[dir]` | 2 | dirección | Mem[dir] → A | No |
| `20` | `0010 0000` | `MOV B,[dir]` | 2 | dirección | Mem[dir] → B | No |
| `30` | `0011 0000` | `MOV A,n` | 2 | valor | n → A | No |
| `40` | `0100 0000` | `MOV B,n` | 2 | valor | n → B | No |
| `50` | `0101 0000` | `MOV [dir],A` | 2 | dirección | A → Mem[dir] | No |
| `60` | `0110 0000` | `ADD` | 1 | — | A + B → A | **Sí** |
| `70` | `0111 0000` | `SUB` | 1 | — | A − B → A | **Sí** |
| `80` | `1000 0000` | `AND` | 1 | — | A & B → A | **Sí** |
| `90` | `1001 0000` | `OR` | 1 | — | A \| B → A | **Sí** |
| `A0` | `1010 0000` | `XOR` | 1 | — | A ⊕ B → A | **Sí** |
| `B0` | `1011 0000` | `OUT` | 1 | — | A → LEDs | No |
| `C0` | `1100 0000` | `HLT` | 1 | — | detiene la CPU | No |
| `D0` | `1101 0000` | `JMP dir` | 2 | dirección | dir → PC | No |
| `E0` | `1110 0000` | `JZ dir` | 2 | dirección | si Z=1: dir → PC | No |
| `F0` | `1111 0000` | `JNZ dir` | 2 | dirección | si Z=0: dir → PC | No |

Ejemplos: `MOV A,5` = `30 05` · `MOV B,[0xC1]` = `20 C1` · `ADD` = `60` ·
`JNZ 0x08` = `F0 08`. **Una instrucción da siempre los mismos bytes**, esté donde
esté; lo único que varía es el byte 2 cuando es una dirección que tú elegiste.

### Lo que NO existe

No hay `MOV [dir],B`, ni `MOV A,B`, ni memoria a memoria, ni salto por acarreo
(`JC`). Para guardar B: pásalo por A con la ALU (por ejemplo `MOV A,0` + `ADD`
deja A = B).

---

## 2. Banderas

- **Z = 1** si el resultado de la última operación de ALU fue `0x00`.
- **C** — en `ADD`: 1 si hubo acarreo (resultado > 255). En `SUB`: 1 si **no**
  hubo préstamo (A ≥ B sin signo). En `AND`/`OR`/`XOR`: siempre 0.
- **Solo `ADD SUB AND OR XOR` cambian las banderas.** Los `MOV`, `OUT` y saltos
  las dejan como estaban. Por eso es válido `SUB` → `MOV [dir],A` → `JNZ`: el
  guardado no borra Z.

Trucos de comparación:

| Quiero saber… | Hago | Salto |
|---|---|---|
| ¿A == B? | `XOR` (o `SUB`) | `JZ` iguales / `JNZ` distintos |
| ¿A == 0? | `MOV B,0` + `OR` | `JZ` |
| ¿bit k de A encendido? | `MOV B,máscara` + `AND` | `JNZ` encendido |

`XOR` y `SUB` **destruyen A** (el resultado se guarda en A). Si necesitas el
valor original, guárdalo antes con `MOV [dir],A`.

---

## 3. Mapa de memoria

| Rango | Uso |
|---|---|
| `0x00`–`0xBF` | Programa. La CPU **siempre arranca en `0x00`**. |
| `0xC0`–`0xFF` | Datos (variables y constantes). |

Toda la memoria vale `0x00` tras `BORRAR`, y `0x00` es `NOP`.

---

## 4. Método paso a paso

### Paso 1 — Escribe el programa en nemónicos

Pon etiquetas donde vayas a saltar (`INICIO:`) y nombres a las variables (`N`).

### Paso 2 — Asigna direcciones (primera pasada)

Empieza en `0x00` y suma el tamaño de cada instrucción: **2 bytes** las que
llevan operando (`MOV`, `JMP`, `JZ`, `JNZ`), **1 byte** el resto. Apunta en qué
dirección cae cada etiqueta. Decide en qué dirección de `0xC0`–`0xFF` vive cada
variable.

### Paso 3 — Traduce a bytes (segunda pasada)

Byte 1 de la tabla de la sección 1. Byte 2: el número, o la dirección que
apuntaste para la etiqueta/variable.

### Paso 4 — Escribe las líneas `LOADB`

```
LOADB <dirección inicial> <byte> <byte> <byte> ...
```

Los bytes se escriben en direcciones **consecutivas** a partir de la inicial.
Un bloque nuevo cada vez que haya un hueco (por ejemplo, el código en `0x00` y
los datos en `0xC0` van en líneas distintas).

### Paso 5 — Carga y ejecuta

```
BORRAR
LOADB ...
LOADB ...
RESET
RUN
```

---

## 5. Ejemplo completo — cuenta regresiva 3, 2, 1

### Pasos 1 y 2: programa y direcciones

| Dir | Etiqueta | Instrucción | Tamaño |
|---|---|---|---|
| `00` | `INICIO:` | `MOV A,[N]` | 2 |
| `02` | | `OUT` | 1 |
| `03` | | `MOV B,1` | 2 |
| `05` | | `SUB` | 1 |
| `06` | | `MOV [N],A` | 2 |
| `08` | | `JNZ INICIO` | 2 |
| `0A` | | `HLT` | 1 |
| `C0` | `N:` | dato = 3 | 1 |

Etiquetas: `INICIO = 0x00`, `N = 0xC0`.

### Paso 3: bytes

| Dir | Instrucción | Bytes |
|---|---|---|
| `00` | `MOV A,[N]` | `10 C0` |
| `02` | `OUT` | `B0` |
| `03` | `MOV B,1` | `40 01` |
| `05` | `SUB` | `70` |
| `06` | `MOV [N],A` | `50 C0` |
| `08` | `JNZ INICIO` | `F0 00` |
| `0A` | `HLT` | `C0` |
| `C0` | `N` | `03` |

### Paso 4: el `.load`

```
LOADB 0x00 0x10 0xC0 0xB0 0x40 0x01 0x70 0x50 0xC0
LOADB 0x08 0xF0 0x00 0xC0
LOADB 0xC0 0x03
```

Salida en los LEDs: `3`, `2`, `1` y se detiene. (Verificado: el ensamblador
produce exactamente estos mismos bytes.)

---

## 6. Reglas del monitor serial (importantes)

1. **Una línea = un comando.** Debe responder `OK dir=0x.. n=N`. Cuenta los
   `OK`: si hay menos que líneas, se perdieron bytes (el buffer del Arduino es
   de 64 bytes). Vuelve a mandar las que faltan.
2. **Máximo 95 caracteres por línea** (si no: `ERR linea demasiado larga` y la
   línea se descarta entera). Con el formato `0xNN` caben unos 16 bytes por
   `LOADB`; usa 8 para ir sobrado.
3. **Números:** `0x1F` (hex) o `31` (decimal). Rango 0–255.
   ⚠️ **Nunca pongas ceros a la izquierda sin `0x`**: `010` se lee en *octal*
   (= 8) y `08` da `ERR byte invalido`. Escribe `0x08` o `8`.
4. **Sin comentarios** al pegar en el monitor serial: una línea que empiece
   por `;` da `ERR comando desconocido`. (El depurador Tkinter sí ignora las
   líneas que empiezan por `;` o `#`, así que en un archivo para el depurador
   puedes anotarlas.)
5. **`BORRAR` antes de cargar.** `LOADB` solo escribe las direcciones que
   mandas; los bytes del programa anterior siguen ahí y pueden ejecutarse.
6. Mayúsculas o minúsculas da igual en el comando (`loadb` = `LOADB`).
7. Para un solo byte también sirve `LOAD <dir> <byte>`
   (ej. `LOAD 0xC0 5` → cambia `N` en vivo).

### Comprobar lo que cargaste

- `DUMP 0x00 0x0F` — vuelca la memoria; compárala con tu tabla del paso 3.
- `STEP` — avanza un microciclo; `STATE` — muestra PC, IR, A, B, Z, C.
- `VEL 500` — medio segundo entre instrucciones en `RUN`, para ver los LEDs.

---

## 7. Errores típicos al ensamblar a mano

| Síntoma | Causa probable |
|---|---|
| El programa salta a un sitio raro | Contaste mal el tamaño de alguna instrucción: las de 2 bytes desplazan todo lo que viene después. |
| Lee basura en vez de tu variable | Olvidaste los corchetes: `MOV A,[0xC0]` es `10 C0`, `MOV A,0xC0` es `30 C0` (carga el número 192). |
| Bucle infinito (`ERR limite de instrucciones`) | El salto vuelve a una dirección que reinicia el contador, o la condición nunca da Z=1. |
| La CPU ejecuta "de más" al final | Falta `HLT` (`C0`); tras él venían restos de otro programa → usa `BORRAR`. |
| Insertaste una instrucción y todo falla | Al insertar, cambian las direcciones de las etiquetas posteriores: recalcula todos los saltos y `[dir]` que apunten a ellas. |

---

## 8. Plantilla para tus programas

| Dir | Etiqueta | Instrucción | Tamaño | Bytes |
|---|---|---|---|---|
| `00` | | | | |
| | | | | |
| | | | | |
| `C0` | | dato | 1 | |

Etiquetas: `______ = 0x__`, `______ = 0x__`

```
BORRAR
LOADB 0x00 ...
LOADB 0xC0 ...
RESET
RUN
```

> Si luego quieres comprobar tu trabajo, escribe el mismo programa en un `.asm`
> y compara tus bytes con su `.lst` — pero nada de esta hoja depende de él.
