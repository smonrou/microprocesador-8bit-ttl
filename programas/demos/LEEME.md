# Programas de demostración

Once programas que muestran qué aplicaciones permite el set de 16 instrucciones. Cada `.asm` trae su `.load` listo para pegar en el Monitor Serie o en **Cargar .load** del depurador, más su `.lst` (listado con direcciones) y `.bin` (imagen de 256 bytes).

Todos están verificados en el simulador y en el núcleo del firmware, instrucción por instrucción (`tests/test_programas_demos.py`, `tests/test_firmware_nucleo.py`).

## Catálogo

| # | Programa | Qué demuestra | Salida esperada | VEL |
|---|---|---|---|---|
| 01 | `01_contador` | Bucle; igualdad con XOR + JNZ; cuenta binaria en LEDs | `1, 2, …, 15` | 300 |
| 02 | `02_luz_corrediza` | ADD como desplazamiento (A+A); Z y C al desbordar 8 bits | `1, 2, 4, …, 128` ×3 | 200 |
| 03 | `03_parpadeo` | XOR 0xFF = NOT; MOV no toca banderas | `85, 170` ×4 | 400 |
| 04 | `04_fibonacci` | Recurrencia con variables en memoria | `1, 1, 2, 3, 5, …, 233` | 400 |
| 05 | `05_cuadrados` | n² = suma de impares, sin multiplicar | `1, 4, 9, …, 225` | 400 |
| 06 | `06_division` | Cociente y residuo; validación (divisor 0 → 255) | `14, 2` (100 / 7) | 0 |
| 07 | `07_mcd` | Algoritmo de Euclides, bucles anidados | `6` (mcd 48, 18) | 0 |
| 08 | `08_comparador` | Mayor/menor usando solo la bandera Z | `42, 23` | 1000 |
| 09 | `09_contar_unos` | AND como máscara; contar bits en 1 | `182, 5` | 1000 |
| 10 | `10_suma_arreglo` | **Código automodificable** (von Neumann) recorriendo un arreglo | `12, 19, …, 140` | 400 |
| 11 | `11_busqueda` | Búsqueda lineal automodificable; índice o 255 | `4` | 0 |

**VEL** = retardo sugerido (ms) entre instrucciones en el hardware para alcanzar a ver cada `OUT` en los LEDs. Con 0 se ve solo el último valor; la consola serial muestra todos igual.

## Datos en vivo (requisito A.1)

Los parámetros viven en direcciones fijas de la zona de datos. Para cambiarlos no hace falta reensamblar: después de cargar el `.load`, un `LOAD` y `RESET` + `RUN`.

| Programa | Comando | Ejemplo | Resultado |
|---|---|---|---|
| 01 | `LOAD 0xC0 <límite>` | `LOAD 0xC0 0x05` | `1, 2, 3, 4, 5` |
| 02 | `LOAD 0xC0 <vueltas>` | `LOAD 0xC0 0x01` | una sola vuelta |
| 03 | `LOAD 0xC0 <patrón>` · `LOAD 0xC1 <cuántos>` | `LOAD 0xC0 0x0F` | `15, 240, …` |
| 04 | `LOAD 0xC0 <términos>` | `LOAD 0xC0 0x05` | `1, 1, 2, 3, 5` |
| 05 | `LOAD 0xC0 <n>` (máx. 15) | `LOAD 0xC0 0x05` | `1, 4, 9, 16, 25` |
| 06 | `LOAD 0xC0 <dividendo>` · `LOAD 0xC1 <divisor>` | `LOAD 0xC0 0xC8` · `LOAD 0xC1 0x0D` | `15, 5` (200 / 13) |
| 07 | `LOAD 0xC0 <x>` · `LOAD 0xC1 <y>` | `LOAD 0xC0 0x64` · `LOAD 0xC1 0x4B` | `25` (mcd 100, 75) |
| 08 | `LOAD 0xC0 <x>` · `LOAD 0xC1 <y>` | `LOAD 0xC0 0x63` · `LOAD 0xC1 0x07` | `99, 7` |
| 09 | `LOAD 0xC0 <byte>` | `LOAD 0xC0 0xFF` | `255, 8` |
| 10 | `LOAD 0xD0..0xD7 <valor>` · `LOAD 0xC0 <longitud>` | `LOAD 0xC0 0x03` | `12, 19, 49` |
| 11 | `LOAD 0xC0 <buscado>` | `LOAD 0xC0 0x33` | `7` (último) |
|    |  | `LOAD 0xC0 0x64` | `255` (no está) |

Todos los programas inicializan sus variables al arrancar, así que `RESET` + `RUN` repite la ejecución sin recargar el `.load` (también los automodificables: reponen su puntero al inicio).

## Cómo correr uno en el hardware

```
BORRAR                      ← memoria limpia (evita restos del programa anterior)
<pegar el .load>            ← un "OK dir=0x.. n=N" por línea
VEL 400                     ← opcional, según la tabla
RUN
```

Para repetir: `RESET` y `RUN`. Antes de pegar en la placa se puede comprobar en el simulador:

```
python -m asm programas/demos/06_division.asm --run
```

## Orden sugerido para la defensa

1. **01 contador** y **02 luz corrediza** — lo más visual; abre con los LEDs en movimiento.
2. **03 parpadeo** — NOT con XOR y la regla de que MOV no toca banderas.
3. **04 Fibonacci** y **05 cuadrados** — algoritmos numéricos solo con sumas.
4. **06 división** y **07 MCD** — el ingeniero elige los números (`LOAD`), incluido divisor 0.
5. **08 comparador** y **09 contar unos** — decisiones con una sola bandera; AND como máscara.
6. **10 suma de arreglo** y **11 búsqueda** — cierre fuerte: el programa se reescribe a sí mismo porque programa y datos comparten memoria (von Neumann). En la consola, `DUMP 0x00 0x1F` antes y después del `RUN` muestra el byte modificado (`0x0F` en el 10, `0x0B` en el 11).

## Por qué el aviso al ensamblar 10 y 11

```
aviso: datos (.DB) en la zona de programa a partir de 0x0E ...
```

Es intencional. El ensamblador no admite `ETIQUETA+1`, y el programa necesita una etiqueta en el **byte de dirección** de su instrucción `MOV B,[dir]` para reescribirlo. Por eso esa instrucción se escribe byte a byte: `.DB 0x20` (opcode de `MOV B,[dir]`) y `PTR: .DB ARREGLO` (su operando).
