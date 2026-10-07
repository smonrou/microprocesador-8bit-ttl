# Guion de explicación: carpeta `asm/`

> Ensamblador de dos pasadas para el microprocesador de 8 bits.
> Orden: de abajo hacia arriba, siguiendo las dependencias. Cada archivo solo usa piezas ya explicadas.

---

## 0. Introducción (≈1 min)

- "La carpeta `asm/` es el ensamblador. Toma un archivo `.asm` escrito por una persona y produce la imagen de memoria de 256 bytes que ejecuta el procesador."
- "No define la ISA. La lee de `sim/isa.py`, de la tabla `OPCODE_TABLE`. Esa tabla es la única fuente de verdad: 16 instrucciones, opcode de 4 bits, largo de 1 o 2 bytes y modo de direccionamiento."
- "Si mañana cambiara la ISA, el ensamblador se adapta solo, porque nada de los nemónicos está escrito a mano."
- "El ensamblado tiene tres fases: **análisis de líneas → pasada 1 → pasada 2**. Voy a ir de las piezas pequeñas hacia la grande."

Mapa rápido para mostrar en pantalla:

```
errors.py ─┬─> numbers.py ─┐
           │               ├─> parser.py ─> assembler.py ─> __main__.py
sim/isa.py ─> mnemonics.py ┘                    │
                                          listing.py
```

---

## 1. `errors.py`: cómo se reportan los problemas (≈2 min)

- "Todo error de ensamblado hereda de `AssemblerError`. Siempre lleva **número de línea** y **texto de la línea**, así el mensaje sale como `línea 7: nemónico desconocido`, con la línea original debajo."
- "Hay una subclase por categoría: nemónico desconocido, etiqueta no definida o duplicada, operando fuera de rango, cantidad o forma de operandos, literal mal formado, desborde de memoria, instrucción fuera de la zona de programa y solape de direcciones."
- Idea clave, el **`ErrorCollector`**:
  - "*Dentro* de una fase los errores se acumulan. Si hay cinco errores de tipeo, salen los cinco de una vez."
  - "*Entre* fases se aborta. Si un nemónico es desconocido, no sabemos si ocupa 1 o 2 bytes, y seguir a la pasada 1 daría errores de dirección fantasma."
- "Al final de cada fase, `raise_if_any()` lanza `AssemblyFailed`: un solo error que contiene la lista completa, ordenada por línea."

---

## 2. `numbers.py`: literales numéricos (≈1.5 min)

- "Acepta cuatro formatos: decimal (`200`), hexadecimal con `0x` (`0xC8`), hexadecimal con `$` (`$C8`) y binario (`0b1010`). Hay una regex por formato."
- "Todo valor tiene que caber en un byte sin signo: **0 a 255**."
- Detalle de diseño: "Un `-1` se lee bien como número y falla después en el control de rango. Así el error dice *operando fuera de rango*, que es lo que pide la especificación, y no *error de sintaxis*."
- "También define qué es un nombre de etiqueta válido: empieza con letra o `_`, y sigue con letras, dígitos o `_`."
- "`parse_and_check` junta los dos pasos: leer el literal y comprobar su rango."

---

## 3. `mnemonics.py`: de la ISA a los nemónicos (≈2 min)

- "Este archivo traduce la tabla de la ISA a algo que el parser pueda consultar. No escribe ningún nemónico a mano."
- "`REGISTERS` (A y B) y `MNEMONIC_TABLE` se construyen recorriendo `OPCODE_TABLE`."
- Concepto de **slots**, los huecos del patrón de operandos:
  - `[DIR]`: dirección entre corchetes, como en `MOV A,[200]`.
  - `INM`: valor sin corchetes, como en `MOV A,5`.
  - `DIR`: dirección sin corchetes, para saltos, como en `JNZ LOOP`.
  - Cualquier otro slot es el nombre literal de un registro.
- "`operand_pattern` obtiene esos slots del texto del nemónico. Si el texto no los trae (`JMP`, `ADD`), los deduce del modo de direccionamiento."
- "`FORMS_BY_BASE` agrupa las formas por palabra base. `MOV` tiene 5 formas distintas con 5 opcodes distintos. El programador escribe solo `MOV`, y el parser elige cuál de las cinco es."
- "Directivas: `.ORG` mueve el puntero de ensamblado y `.DB` escribe bytes de datos."

---

## 4. `parser.py`: de texto a `ParsedLine` (≈5 min, núcleo)

### 4.1 Estructuras de datos

