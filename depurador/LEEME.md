# DEPURADOR — cómo levantarlo y cómo usarlo

> Manual operativo del panel frontal en Python/Tkinter. Para las **especificaciones** (opcodes, tabla de la ALU, formato de instrucción) la fuente de verdad sigue siendo `contexto_proyecto.md`; para el **protocolo serial**, `firmware/unidad_control/consola.cpp` y `formato.cpp`.

---

## Qué es esto

Un depurador gráfico que muestra **por dónde va pasando la información y qué información es**: los registros A y B en los cuatro formatos a la vez, las banderas Z y C de la unidad de control, las líneas de control de la ALU, la memoria completa con la celda del PC resaltada, el desensamblado con la instrucción actual marcada, y ejecución **microciclo a microciclo** para la demostración.

El Arduino Mega ya está comprado y corriendo el firmware (`referencia.load` corrió en el hardware el 2026-10-01), pero el paquete trae además un **servidor de prueba local**: un Arduino de mentira que habla exactamente el mismo protocolo serial que el firmware real, montado sobre el simulador `sim/`. Todo se puede probar sin hardware y sin instalar nada.

Con la placa **no cambia la interfaz**, solo el transporte: la casilla del servidor local viene desmarcada (modo placa); para probar sin hardware se marca antes de conectar.

---

## Requisitos

| Requisito | Comprobación | ¿Obligatorio? |
|---|---|---|
| Python 3.8 o superior | `python --version` | Sí |
| Tkinter | `python -m tkinter` (abre una ventanita) | Sí — viene con Python en Windows y macOS |
| pyserial | `python -m pip install -r requirements.txt` | **No** — solo para conectarse al Arduino real |

> En Linux, Tkinter a veces no viene instalado: `sudo apt install python3-tk`.

**El flujo completo con el servidor de prueba local no necesita ni una sola dependencia de terceros.** Sin pyserial, la lista de puertos serie sale vacía y todo lo demás funciona igual.

---

## Levantarlo

Desde la **raíz del proyecto** (la carpeta que contiene `sim/`, `asm/`, `depurador/` y `pytest.ini`):

```
python -m depurador
```

Antes de la primera vez, conviene comprobar que la suite está verde:

```
python -m pytest -q
```

Debe terminar sin fallos (`925 passed` a 2026-10-01). Si algo falla, no sigas: el resto de este documento asume una suite verde.

---

## Primer arranque, paso a paso

1. **Conectar.** La casilla `servidor de prueba local` viene desmarcada (modo placa): márcala y pulsa **Conectar**.
   El indicador pasa a `TCP 127.0.0.1:<puerto>` y en el registro de tráfico aparece el saludo de la placa:

   ```
   Microprocesador de 8 bits - unidad de control lista
   ALU: 2x SN74LS181  Registros: 2x 74LS273  Mux: 2x 74LS157
   ```

2. **Cargar un programa.** Pulsa **Cargar .load** y elige `programas/referencia.load`
   (el programa canónico de A.7: multiplica 4 × 3 por sumas repetidas, `OUT` debe dar 12).

   Las líneas se mandan **una a una, esperando el `OK` de cada una** antes de la siguiente. No es lentitud gratuita: el buffer de recepción del Arduino son 64 bytes y mandarlas de golpe perdería comandos **en silencio** (ver el comentario de `firmware/unidad_control/consola.h`).

   Al terminar, la rejilla de memoria se llena y el desensamblado muestra `MOV A,0x00 / MOV [0xC8],A / MOV A,0x03 / ...`.

3. **Elegir la velocidad.** Arrastra **VEL** (0–5000 ms, el retardo entre instrucciones en `RUN`) y pulsa el botón `ms` para aplicarlo. Para la demostración, 300–500 ms se ve bien; para ir rápido, 0.

4. **Ejecutar.** Pulsa **RUN**. Las instrucciones van apareciendo una a una y al final el registro de salidas muestra:

   ```
   OUT  hex 0x0C   bin 0000 1100   sin signo  12   con signo  +12
   ```

