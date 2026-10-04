"""Pruebas rápidas: el ingeniero dicta pasos y aquí se vuelven ensamblador.

El ingeniero prueba el procesador dictando en vivo ("carga A con 5, niégalo,
vuelve a negarlo, carga B con 3, niégalo, suma"). Este módulo convierte esa
lista de pasos en un programa ``.asm`` legible, lo ensambla en memoria con el
mismo ``asm.assemble`` de siempre y predice con ``sim/`` qué valores deben
quedar en A y B tras cada paso. La GUI solo pinta lo que sale de aquí.

Módulo puro: no abre puertos ni toca Tkinter.

El ISA (Parte A, congelada) no tiene NOT ni NEG, y TODA operación de la ALU
deja su resultado en A. Por eso "negar" es una macro de instrucciones reales:

- NOT x = x XOR 0xFF            (complemento a 1)
- NEG x = 0 - x                  (complemento a 2)

Cada macro conserva el OTRO registro. Como el Arduino no puede guardar B
directamente (no hay ``MOV [dir],B``), B se copia a A a través de la ALU con
``MOV A,0`` + ``ADD`` (A = 0 + B) y de ahí a memoria. Las celdas temporales
viven en la zona de datos (0xC0-0xFF, por convención).

La aritmética la sigue haciendo el 74LS181: el PC solo genera instrucciones.
La predicción corre en el simulador y nunca se mete en el programa.
"""

import io
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from asm.assembler import AssemblyResult, assemble
from asm.errors import AssemblerError
from asm.numbers import MAX_VALUE, parse_number
from sim.cpu import CPU
from sim.memory import Memory

from . import cargador

TEMP_A = 0xF0   # copia de A mientras una macro usa la ALU
TEMP_B = 0xF1   # copia de B (o resultado de paso hacia B)

FIN_ZONA_PROGRAMA = 0xBF
BYTES_DE_PROGRAMA = FIN_ZONA_PROGRAMA + 1

CARGAR_A = "A"
CARGAR_B = "B"
NOT_A = "NOT A"
NOT_B = "NOT B"
NEG_A = "NEG A"
NEG_B = "NEG B"
SALIDA = "OUT"
OPERACIONES_ALU = ("ADD", "SUB", "AND", "OR", "XOR")

TIPOS_CON_VALOR = (CARGAR_A, CARGAR_B)
TIPOS = TIPOS_CON_VALOR + (NOT_A, NOT_B, NEG_A, NEG_B) + OPERACIONES_ALU + (SALIDA,)


@dataclass(frozen=True)
class Paso:
    tipo: str
    valor: Optional[int] = None

    def __post_init__(self) -> None:
        if self.tipo not in TIPOS:
            raise ValueError(f"tipo de paso desconocido: {self.tipo!r}")
        if self.tipo in TIPOS_CON_VALOR:
            if self.valor is None or not 0 <= self.valor <= MAX_VALUE:
                raise ValueError(f"{self.tipo} necesita un valor entre 0 y 255")
        elif self.valor is not None:
            raise ValueError(f"{self.tipo} no lleva valor")


@dataclass(frozen=True)
class Prediccion:
    """Estado que el simulador espera tras un paso."""
    a: int
    b: int
    z: int
    c: int


def _hex(valor: int) -> str:
    return f"0x{valor:02X}"


def descripcion(paso: Paso) -> str:
    """Texto corto para la lista: ``A ← 0x05``, ``NOT B``, ``ADD``..."""
    if paso.tipo in TIPOS_CON_VALOR:
        return f"{paso.tipo} ← {_hex(paso.valor)}"
    return paso.tipo


def instrucciones_de(paso: Paso) -> List[str]:
    """Las líneas de ensamblador de un paso, ya con su comentario."""
    temp_a, temp_b = _hex(TEMP_A), _hex(TEMP_B)
    tipo = paso.tipo

    if tipo == CARGAR_A:
        return [f"MOV A,{_hex(paso.valor)}"]
    if tipo == CARGAR_B:
        return [f"MOV B,{_hex(paso.valor)}"]
    if tipo in OPERACIONES_ALU:
        return [f"{tipo:<14}; A = A {tipo} B"]
    if tipo == SALIDA:
        return ["OUT"]

    if tipo == NOT_A:
        return [
            f"MOV [{temp_a}],A  ; guarda A",
            "MOV A,0",
            "ADD           ; A = B (copia vía ALU)",
            f"MOV [{temp_b}],A  ; guarda B",
            "MOV B,0xFF",
            f"MOV A,[{temp_a}]",
            "XOR           ; A = NOT A",
            f"MOV B,[{temp_b}]  ; restaura B",
        ]
    if tipo == NOT_B:
        return [
            f"MOV [{temp_a}],A  ; guarda A",
            "MOV A,0xFF",
            "XOR           ; A = NOT B",
            f"MOV [{temp_b}],A",
            f"MOV B,[{temp_b}]  ; B = NOT B",
            f"MOV A,[{temp_a}]  ; restaura A",
        ]
    if tipo == NEG_A:
        return [
            f"MOV [{temp_a}],A  ; guarda A",
            "MOV A,0",
            "ADD           ; A = B (copia vía ALU)",
            f"MOV [{temp_b}],A  ; guarda B",
            f"MOV B,[{temp_a}]  ; B = A original",
            "MOV A,0",
            "SUB           ; A = 0 - A",
            f"MOV B,[{temp_b}]  ; restaura B",
        ]
    # NEG_B: __post_init__ ya descartó cualquier otro tipo.
    return [
        f"MOV [{temp_a}],A  ; guarda A",
        "MOV A,0",
        "SUB           ; A = 0 - B",
        f"MOV [{temp_b}],A",
        f"MOV B,[{temp_b}]  ; B = -B",
        f"MOV A,[{temp_a}]  ; restaura A",
    ]


