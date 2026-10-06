"""Ensamblador de dos pasadas para el microprocesador de 8 bits.

Convierte un programa fuente (.asm) en la imagen de 256 bytes que se carga
en la memoria del procesador (simulador, o RAM simulada en el Arduino Mega).

Flujo completo (cada flecha es un módulo de este paquete):

    texto fuente
      -> parser.py      fase 1: cada línea se convierte en un ParsedLine
                        (etiqueta, instrucción/directiva, operandos)
      -> assembler.py   fase 2 (pasada 1): calcula direcciones y la tabla
                        de símbolos
                        fase 3 (pasada 2): emite los bytes y resuelve las
                        etiquetas
      -> listing.py     da formato a la salida: listado, tabla de símbolos,
                        script LOAD/LOADB para el monitor serie

Módulos de apoyo:
    mnemonics.py  tabla nemónico -> opcode, derivada de sim/isa.py (nunca
                  copiada a mano)
    numbers.py    literales numéricos (decimal, 0xFF, $FF, 0b1010)
    errors.py     un tipo de error por categoría, siempre con número de línea
    __main__.py   línea de comandos: python -m asm programa.asm

API pública: `assemble(texto)` devuelve un `AssemblyResult`, o lanza
`AssemblyFailed` con la lista de todos los errores encontrados.
"""

from .assembler import AssemblyResult, ListingRow, assemble
from .errors import AssemblerError, AssemblyFailed

# Lo que se exporta con "from asm import *".
__all__ = [
    "assemble",
    "AssemblyResult",
    "ListingRow",
    "AssemblerError",
    "AssemblyFailed",
]