5. **Paso a paso.** Pulsa **RESET** (conserva el programa) y luego **STEP** repetidamente.
   Cada pulsación avanza **un microciclo**, no una instrucción entera. La etiqueta `paso:` va recorriendo `FETCH → DECODE → FETCH2 → EXECUTE` (y además `WAIT → WRITE` en las operaciones de ALU). El bloque legible solo se imprime al terminar la instrucción; una instrucción tarda 5 microciclos si es de ALU, 3 si es `NOP`/`HLT`/`OUT` y 4 si es de 2 bytes (`MOV`, saltos).

---

## Qué mira cada panel

| Panel | Qué muestra | De dónde sale |
|---|---|---|
| **Registros** | A y B en hexadecimal, binario, sin signo y con signo, **a la vez** | línea `#clave=valor` y `STATE` |
| **Unidad de control** | PC, IR con el nemónico decodificado, número de ciclo y microciclo | `#ciclo=` / `#paso=` |
| **Banderas** | Z y C. Se encienden en ámbar cuando valen 1 | `z=` / `c=` |
| **ALU 2x SN74LS181** | Las líneas de control reales: `M`, `S3-S0`, `Cn` | la línea `ALU:` del bloque legible |
| **Memoria** | Los 256 bytes; la celda del PC va resaltada en azul | `DUMP` |
| **Desensamblado** | Dirección, bytes y mnemónico; la línea actual va seleccionada | `sim.isa.OPCODE_TABLE` |
| **Salidas (OUT)** | Cada valor que sacó `OUT`, en los cuatro formatos. **Limpiar** vacía el panel | `salida=` |
| **Tráfico crudo** | Todo lo enviado (`>`) y recibido, **literal**. **Limpiar** vacía el panel | el cable |

### Dos detalles que conviene entender antes de la defensa

- **`M` distingue SUB de XOR.** Las dos operaciones comparten `S=0110` en el 74LS181; lo único que las separa es el pin `M` (`M=0` aritmético para SUB, `M=1` lógico para XOR). El panel de la ALU lo muestra explícitamente por eso.

- **Solo las 5 operaciones de ALU tocan Z y C.** los `MOV` (cargas y guardado), los saltos, `OUT`, `HLT` y `NOP` no las modifican nunca. El programa de referencia depende de ello: hace `SUB → MOV [dir],A → JNZ` y necesita que ese `MOV` no pise la Z.

---

## Botones

| Botón | Comando que manda | Qué hace |
|---|---|---|
| **RUN** | `RUN` | Ejecuta hasta `HLT`, con el retardo de `VEL` entre instrucciones |
| **STEP** | `STEP` | Avanza **un microciclo** |
| **RESET** | `RESET` | PC, registros y banderas a 0. **Conserva la memoria** (el programa sigue cargado) |
| **BORRAR** | `BORRAR` | Borra los 256 bytes a `0x00` y reinicia |
| **STATE** | `STATE` | Vuelve a leer el estado. Es la lectura **autoritativa** de A y B |
| **DUMP** | `DUMP` | Relee la memoria entera y repinta la rejilla |
| **Cargar .load** | `LOADB ...` | Manda un `.load` línea por línea |
| **Pruebas rápidas ▸** | — | Despliega el panel de pruebas dictadas (ver abajo) |
| **`ms`** | `VEL <n>` | Aplica el retardo elegido en la barra |

Tras un `HLT`, `RUN` y `STEP` responden `ERR la CPU esta detenida; usa RESET`. Es el comportamiento del firmware, no un fallo: pulsa **RESET** y vuelve a ejecutar (el programa sigue en memoria).

---

## Pruebas rápidas (cuando el ingeniero dicta)

Para pruebas dictadas en vivo ("carga A con 5, niégalo, vuelve a negarlo, carga B con 3, niégalo, suma") no hace falta escribir un `.asm` ni pasar por `python -m asm`. El botón **Pruebas rápidas ▸** (a la derecha de la barra de conexión) despliega un panel:

1. Escribe el valor en `valor v` (`5`, `0x0F`, `$0F`, `0b1010` o negativo `-3`, que se guarda en complemento a 2 → `0xFD`).
2. Pulsa un botón por cada paso que dicte: `A ← v`, `B ← v`, `NOT A`, `NOT B`, `NEG A`, `NEG B`, `ADD`, `SUB`, `AND`, `OR`, `XOR`, `OUT`.
3. A cada clic se reescribe el **ensamblador generado** (con un comentario por paso y `HLT` al final). La lista de pasos muestra el **valor esperado** de A, B, Z y C tras cada paso, calculado con el simulador `sim/`.
4. **Cargar y ejecutar** (solo con conexión) manda `BORRAR`, los `LOADB`, `DUMP`, `RESET` y `RUN`, con la misma confirmación línea a línea que **Cargar .load**. El `DUMP` previo hace que memoria y desensamblado muestren el programa **antes** de que empiece a correr. Mientras corre, el PC resaltado avanza sobre él. Las temporales `0xF0`/`0xF1` se repintan al llegar al `HLT`, porque durante un `RUN` el Arduino no atiende comandos.

