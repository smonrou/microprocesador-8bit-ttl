"""Pruebas rápidas: el ingeniero dicta pasos y aquí se vuelven ensamblador.

El ingeniero prueba el procesador dictando en vivo ("carga A con 5, niégalo,
vuelve a negarlo, carga B con 3, niégalo, suma"). Este módulo convierte esa
lista de pasos en un programa ``.asm`` legible y lo codifica a bytes con la
tabla de opcodes de ``depurador.isa``. La GUI solo pinta lo que sale de aquí.

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
"""

import io
import re
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from . import cargador
from .isa import TABLA_DE_OPCODES

MAX_VALUE = 255

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


class ProgramaDemasiadoGrande(Exception):
    """El programa no cabe en la zona 0x00-0xBF."""


@dataclass(frozen=True)
class Programa:
    binario: bytes


def _patron_de(mnemonico: str, longitud: int) -> "re.Pattern":
    patron = re.escape(mnemonico)
    operando = r"(0[xX][0-9A-Fa-f]{1,2}|[0-9]{1,3})"
    if "[dir]" in mnemonico:
        patron = patron.replace(r"\[dir\]", r"\[" + operando + r"\]")
    elif mnemonico.endswith(",inm"):
        patron = patron[: -len("inm")] + operando
    elif longitud == 2:
        patron += r"\s+" + operando
    return re.compile(patron)


_PATRONES = [(spec, _patron_de(spec.mnemonico, spec.longitud))
             for spec in TABLA_DE_OPCODES.values()]


def codificar(linea: str) -> List[int]:
    """Una línea de ensamblador (con o sin comentario) -> sus bytes."""
    texto = linea.split(";", 1)[0].strip()
    for spec, patron in _PATRONES:
        coincidencia = patron.fullmatch(texto)
        if coincidencia:
            codigo = [spec.opcode << 4]
            if spec.longitud == 2:
                codigo.append(int(coincidencia.group(1), 0) & 0xFF)
            return codigo
    raise ValueError(f"instrucción desconocida: {texto!r}")


def ensamblar(pasos: Sequence[Paso], out_tras_cada: bool = False) -> Programa:
    """Pasos -> bytes desde 0x00. Lanza ``ProgramaDemasiadoGrande`` si no cabe."""
    binario: List[int] = []
    for linea in generar_asm(pasos, out_tras_cada).splitlines():
        if linea.split(";", 1)[0].strip():
            binario.extend(codificar(linea))
    if len(binario) > BYTES_DE_PROGRAMA:
        raise ProgramaDemasiadoGrande(
            f"{len(binario)} bytes, el máximo es {BYTES_DE_PROGRAMA}")
    return Programa(bytes(binario))


def bytes_usados(programa: Programa) -> int:
    return len(programa.binario)


def lineas_de_carga(programa: Programa) -> List[str]:
    """Los ``LOADB`` a mandar, ocho bytes por línea."""
    lineas = []
    for inicio in range(0, len(programa.binario), 8):
        trozo = programa.binario[inicio:inicio + 8]
        lineas.append(f"LOADB 0x{inicio:02X} "
                      + " ".join(f"0x{byte:02X}" for byte in trozo))
    return lineas


def guardar(pasos: Sequence[Paso], ruta_asm: str,
            out_tras_cada: bool = False) -> Tuple[str, str]:
    """Escribe ``.asm`` y ``.load`` uno al lado del otro, como ``python -m asm``.

    Ensambla antes de escribir nada: si no cabe, no queda un ``.asm`` suelto
    sin su ``.load``. Devuelve las dos rutas escritas.
    """
    programa = ensamblar(pasos, out_tras_cada)
    ruta_load = cargador.ruta_load_de(ruta_asm)
    with io.open(ruta_asm, "w", encoding=cargador.CODIFICACION) as archivo:
        archivo.write(generar_asm(pasos, out_tras_cada))
    with io.open(ruta_load, "w", encoding=cargador.CODIFICACION) as archivo:
        archivo.write("\n".join(lineas_de_carga(programa)) + "\n")
    return ruta_asm, ruta_load


_DECIMAL = re.compile(r"^[+-]?[0-9]+$")
_HEX_0X = re.compile(r"^0[xX][0-9A-Fa-f]+$")
_HEX_DOLAR = re.compile(r"^\$[0-9A-Fa-f]+$")
_BINARIO = re.compile(r"^0[bB][01]+$")


def _leer_numero(texto: str) -> int:
    if _DECIMAL.match(texto):
        return int(texto, 10)
    if _HEX_0X.match(texto):
        return int(texto[2:], 16)
    if _HEX_DOLAR.match(texto):
        return int(texto[1:], 16)
    if _BINARIO.match(texto):
        return int(texto[2:], 2)
    raise ValueError(f"literal numérico mal formado: '{texto}'")


def valor_de_texto(texto: str) -> int:
    """Valor del campo de la GUI: decimal, ``0x0F``, ``$0F``, ``0b1010``.

    Acepta también negativos -128..-1, que se guardan en complemento a 2
    (``-3`` -> ``0xFD``): es como los dicta el ingeniero.
    """
    limpio = texto.strip()
    if not limpio:
        raise ValueError("escribe un valor")
    valor = _leer_numero(limpio)
    if not -128 <= valor <= MAX_VALUE:
        raise ValueError(f"fuera de rango: {valor} (válido -128 a 255)")
    return valor & 0xFF
