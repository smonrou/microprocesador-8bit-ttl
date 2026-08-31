"""Un byte visto de las cuatro maneras a la vez: binario, hexadecimal,
con signo y sin signo.

El pedido del usuario fue explícito: los valores de salida y de los registros
deben verse en los cuatro formatos SIMULTÁNEAMENTE, sin tener que convertir
mentalmente durante la demostración.

La máquina es de 8 bits y no tiene instrucciones con signo: el complemento a
dos es una LECTURA del mismo byte, no un modo de operación. Se muestra porque
un SUB que "da 0xFC" es más fácil de entender leyéndolo como -4.

Módulo puro: sin dependencias, sin estado.
"""

from dataclasses import dataclass

BITS = 8
MASCARA = (1 << BITS) - 1


def _normalizar(valor: int) -> int:
    """Un byte, pase lo que pase. La memoria es de 8 bits (``Memory.write``
    también enmascara), así que mostrar 0x1FF sería mentir sobre el hardware."""
    return valor & MASCARA


def binario(valor: int) -> str:
    """``0b`` no: los ocho bits pelados, que es lo que se ve en los LEDs."""
    return format(_normalizar(valor), "08b")


def binario_agrupado(valor: int) -> str:
    """Los ocho bits partidos en dos nibbles: ``0000 1100``.

    Cada nibble es un dígito hexadecimal, así que agrupar de cuatro hace la
    conversión mental inmediata (y es como se leen los 74LS181, que son de
    4 bits cada uno).
    """
    bits = binario(valor)
    return f"{bits[:4]} {bits[4:]}"


def hexadecimal(valor: int) -> str:
    """Dos dígitos en MAYÚSCULA, igual que todo el resto del proyecto."""
    return f"0x{_normalizar(valor):02X}"


def sin_signo(valor: int) -> int:
    return _normalizar(valor)


def con_signo(valor: int) -> int:
    """Complemento a dos de 8 bits: 0x00-0x7F -> 0..127, 0x80-0xFF -> -128..-1."""
    entero = _normalizar(valor)
    return entero - (1 << BITS) if entero & 0x80 else entero


@dataclass(frozen=True)
class ResumenNumerico:
    """El mismo byte en los cuatro formatos."""
    byte: int
    binario: str
    hexadecimal: str
    sin_signo: int
    con_signo: int

    def __str__(self) -> str:
        return self.linea()

    def linea(self) -> str:
        """Una sola línea, para un log: ``0x0C  0000 1100  12  +12``."""
        return (f"{self.hexadecimal}  {binario_agrupado(self.byte)}  "
                f"{self.sin_signo}  {con_signo_con_letrero(self.byte)}")


def resumen_numerico(valor: int) -> ResumenNumerico:
    """Los cuatro formatos de un byte, listos para pintar en la GUI."""
    byte = _normalizar(valor)
    return ResumenNumerico(
        byte=byte,
        binario=binario(byte),
        hexadecimal=hexadecimal(byte),
        sin_signo=sin_signo(byte),
        con_signo=con_signo(byte),
    )


def con_signo_con_letrero(valor: int) -> str:
    """El valor con signo escrito siempre con signo: ``+12`` / ``-4``.

    Sin el ``+`` explícito no se distingue de la lectura sin signo cuando el
    byte es menor que 0x80, que es justo la confusión que se quiere evitar.
    """
    return f"{con_signo(valor):+d}"