Con la casilla **OUT tras cada paso** se añade un `OUT` después de cada paso, así los LEDs muestran cada valor intermedio (súbele `VEL` para alcanzar a verlos). Ojo: `OUT` siempre saca **A**; tras `B ← v` o `NOT B` los LEDs repiten A, el valor de B se ve en el panel de registros. **Deshacer** quita el último paso, **Limpiar** los quita todos y **Guardar** escribe el `.asm` y su `.load` con el mismo nombre (como `python -m asm`), así la prueba se puede volver a cargar con **Cargar .load**.

### Por qué NOT y NEG son varias instrucciones

El ISA (Parte A, congelada) **no tiene NOT ni NEG**, y toda operación de ALU deja su resultado en **A**. Cada botón genera una macro de instrucciones reales que además **conserva el otro registro**. B no se puede guardar directo (no existe `MOV [dir],B`), así que se copia a A pasando por la ALU (`MOV A,0` + `ADD` → A = 0 + B). Las temporales están en `0xF0` (A) y `0xF1` (B), en la zona de datos:

| Paso | Instrucciones | Bytes |
|---|---|---|
| `NOT A` | `MOV [0xF0],A` · `MOV A,0` · `ADD` · `MOV [0xF1],A` · `MOV B,0xFF` · `MOV A,[0xF0]` · `XOR` · `MOV B,[0xF1]` | 14 |
| `NOT B` | `MOV [0xF0],A` · `MOV A,0xFF` · `XOR` · `MOV [0xF1],A` · `MOV B,[0xF1]` · `MOV A,[0xF0]` | 11 |
| `NEG A` | `MOV [0xF0],A` · `MOV A,0` · `ADD` · `MOV [0xF1],A` · `MOV B,[0xF0]` · `MOV A,0` · `SUB` · `MOV B,[0xF1]` | 14 |
| `NEG B` | `MOV [0xF0],A` · `MOV A,0` · `SUB` · `MOV [0xF1],A` · `MOV B,[0xF1]` · `MOV A,[0xF0]` | 11 |

NOT = XOR con `0xFF` (complemento a 1); NEG = `0 - x` (complemento a 2). La operación la sigue haciendo el 74LS181: el PC solo escribe instrucciones. Tras una macro, Z y C son los de su `XOR`/`SUB` final (los `MOV` no tocan banderas). Todo el programa debe caber en `0x00–0xBF` (192 bytes, el panel muestra cuántos van); si un paso no cabe, se rechaza y se avisa.

---

## Preparar tus propios programas

El depurador carga archivos `.load`, que genera el ensamblador. Al cargar ignora las líneas vacías y las que empiezan con `;` o `#`, el diálogo abre en `programas/` y, al terminar, hace un `DUMP` automático:

```
python -m asm programas/referencia.asm      # produce .bin, .lst y .load
```

Luego se abre ese `.load` con el botón **Cargar .load**. Los que ya vienen hechos:

| Archivo | Qué demuestra |
|---|---|
| `programas/referencia.load` | El programa canónico de A.7 — `OUT` = 12 |
| `programas/referencia_etiquetas.load` | El mismo, escrito con etiquetas |
| `programas/demo_alu.load` | Las cinco operaciones de la ALU (seis salidas) |
| `programas/demo_multiplicacion.load` | Multiplicación por sumas repetidas |

---

## Conectarse al Arduino real

1. `python -m pip install -r requirements.txt` (instala pyserial — **solo hace falta para esto**).
2. Sube `firmware/unidad_control/` a la placa con el IDE de Arduino.
3. **Cierra el Monitor Serie del IDE.** El puerto es de un solo dueño: si el Monitor lo tiene abierto, el depurador no podrá abrirlo.
4. En el depurador, deja **desmarcada** `servidor de prueba local` (así arranca), pulsa `↻` para refrescar la lista, elige el puerto (`COM3`, `/dev/ttyACM0`, …) y pulsa **Conectar**.