- "`LineKind`: cada línea es vacía, instrucción o directiva. Una línea con solo una etiqueta cuenta como vacía."
- "`OperandForm`: cómo se escribió un operando: `NUMBER`, `LABEL`, `MEMORY_NUMBER`, `MEMORY_LABEL` o `REGISTER`."
- "`ParsedLine` guarda todo lo que hace falta de una línea: etiqueta, instrucción elegida (`spec`), directiva y operandos."
- "Su propiedad `size` dice cuántos bytes emite: 1 o 2 para instrucciones, uno por valor en `.DB` y 0 en lo demás. Es lo único que necesita la pasada 1."

### 4.2 Tokenización

- "Primero se quita el comentario (desde `;`). Después, una regex separa la línea en tokens."
- "Las comas quedan como tokens sueltos y lo que va entre corchetes es un solo token. Por eso `MOV A,[200]` y `MOV A , [ 200 ]` dan lo mismo."

### 4.3 `parse_operand`: clasificar un operando

Orden de las comprobaciones:
1. "Si empieza con `#`, es error. Es la sintaxis antigua, y el mensaje explica cómo escribirlo ahora."
2. "Si es `A` o `B`, es registro."
3. "Si tiene corchetes, es acceso a memoria y se trabaja con lo de adentro."
4. "Si es un número, se lee y se comprueba su rango en el momento."
5. "Si es una etiqueta, se guarda el nombre y se resuelve en la pasada 2. `[A]` se rechaza porque esta ISA no tiene direccionamiento indirecto por registro."
6. "Si no es nada de lo anterior, es un operando mal formado."

### 4.4 `select_form`: la pieza clave

- "Recibe la palabra base y los operandos escritos, y prueba cada forma posible de esa instrucción. Devuelve la única cuyo patrón de slots encaja."
- Ejemplo verbal: "`MOV A,[200]` da registro A y memoria-número. De las cinco formas de `MOV`, solo `MOV A,[dir]` encaja, así que el opcode es 0x1."
- "Si ninguna encaja, el resto de la función solo arma el mensaje de error más útil:"
  - "Error de **cantidad**: sobran o faltan operandos."
  - "Error de **forma**: la cantidad es correcta pero el tipo no, por ejemplo `MOV B,A`. El mensaje lista las formas válidas. En los saltos, el error típico es poner corchetes, y el mensaje lo indica."

### 4.5 `parse_line` y `parse_source`

- "`parse_line` sigue este orden: tokens, etiqueta opcional, directiva o instrucción, operandos."
- "Una etiqueta no puede llamarse como un nemónico ni como un registro, porque sería ambigua al usarla como operando. Las etiquetas no distinguen mayúsculas."
- "No se admite etiqueta en una línea `.ORG`, porque es ambiguo si vale lo de antes o lo de después del salto."
- "En una instrucción, los registros ya van codificados en el opcode, así que se descartan. Solo queda el operando que se convierte en el segundo byte."
- "`parse_source` recorre todas las líneas, acumula los errores con el `ErrorCollector` y aborta al final de la fase si hubo alguno. Esta es la **fase 1**."

---

## 5. `assembler.py`: las dos pasadas (≈5 min, núcleo)

### 5.1 Mapa de memoria

- "Programa en `0x00–0xBF` y datos en `0xC0–0xFF`. La ejecución siempre arranca en `0x00`."

### 5.2 Estructuras

- "`LayoutItem` es una línea con su dirección asignada. Es la salida de la pasada 1."
- "`ListingRow` es una fila del listado con los bytes emitidos. Es la salida de la pasada 2."
- "`AssemblyResult` es todo lo que devuelve `assemble()`: binario de 256 bytes, tabla de símbolos, filas, listado, scripts de carga, avisos y tramos escritos."

### 5.3 Pasada 1: `first_pass`

- "La idea central es un **puntero de ensamblado** que empieza en 0 y avanza según el tamaño de cada línea."
- "Una etiqueta vale lo que vale el puntero en la línea donde se define. Así se arma la **tabla de símbolos**."
- "`.ORG` cambia el puntero directamente."
- Controles de esta pasada:
  - "Etiqueta duplicada. El mensaje dice en qué línea se definió primero."
  - "Que la línea no pase de los 256 bytes."
  - "Que una *instrucción* no invada la zona de datos. Los `.DB` sí pueden ir en cualquier parte."
- "¿Por qué hacen falta dos pasadas? Por las referencias hacia adelante. `JNZ FIN` puede usar `FIN` antes de que esté definida, y en la pasada 1 todavía no se conoce su dirección."

### 5.4 Pasada 2: `second_pass`

