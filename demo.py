"""Secuencia de demostración del proyecto — pensada para la defensa.

    python demo.py            toda la secuencia
    python demo.py 3          solo el paso 3
    python demo.py --lista    ver los pasos disponibles

Cada paso es independiente: se puede ejecutar suelto si el ingeniero
pregunta por algo concreto.
"""

import sys

from asm import assemble
from asm.examples import read_source
from sim.cpu import CPU
from sim.memory import Memory
from sim.trace import format_cycle

ENCODING = "utf-8"

REFERENCIA = "programas/referencia.asm"
DEMO_ALU = "programas/demo_alu.asm"
DEMO_MULT = "programas/demo_multiplicacion.asm"

# Direcciones de los dos operandos de demo_multiplicacion.asm.
# El multiplicador es el byte inmediato de la instrucción `LDI A,#3`;
# el multiplicando es la constante declarada con .DB.
DIR_MULTIPLICADOR = 0x05
DIR_MULTIPLICANDO = 0xCC


def titulo(texto: str) -> None:
    print()
    print("=" * 70)
    print(f"  {texto}")
    print("=" * 70)


def ejecutar(binary, patches=None):
    """Carga una imagen en una CPU limpia y la ejecuta hasta HLT."""
    memoria = Memory()
    memoria.load_bytes(binary)
    for direccion, valor in (patches or {}).items():
        memoria.write(direccion, valor)
    cpu = CPU(memoria)
    cpu.run()
    return cpu


# ── Paso 1 ────────────────────────────────────────────────────────────────

def paso_1_ensamblar():
    titulo("PASO 1 — Ensamblar el programa canónico (A.7)")

    resultado = assemble(read_source(REFERENCIA))
    emitidos = sum(fin - ini + 1 for ini, fin in resultado.spans)

    print(f"Bytes emitidos: {emitidos}")
    print(f"Rangos:         ", end="")
    print(", ".join(f"0x{ini:02X}–0x{fin:02X}" for ini, fin in resultado.spans))
    print(f"Etiquetas:      {resultado.symbols}")
    print()
    print("Las etiquetas se resolvieron en la primera pasada. LOOP quedó en")
    print("0x08, que es donde empieza el cuerpo del bucle.")


# ── Paso 2 ────────────────────────────────────────────────────────────────

def paso_2_listado():
    titulo("PASO 2 — Listado de ensamblado")

    resultado = assemble(read_source(REFERENCIA))
    lineas = resultado.listing.splitlines()

    # Saltar la cabecera de comentarios del fuente: mostrar desde la
    # primera línea que emite bytes.
    inicio = next(i for i, linea in enumerate(lineas) if linea.startswith("00 "))
    for linea in lineas[:2] + lineas[inicio : inicio + 14]:
        print(linea)
    print("...")
    print()
    print(resultado.listing.split("TABLA DE SÍMBOLOS")[1].strip())


# ── Paso 3 ────────────────────────────────────────────────────────────────

def paso_3_ejecutar():
    titulo("PASO 3 — Ejecutar en el simulador (modo RUN)")

    resultado = assemble(read_source(REFERENCIA))
    cpu = ejecutar(resultado.binary)

    print(f"Salida (OUT):  {cpu.output}      ← 4 × 3 = 12")
    print(f"Instrucciones: {cpu.instruction_count}")
    print(f"Estado final:  A=0x{cpu.a:02X}  B=0x{cpu.b:02X}  "
          f"PC=0x{cpu.pc:02X}  Z={cpu.z}  C={cpu.c}")
    print(f"Memoria:       Mem[0xC8]={cpu.memory.read(0xC8)} (resultado)  "
          f"Mem[0xC9]={cpu.memory.read(0xC9)} (contador agotado)")
    print()
    print("El binario se bastó solo: la directiva .DB puso el 4 en 0xCC,")
    print("no hubo que escribir ninguna constante a mano.")