def generar_asm(pasos: Sequence[Paso], out_tras_cada: bool = False) -> str:
    """Programa completo: un bloque comentado por paso y ``HLT`` al final.

    Con ``out_tras_cada`` se añade un ``OUT`` después de cada paso (salvo los
    que ya son ``OUT``), para que los LEDs muestren cada valor intermedio.
    """
    lineas: List[str] = []
    for numero, paso in enumerate(pasos, start=1):
        lineas.append(f"; paso {numero}: {descripcion(paso)}")
        lineas.extend(f"      {instruccion}" for instruccion in instrucciones_de(paso))
        if out_tras_cada and paso.tipo != SALIDA:
            lineas.append("      OUT")
        lineas.append("")
    lineas.append("      HLT")
    return "\n".join(lineas) + "\n"


def ensamblar(pasos: Sequence[Paso], out_tras_cada: bool = False) -> AssemblyResult:
    """Ensambla en memoria. Propaga ``AssemblyFailed`` si no cabe en 0x00-0xBF."""
    return assemble(generar_asm(pasos, out_tras_cada))


def bytes_usados(resultado: AssemblyResult) -> int:
    """Bytes de programa (zona 0x00-0xBF), sin contar las temporales."""
    return sum(fin - inicio + 1 for inicio, fin in resultado.spans
               if inicio <= FIN_ZONA_PROGRAMA)


def lineas_de_carga(resultado: AssemblyResult) -> List[str]:
    """Los ``LOADB`` a mandar, igual que si vinieran de un ``.load``."""
    return cargador.lineas_de_texto(resultado.load_script_bloques)


def guardar(pasos: Sequence[Paso], ruta_asm: str,
            out_tras_cada: bool = False) -> Tuple[str, str]:
    """Escribe ``.asm`` y ``.load`` uno al lado del otro, como ``python -m asm``.

    Ensambla ANTES de escribir nada: si no cabe, no queda un ``.asm`` suelto
    sin su ``.load``. Devuelve las dos rutas escritas.
    """
    resultado = ensamblar(pasos, out_tras_cada)
    ruta_load = cargador.ruta_load_de(ruta_asm)
    with io.open(ruta_asm, "w", encoding=cargador.CODIFICACION) as archivo:
        archivo.write(generar_asm(pasos, out_tras_cada))
    with io.open(ruta_load, "w", encoding=cargador.CODIFICACION) as archivo:
        archivo.write(resultado.load_script_bloques + "\n")
    return ruta_asm, ruta_load


def _correr(pasos: Sequence[Paso]) -> Prediccion:
    memoria = Memory()
    memoria.load_bytes(ensamblar(pasos).binary)
    cpu = CPU(memoria)
    cpu.run()
    return Prediccion(cpu.a, cpu.b, cpu.z, cpu.c)


def predecir(pasos: Sequence[Paso]) -> List[Prediccion]:
    """Estado esperado tras cada paso, corriendo cada prefijo en ``sim/``.

    Los ``OUT`` no cambian A, B ni las banderas, así que la predicción no
    depende de ``out_tras_cada``. Correr cada prefijo es cuadrático, pero
    con programas de este tamaño (máx. 192 bytes) no importa.
    """
    return [_correr(pasos[:fin]) for fin in range(1, len(pasos) + 1)]


def valor_de_texto(texto: str) -> int:
    """Valor del campo de la GUI: decimal, ``0x0F``, ``$0F``, ``0b1010``.

    Acepta también negativos -128..-1, que se guardan en complemento a 2
    (``-3`` -> ``0xFD``): es como los dicta el ingeniero.
    """
    limpio = texto.strip()
    if not limpio:
        raise ValueError("escribe un valor")
    try:
        valor = parse_number(limpio, 0, limpio)
    except AssemblerError as error:
        raise ValueError(error.message) from None
    if not -128 <= valor <= MAX_VALUE:
        raise ValueError(f"fuera de rango: {valor} (válido -128 a 255)")
    return valor & 0xFF
