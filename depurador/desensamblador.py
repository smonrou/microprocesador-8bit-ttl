"""Desensamblador: bytes de memoria -> mnemónico + operando.

Lee la tabla de opcodes de ``sim.isa`` en vez de repetirla. Igual que
``asm/mnemonics.py``, este módulo no contiene ni un solo literal de opcode: si
la tabla cambiara, el desensamblador la sigue sin tocarse.

La sintaxis emitida es la misma que acepta el ensamblador (``LDI A,#0x04``,
``LDA 0xC8``), así que lo desensamblado se puede volver a ensamblar.

Módulo puro: no toca sockets, hilos ni Tkinter.
"""

from dataclasses import dataclass
from typing import List, Optional, Sequence

from sim.isa import OPCODE_TABLE, Mode

TAMANO_MEMORIA = 256


@dataclass(frozen=True)
class LineaDesensamblada:
    direccion: int
    bytes_crudos: List[int]
    mnemonico: str
    operando: Optional[int]
    texto: str          # "LDA 0xC8" — listo para pintar

    @property
    def longitud(self) -> int:
        return len(self.bytes_crudos)


def _leer(memoria: Sequence[int], direccion: int) -> int:
    return memoria[direccion & 0xFF] & 0xFF


def desensamblar_en(memoria: Sequence[int], direccion: int) -> LineaDesensamblada:
    """Desensambla la instrucción que empieza en ``direccion``.

    El opcode son SIEMPRE los 4 bits altos del primer byte (A.4), así que
    cualquier byte decodifica: no existe el "opcode inválido". Los 4 bits bajos
    del primer byte no se usan y se ignoran, igual que en el hardware.
    """
    direccion &= 0xFF
    primero = _leer(memoria, direccion)
    spec = OPCODE_TABLE[primero >> 4]

    if spec.length == 1:
        return LineaDesensamblada(
            direccion=direccion,
            bytes_crudos=[primero],
            mnemonico=spec.mnemonic,
            operando=None,
            texto=spec.mnemonic,
        )

    operando = _leer(memoria, direccion + 1)
    if spec.mode == Mode.IMMEDIATE:
        # "LDI A" + ",#0x04": la coma va pegada al registro, como en el .asm.
        texto = f"{spec.mnemonic},#0x{operando:02X}"
    else:
        texto = f"{spec.mnemonic} 0x{operando:02X}"

    return LineaDesensamblada(
        direccion=direccion,
        bytes_crudos=[primero, operando],
        mnemonico=spec.mnemonic,
        operando=operando,
        texto=texto,
    )


def mnemonico_de(ir: int) -> str:
    """El nemónico de un IR suelto, sin necesidad de la memoria.

    Sirve para la línea ``#pc=...`` de STATE, que trae el IR pero no el
    operando. El opcode son los 4 bits altos (A.4), así que los 16 valores
    existen y esto nunca falla.
    """
    return OPCODE_TABLE[(ir >> 4) & 0xF].mnemonic


def desensamblar(memoria: Sequence[int], inicio: int = 0,
                 fin: int = TAMANO_MEMORIA - 1) -> List[LineaDesensamblada]:
    """Desensambla linealmente desde ``inicio`` hasta ``fin`` (ambos incluidos).

    Lineal a propósito: no sigue saltos ni intenta adivinar dónde acaba el
    código y empieza la zona de datos. El mapa 0x00-0xBF / 0xC0-0xFF es una
    CONVENCIÓN (A.6), no algo que el hardware imponga, así que un desensamblador
    que decidiera solo dónde cortar estaría inventando.

    Una instrucción de 2 bytes que empieza justo en ``fin`` se emite completa.
    """
    lineas: List[LineaDesensamblada] = []
    direccion = inicio
    while direccion <= fin:
        linea = desensamblar_en(memoria, direccion)
        lineas.append(linea)
        direccion += linea.longitud
    return lineas


def indice_por_direccion(lineas: Sequence[LineaDesensamblada]) -> dict:
    """Mapa dirección -> posición en la lista, para resaltar la línea del PC.

    Solo se indexa el PRIMER byte de cada instrucción: si el PC cayera en el
    operando de una instrucción de 2 bytes (posible con un salto a media
    instrucción), no hay línea que resaltar y es correcto no resaltar ninguna.
    """
    return {linea.direccion: posicion for posicion, linea in enumerate(lineas)}