# ── Paso 4 ────────────────────────────────────────────────────────────────

def paso_4_paso_a_paso(ciclos: int = 8):
    titulo(f"PASO 4 — Ejecución paso a paso (primeros {ciclos} ciclos)")

    resultado = assemble(read_source(REFERENCIA))
    memoria = Memory()
    memoria.load_bytes(resultado.binary)
    cpu = CPU(memoria)

    completadas = 0
    while not cpu.halted and completadas < ciclos:
        paso = cpu.step()
        if paso.completed:
            completadas += 1
            print(format_cycle(paso.trace))
            print()

    print("Cada llamada avanza UN microciclo; el bloque se imprime cuando la")
    print("instrucción termina. La línea 'ALU:' es la configuración exacta de")
    print("pines que el Arduino envía al 74LS181 — contrastable con multímetro.")


# ── Paso 5 ────────────────────────────────────────────────────────────────

def paso_5_alu():
    titulo("PASO 5 — Las 6 funciones aprobadas (ADD, SUB, AND, OR, XOR, OUT)")

    resultado = assemble(read_source(DEMO_ALU))
    cpu = ejecutar(resultado.binary)

    etiquetas = [
        ("ADD", "5 + 3", 8),
        ("SUB", "5 - 3", 2),
        ("AND", "0xCC & 0xAA", 0x88),
        ("OR", "0xCC | 0xAA", 0xEE),
        ("XOR", "0xCC ^ 0xAA", 0x66),
        ("NOT", "0x0F ^ 0xFF", 0xF0),
    ]

    print(f"{'OP':<5} {'OPERACIÓN':<14} {'ESPERADO':>10}  {'OBTENIDO':>10}")
    print("-" * 45)
    for (nombre, operacion, esperado), obtenido in zip(etiquetas, cpu.output):
        marca = "OK" if esperado == obtenido else "FALLO"
        print(f"{nombre:<5} {operacion:<14} "
              f"{esperado:>4} (0x{esperado:02X})  {obtenido:>4} (0x{obtenido:02X})  {marca}")

    print()
    print("La última fila suple la ausencia de una instrucción NOT: XOR contra")
    print("0xFF da el complemento a 1, igual que en arquitecturas RISC reales.")


# ── Paso 6 ────────────────────────────────────────────────────────────────

def paso_6_en_vivo():
    titulo("PASO 6 — Datos elegidos en vivo, sin reensamblar")

    resultado = assemble(read_source(DEMO_MULT))

    print("Los dos operandos viven en direcciones fijas:")
    print(f"  multiplicador  → 0x{DIR_MULTIPLICADOR:02X}  "
          f"(byte inmediato de 'LDI A,#n')")
    print(f"  multiplicando  → 0x{DIR_MULTIPLICANDO:02X}  (constante .DB)")
    print()
    print("Cambiarlos son dos comandos LOAD en el monitor serial. Aquí se")
    print("simula ese parcheo sobre la misma imagen ya cargada:")
    print()
    print(f"{'MULTIPLICACIÓN':<18} {'LOAD equivalentes':<34} RESULTADO")
    print("-" * 70)

    for multiplicando, multiplicador in [(4, 3), (7, 6), (9, 9), (12, 20), (16, 16)]:
        cpu = ejecutar(
            resultado.binary,
            {
                DIR_MULTIPLICADOR: multiplicador,
                DIR_MULTIPLICANDO: multiplicando,
            },
        )
        comandos = (
            f"LOAD 0x{DIR_MULTIPLICANDO:02X} 0x{multiplicando:02X} / "
            f"LOAD 0x{DIR_MULTIPLICADOR:02X} 0x{multiplicador:02X}"
        )
        nota = "  ← desborda 8 bits" if multiplicando * multiplicador > 255 else ""
        print(f"{multiplicando:>3} × {multiplicador:<12} {comandos:<34} "
              f"{cpu.output[0]:>3}{nota}")

    print()
    print("Ninguna de esas corridas reensambló nada. El sistema es genérico,")
    print("no una demo pregrabada (requisito A.1).")