La velocidad es 115200 baudios, la misma que fija `unidad_control.ino`. A partir de ahí, todos los paneles y botones funcionan **exactamente igual**: el depurador no sabe si está hablando con el simulador o con el hardware.

---

## Si algo va mal

| Síntoma | Causa probable |
|---|---|
| `No module named 'depurador'` | No estás en la raíz del proyecto. `cd` a la carpeta que contiene `pytest.ini` |
| La lista de puertos dice `(falta pyserial)` | Normal si no lo instalaste. El servidor local no lo necesita |
| No se puede abrir el puerto serie | El Monitor Serie del IDE lo tiene ocupado, o falta el driver USB de la placa |
| `ERR la CPU esta detenida; usa RESET` | El programa llegó a `HLT`. Pulsa **RESET** |
| `ERR limite de instrucciones; posible bucle infinito` | El programa no llega nunca a `HLT` (¿falta el `HLT`? ¿un salto mal puesto?) |
| La memoria sale toda en `00` | No cargaste ningún `.load`, o pulsaste **BORRAR** |
| `ERR valor fuera de rango (0-255)` | Un byte del `.load` no cabe en 8 bits |
| La ventana no abre y se queja de Tkinter | En Linux: `sudo apt install python3-tk` |

---

## Cómo está hecho (para tocarlo)

```
depurador/
├── protocolo.py         formato y parseo del protocolo serial — espejo de formato.cpp
├── formato_numerico.py  un byte en binario / hex / con signo / sin signo
├── desensamblador.py    bytes -> mnemónico, leyendo sim.isa.OPCODE_TABLE
├── cargador.py          lectura de un .load
├── pruebas_rapidas.py   pasos dictados -> .asm + predicción (panel de pruebas rápidas)
├── servidor_falso.py    el Arduino de mentira (TCP, solo biblioteca estándar)
├── transporte.py        TransporteSocket (TCP) y TransporteSerial (pyserial, import perezoso)
├── gui.py               la ventana Tkinter — solo cableado, sin lógica propia
└── __main__.py          `python -m depurador`
```

Dos reglas que **no se pueden romper** al modificar esto:

1. **El hilo lector nunca toca un widget.** Empuja líneas a una `queue.Queue`; `gui.py` la vacía desde `root.after(50, ...)`, en el hilo principal. Tkinter no es seguro entre hilos, y saltarse esto produce cuelgues que aparecen semanas después y no se reproducen.

2. **El bloque legible no se reimplementa.** Lo genera `sim.trace.format_cycle()`, que `tests/test_firmware_formato.py` ya demuestra byte-idéntico al del firmware. Escribir una tercera versión sería garantizar que algún día diverjan.

Todo salvo `gui.py` se prueba sin pantalla — 393 pruebas, ninguna necesita hardware ni pyserial:

```
python -m pytest -k depurador -v
```

`tests/test_depurador_end_to_end.py` es el que importa: levanta el servidor falso, carga `programas/referencia.load` con un socket pelado y exige `salida=12`.

---

## Una rareza real del firmware, documentada aquí a propósito

En las líneas `#clave=valor`, los campos `a=` y `b=` salen en `0x00` para los **saltos, `NOP`, `HLT`** y para **el registro que no es destino** de un `MOV` de carga (`MOV A,[dir]`, `MOV B,inm`...).

No es que A valga cero: es que `nucleo.cpp` reinicia la estructura `Traza` en cada instrucción (`traza_ = Traza();`) y cada categoría solo rellena los campos que le tocan. El bloque legible nunca imprime esos campos, así que nadie lo había notado.

El servidor falso **replica esa conducta** — el objetivo es hablar el mismo protocolo que el Arduino real, no uno mejorado — y el depurador la compensa: conserva el último valor conocido en vez de pintar un 0 falso. Para leer A y B con seguridad, usa **STATE**, que los saca de los registros físicos pasando por la ALU (`F=A` con `M=0,S=0000,Cn=1`).

Si algún día se corrige `nucleo.cpp` para rellenar `aDespues`/`bDespues` en todas las categorías, hay que quitar `protocolo.registros_significativos()` y sus pruebas.
