"""Protocolo serial: formato y parseo de lo que habla el firmware real.

Espejo exacto de ``firmware/unidad_control/formato.cpp`` (líneas ``#clave=valor``)
y de ``firmware/unidad_control/consola.cpp`` (``leerNumero``, que es un
``strtol`` con base 0).

El bloque humano de A.9 llega ya formateado por el firmware; aquí solo se
reensambla (``EnsambladorDeBloques``) y se le extraen los datos.

Módulo puro: sin sockets, sin hilos, sin Tkinter.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .isa import TABLA_DE_OPCODES, Categoria

# El bloque humano viaja como UN solo Serial.println con '\n' internos
# (consola.cpp::imprimirBloqueYClaves). Al leer por líneas hay que reensamblarlo:
# empieza con esta marca y termina con la otra.
MARCA_INICIO_BLOQUE = "─── Ciclo"
MARCA_FIN_BLOQUE = "PC → 0x"

# Prefijos de las líneas legibles por máquina (formato.cpp).
PREFIJO_CICLO = "#ciclo="
PREFIJO_ESTADO = "#pc="
PREFIJO_PASO = "#paso="

# Nombres de microciclo (isa.cpp::nombrePaso), en el orden del ciclo.
NOMBRES_DE_PASO = ("FETCH", "DECODE", "FETCH2", "EXECUTE", "WAIT", "WRITE")

# Claves de las líneas #clave=valor cuyo valor es un número.
_CLAVES_NUMERICAS = ("ciclo", "pc", "ir", "a", "b", "z", "c", "halted", "salida")


# ── Qué registros trae de verdad una línea #clave=valor ────────────────────
#
# ATENCIÓN, rareza real del firmware (nucleo.cpp): la estructura `Traza` se
# reinicia a ceros en cada instrucción (`traza_ = Traza();`) y cada categoría
# solo rellena los campos que le tocan. Resultado: `aDespues`/`bDespues` —los
# que imprime `formato::lineaClaveValor` como `a=`/`b=`— salen en 0x00 para las
# categorías que no los tocan (saltos, NOP, HLT y el registro que NO es destino
# de un MOV de carga). No es que A valga cero: es que el firmware no lo reporta
# en esa línea.
#
# El depurador replica esa conducta (el objetivo es hablar el mismo protocolo
# que el Arduino real, no uno mejorado) y además la expone, para que la GUI
# pueda conservar el último valor conocido en vez de mostrar un 0 falso.
# El valor autoritativo de A y B siempre se obtiene con STATE, que los lee de
# los registros físicos a través de la ALU.

_REGISTROS_POR_CATEGORIA = {
    Categoria.ALU: (True, True),
    Categoria.GUARDADO_DIRECTO: (True, False),
    Categoria.SALIDA: (True, False),
    Categoria.SALTO_INCONDICIONAL: (False, False),
    Categoria.SALTO_CONDICIONAL: (False, False),
    Categoria.CONTROL: (False, False),
}


def _significativos(categoria, registro) -> Tuple[bool, bool]:
    if categoria in (Categoria.CARGA_DIRECTA, Categoria.CARGA_INMEDIATA):
        return (registro == "A", registro == "B")
    return _REGISTROS_POR_CATEGORIA.get(categoria, (False, False))


def registros_significativos(op: str) -> Tuple[bool, bool]:
    """¿Los campos ``a=``/``b=`` de una línea ``#ciclo=`` traen valor real?

    Se decide por el nemónico, que es lo único que la GUI recibe. Devuelve
    ``(False, False)`` para un nemónico desconocido: ante la duda, no creerle.
    """
    for spec in TABLA_DE_OPCODES.values():
        if spec.mnemonico == op:
            return _significativos(spec.categoria, spec.registro)
    return (False, False)


# ── Parseo de números: espejo de consola.cpp::leerNumero ───────────────────

def parsear_numero(texto: Optional[str]) -> Optional[int]:
    """``strtol(texto, &sobrante, 0)`` exigiendo que consuma la cadena entera.

    Base 0 significa: ``0x``/``0X`` hexadecimal, un ``0`` inicial octal, el
    resto decimal. Devuelve ``None`` donde ``leerNumero`` devolvería ``false``:
    cadena vacía, sin dígitos, o con sobrante.
    """
    if texto is None or texto == "":
        return None

    n = len(texto)
    i = 0
    while i < n and texto[i] in " \t\n\r\f\v":   # strtol salta el espacio inicial
        i += 1

    signo = 1
    if i < n and texto[i] in "+-":
        if texto[i] == "-":
            signo = -1
        i += 1

    if i < n and texto[i] == "0" and i + 1 < n and texto[i + 1] in "xX":
        base, inicio = 16, i + 2
    elif i < n and texto[i] == "0":
        base, inicio = 8, i           # el propio '0' ya es un dígito octal
    else:
        base, inicio = 10, i

    digitos = "0123456789abcdef"[:base]
    fin = inicio
    while fin < n and texto[fin].lower() in digitos:
        fin += 1

    if fin == inicio:      # sobrante == texto: no había ningún dígito
        return None
    if fin != n:           # *sobrante != '\0': quedó basura detrás
        return None

    return signo * int(texto[inicio:fin], base)


def en_rango(valor: int) -> bool:
    """Espeja ``consola.cpp::enRango``."""
    return 0 <= valor <= 255


# ── Reensamblado del bloque multilínea ─────────────────────────────────────

@dataclass
class Mensaje:
    """Una unidad de salida ya reensamblada.

    ``tipo`` es ``"bloque"`` (el volcado A.9 completo, con saltos de línea) o
    ``"linea"`` (cualquier otra línea suelta: ``OK ...``, ``ERR ...``,
    ``#ciclo=...``, un renglón de DUMP...).
    """
    tipo: str
    texto: str

    @property
    def es_bloque(self) -> bool:
        return self.tipo == "bloque"


class EnsambladorDeBloques:
    """Convierte un flujo de líneas sueltas en mensajes completos.

    El firmware manda el bloque humano de A.9 con un único ``Serial.println``,
    pero lleva ``\\n`` dentro: quien lee por líneas recibe siete renglones
    separados que en realidad son UNA respuesta. Este ensamblador los junta
    detectando el inicio (``─── Ciclo``) y el final (``PC → 0x``).
    """

    def __init__(self) -> None:
        self._pendiente: List[str] = []

    @property
    def dentro_de_bloque(self) -> bool:
        return bool(self._pendiente)

    def agregar(self, linea: str) -> List[Mensaje]:
        """Consume una línea y devuelve los mensajes que ya estén completos."""
        linea = linea.rstrip("\r\n")

        if not self._pendiente:
            if linea.startswith(MARCA_INICIO_BLOQUE):
                self._pendiente = [linea]
                return []
            return [Mensaje("linea", linea)]

        self._pendiente.append(linea)
        if linea.startswith(MARCA_FIN_BLOQUE):
            bloque = "\n".join(self._pendiente)
            self._pendiente = []
            return [Mensaje("bloque", bloque)]
        return []

    def vaciar(self) -> List[Mensaje]:
        """Cierra un bloque a medias (desconexión). Lo devuelve tal cual."""
        if not self._pendiente:
            return []
        bloque = "\n".join(self._pendiente)
        self._pendiente = []
        return [Mensaje("bloque", bloque)]


# ── Parseo de las líneas #clave=valor ──────────────────────────────────────

def parsear_linea_clave_valor(linea: str) -> Optional[Dict[str, object]]:
    """Parsea ``#ciclo=...``/``#pc=...``/``#paso=...`` a un diccionario.

    Los valores numéricos salen como ``int`` (``0x`` incluido) y el resto como
    texto. Cuidado: ``op=MOV A,inm`` lleva un espacio DENTRO del valor (los
    nemónicos de 0x1-0x5 son "MOV A,[dir]", "MOV A,inm"...), así que no basta con partir por
    espacios: los trozos sin ``=`` pertenecen a la clave anterior.

    Devuelve ``None`` si la línea no empieza por ``#``.
    """
    if not linea.startswith("#"):
        return None

    datos: Dict[str, object] = {}
    clave: Optional[str] = None
    for token in linea[1:].split(" "):
        if "=" in token:
            clave, _, valor = token.partition("=")
            datos[clave] = valor
        elif clave is not None:
            datos[clave] = f"{datos[clave]} {token}"

    for nombre in _CLAVES_NUMERICAS:
        if nombre in datos:
            numero = parsear_numero(str(datos[nombre]))
            if numero is not None:
                datos[nombre] = numero

    return datos


def extraer_control_alu(bloque: str) -> Optional[Dict[str, object]]:
    """Saca ``M``/``S``/``Cn`` de la línea ``        ALU: M=0 S=0110 Cn=0``.

    Devuelve ``None`` cuando la instrucción no fue de ALU: esa línea sencillamente
    no aparece en el bloque (``formato.cpp`` solo la emite en ``CAT_ALU``).
    """
    for linea in bloque.split("\n"):
        despojada = linea.strip()
        if not despojada.startswith("ALU:"):
            continue
        partes = despojada[len("ALU:"):].split()
        control: Dict[str, object] = {}
        for parte in partes:
            clave, _, valor = parte.partition("=")
            control[clave] = valor
        if not {"M", "S", "Cn"} <= set(control):
            return None
        return {
            "M": int(str(control["M"])),
            "S": str(control["S"]),
            "Cn": int(str(control["Cn"])),
        }
    return None


def numero_de_ciclo(bloque: str) -> Optional[int]:
    """El N de ``─── Ciclo N ───``, o ``None`` si el texto no es un bloque."""
    primera = bloque.split("\n", 1)[0]
    if not primera.startswith(MARCA_INICIO_BLOQUE):
        return None
    resto = primera[len(MARCA_INICIO_BLOQUE):].strip()
    numero = resto.split(" ", 1)[0]
    return parsear_numero(numero)


def parsear_fila_dump(linea: str) -> Optional[Tuple[int, List[int]]]:
    """``"0xC8: 0C 00 "`` -> ``(0xC8, [0x0C, 0x00])``.

    Es como la GUI se entera del contenido de la memoria: no hay otro comando
    que la devuelva. Ojo con el espacio final, que el firmware sí emite
    (``Serial.print(' ')`` detrás de cada byte).

    Devuelve ``None`` si la línea no es una fila de DUMP.
    """
    cabecera, separador, resto = linea.partition(": ")
    if not separador or not cabecera.startswith("0x"):
        return None
    direccion = parsear_numero(cabecera)
    if direccion is None or not en_rango(direccion):
        return None

    bytes_leidos = []
    for token in resto.split():
        if len(token) != 2:
            return None
        try:
            bytes_leidos.append(int(token, 16))
        except ValueError:
            return None
    if not bytes_leidos:
        return None
    return (direccion, bytes_leidos)


def es_respuesta_final(linea: str) -> bool:
    """¿Esta línea cierra un comando de carga? (``OK ...`` o ``ERR ...``).

    El cargador manda una línea de un ``.load`` y espera esto antes de mandar la
    siguiente: el buffer serie del Arduino son 64 bytes y pegar el archivo de
    golpe perdería comandos EN SILENCIO (ver ``consola.h``).
    """
    return linea.startswith("OK") or linea.startswith("ERR")