# ── Paso 7 ────────────────────────────────────────────────────────────────

def paso_7_errores():
    titulo("PASO 7 — El ensamblador detecta errores con número de línea")

    from asm import AssemblyFailed

    fuente = (
        "      LDI A,#5\n"
        "      LDX 3\n"
        "      LDA 300\n"
        "      ADD 7\n"
        "      JNZ NOEXISTE\n"
        "      HLT\n"
    )

    print("Fuente con cuatro errores deliberados (líneas 2, 3, 4 y 5):")
    for numero, linea in enumerate(fuente.splitlines(), start=1):
        print(f"  {numero}  {linea}")
    print()

    try:
        assemble(fuente)
    except AssemblyFailed as fallo:
        print(f"{len(fallo.errors)} errores detectados de una sola vez:")
        for error in fallo.errors:
            print(f"  línea {error.line_number}: {error.message}")

    print()
    print("Los errores se acumulan y se reportan juntos, no de uno en uno.")
    print()
    print("Falta el de la línea 5 ('JNZ NOEXISTE') y es deliberado: las")
    print("etiquetas se resuelven en la segunda pasada, y el ensamblador aborta")
    print("al terminar una fase con errores. Seguir adelante con el fuente roto")
    print("produciría errores fantasma — un nemónico desconocido tiene longitud")
    print("desconocida, así que todas las direcciones posteriores serían basura.")
    print("Arregla estos tres y el siguiente intento reporta el de la línea 5.")


# ── Paso 8 ────────────────────────────────────────────────────────────────

def paso_8_script_serial():
    titulo("PASO 8 — Script de carga para el Arduino (puente a B.3)")

    resultado = assemble(read_source(REFERENCIA))
    lineas = resultado.load_script_bloques.splitlines()

    for linea in lineas:
        print(f"  {linea}")
    print()
    print("Estas líneas se pegan tal cual en el monitor serial.")
    print()
    print(f"Son {len(lineas)} líneas para {sum(fin - ini + 1 for ini, fin in resultado.spans)} "
          f"bytes, y ninguna pasa de {max(len(l) for l in lineas)} caracteres:")
    print("el buffer de recepción del Arduino son 64 bytes, así que pegarlas")
    print("de golpe no puede perder comandos. Cada una responde con un OK.")
    print()
    print(f"La última carga la constante en la zona de datos (0xCC), que es")
    print("la precondición que exige A.7.")


PASOS = [
    ("Ensamblar el programa canónico", paso_1_ensamblar),
    ("Listado de ensamblado", paso_2_listado),
    ("Ejecutar en el simulador", paso_3_ejecutar),
    ("Ejecución paso a paso", paso_4_paso_a_paso),
    ("Las 6 funciones aprobadas", paso_5_alu),
    ("Datos elegidos en vivo", paso_6_en_vivo),
    ("Detección de errores", paso_7_errores),
    ("Script de carga serial", paso_8_script_serial),
]


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv

    for flujo in (sys.stdout, sys.stderr):
        reconfigure = getattr(flujo, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding=ENCODING)
            except (OSError, ValueError):
                pass

    if "--lista" in argv:
        print("Pasos disponibles:")
        for numero, (nombre, _) in enumerate(PASOS, start=1):
            print(f"  {numero}  {nombre}")
        return 0

    numeros = [arg for arg in argv if arg.isdigit()]
    if numeros:
        for texto in numeros:
            indice = int(texto)
            if not 1 <= indice <= len(PASOS):
                print(f"paso fuera de rango: {indice} (hay {len(PASOS)})",
                      file=sys.stderr)
                return 1
            PASOS[indice - 1][1]()
    else:
        for _, funcion in PASOS:
            funcion()

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
