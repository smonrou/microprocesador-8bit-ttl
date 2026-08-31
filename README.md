# Microprocesador 8-bit TTL

Microprocesador de 8 bits construido con lógica TTL discreta (ALU SN74LS181, registros 74LS273, multiplexores 74LS157), controlado por un Arduino Mega que actúa **únicamente** como unidad de control, RAM y reloj — toda operación aritmética y lógica ocurre en el hardware TTL, nunca en el microcontrolador.

Este repositorio contiene las tres implementaciones del mismo ISA (juego de instrucciones), mantenidas sincronizadas por una suite de pruebas compartida:

- **`sim/`** — simulador de referencia en Python (CPU, ALU, memoria, ciclo fetch-decode-execute).
- **`asm/`** — ensamblador de dos pasadas que traduce programas fuente `.asm` al binario de 256 bytes que carga la máquina.
- **`firmware/`** — firmware en C++ para el Arduino Mega, con una capa HAL que separa el núcleo de control (probado en PC) de las implementaciones reales/simuladas de hardware.
- **`depurador/`** — herramienta gráfica para inspeccionar y depurar la ejecución en el hardware real o contra un servidor serie simulado.
- **`programas/`** — programas de ejemplo en ensamblador, incluido el programa de referencia (multiplicación por sumas repetidas).
- **`tests/`** — suite de pruebas que valida que las tres implementaciones (simulador, firmware, hardware) produzcan resultados idénticos.

## Arquitectura

- **ISA fijo de 16 instrucciones**, opcode de 4 bits en el nibble alto del primer byte, instrucciones de 1 o 2 bytes.
- **Memoria von Neumann de 256 bytes**: `0x00`–`0xBF` programa, `0xC0`–`0xFF` datos (convención respetada por el ensamblador, no impuesta por el hardware).
- **ALU SN74LS181**: suma, resta, AND, OR, XOR; solo estas cinco operaciones actualizan las banderas Z (cero) y C (acarreo).
- **Frontera HAL en el firmware**: el núcleo de control (`nucleo.cpp`) no toca pines ni hace I/O directamente — corre igual sobre hardware real (`hal_arduino.cpp`) o sobre un emulador de los chips TTL (`hal_falso.cpp`) usado en las pruebas de PC.

## Requisitos

| Requisito | Comprobación |
|---|---|
| Python 3.8 o superior | `python --version` |
| pytest | `python -m pip install pytest` |
| g++ (opcional, para pruebas de firmware) | `g++ --version` |

## Instalación

```bash
git clone <url-del-repositorio>
cd <carpeta-del-repositorio>
python -m pip install -r requirements.txt   # opcional: solo necesario para conectar por serie a un Arduino real
```

## Uso rápido

```bash
# Ejecutar toda la suite de pruebas
python -m pytest -q

# Ensamblar un programa
python -m asm programas/referencia.asm

# Ensamblar y ejecutar en el simulador
python -m asm programas/referencia.asm --run

# Ver el listado sin escribir archivos
python -m asm programas/referencia.asm --listing-only

# Recorrido de demostración de todo el sistema (8 pasos)
python demo.py
python demo.py 4          # solo el paso 4
python demo.py --lista    # listar pasos disponibles
```

## Ejecutar pruebas específicas

```bash
python -m pytest tests/test_asm_errors.py -v   # un archivo
python -m pytest -k "reference" -v              # por nombre
python -m pytest -k firmware -v                 # solo pruebas de firmware (compilan C++ con g++)
```

## Estructura del repositorio

```
.
├── sim/          # simulador de referencia (Python)
├── asm/          # ensamblador de dos pasadas (Python)
├── firmware/     # firmware del Arduino Mega (C++) y su capa HAL
├── depurador/    # herramienta gráfica de depuración
├── programas/    # programas de ejemplo en ensamblador
├── tests/        # suite de pruebas compartida
└── demo.py       # recorrido de demostración end-to-end
```

## Estado del proyecto

El diseño lógico, el simulador, el ensamblador y el firmware están completos y validados por pruebas automatizadas. El circuito físico (montaje en TTL) es la fase pendiente; el simulador sirve como referencia de comportamiento correcto para validar el hardware una vez construido.

## Licencia

MIT — ver [LICENSE](LICENSE).