- "Empieza con una imagen de 256 ceros, y `0x00` es `NOP`."
- "Codificación de una instrucción: el primer byte es `opcode << 4`, con los 4 bits altos para el opcode y los 4 bajos siempre en cero. Por ejemplo, `ADD` (0x6) se emite como `0x60`."
- "Si la instrucción es de 2 bytes, el segundo es el inmediato o la dirección. `_resolve` busca las etiquetas en la tabla de símbolos, y si no están, es *etiqueta no definida*."
- "`.DB` emite un byte por valor. Si el valor es una etiqueta, guarda su dirección como dato."
- "Detección de **solapes**: como `.ORG` permite que dos líneas apunten a la misma dirección, se registra quién escribió cada byte y un segundo intento da error."
- **Avisos**, que no son errores:
  - "Datos `.DB` dentro de la zona de programa. Está permitido porque es convención, no hardware."
  - "No se emitió nada en `0x00`. La CPU arrancaría ejecutando NOPs."
- "`_spans` resume qué tramos contiguos de memoria se escribieron."

### 5.5 `assemble()`: la API pública

- "Encadena las tres fases: `parse_source`, `first_pass` y `second_pass`. Cada una aborta si encuentra errores, así que si se llega al `return`, el resultado está completo y es válido."
- "Al final llama a `listing.py` para formatear la salida."

---

## 6. `listing.py`: formatos de salida (≈2 min)

- "Aquí no hay lógica de ensamblado, solo presentación."
- "`format_listing` produce el `.lst` con las columnas DIR, BYTES, LÍN y FUENTE. Un `.DB` largo continúa en varias filas de 4 bytes. Al final va la **tabla de símbolos**, ordenada por dirección porque se lee como un mapa de memoria."
- "`format_load_script` produce comandos `LOAD dir byte`, uno por byte. Solo incluye direcciones escritas, así que no son 256 líneas."
- "`format_load_script_bloques` produce comandos `LOADB dir b1 … b8`. Es lo que se guarda en el `.load` para el monitor serie del Arduino."
  - "Primero separa la memoria en tramos contiguos y después corta cada tramo en bloques de 8."
  - "¿Por qué 8? El buffer serie del Arduino es de 64 bytes y una línea con 8 valores mide unos 51 caracteres. Con 16 valores pasaría de 90 y podría perder bytes sin avisar."
  - "El programa de referencia baja de 29 líneas a 5."

---

## 7. `__main__.py`: la línea de comandos (≈1.5 min)

- "Permite usar el ensamblador con `python -m asm programa.asm`."
- Flujo de `main()`:
  1. "Leer el fuente en UTF-8. En Windows, además, se fuerza la consola a UTF-8 para que salgan bien los acentos."
  2. "Llamar a `assemble()`. Si falla, se imprimen todos los errores juntos y se sale con código 1."
  3. "Escribir tres archivos: `.bin` (los 256 bytes crudos), `.lst` (el listado para la documentación) y `.load` (los comandos para el Arduino)."
  4. "Imprimir un resumen con los bytes emitidos y sus tramos, y los avisos en `stderr`."
- Opciones:
  - "`-o` cambia la carpeta de salida."
  - "`--listing-only` muestra el listado sin escribir archivos."
  - "`--run` ejecuta el resultado en el simulador de `sim/` y muestra la salida de `OUT` y el estado final de los registros. Une ensamblador y simulador de punta a punta."

---

## 8. `__init__.py`: la cara pública (≈30 s)

- "Define qué se exporta desde el paquete: `assemble`, `AssemblyResult`, `ListingRow`, `AssemblerError` y `AssemblyFailed`. Desde fuera solo hace falta `from asm import assemble`."

---

## 9. `examples.py`: utilidad auxiliar (≈30 s)

- "Lee los programas de referencia en `programas/`: la versión con direcciones numéricas y la versión con etiquetas. Es el mismo programa escrito de dos formas."
- "Lee en UTF-8 explícito porque en Windows el valor por defecto es cp1252. Lo usa `demo.py`."

---

## Cierre (≈1 min)

- "Resumen del recorrido: texto, `parser`, `ParsedLine`, pasada 1 (direcciones y símbolos), pasada 2 (bytes) y luego `.bin`, `.lst` y `.load`."
- Decisiones de diseño para destacar:
  1. **La ISA es la única fuente de verdad.** Los nemónicos y patrones se derivan de `sim/isa.py`.
  2. **Los errores se acumulan dentro de cada fase y se aborta entre fases.** Se ven todos los errores útiles y ninguno fantasma.
  3. **La forma de los operandos decide el opcode.** El programador escribe `MOV` y el ensamblador elige entre 5 opcodes.
  4. **Hay dos pasadas** para permitir referencias hacia adelante.
  5. **La salida está pensada para el hardware real.** Los bloques `LOADB` se ajustan al buffer del Arduino.

**Tiempo total estimado:** unos 22 minutos.
