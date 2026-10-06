"""Índice inverso sobre la tabla congelada de la ISA.

ES EL ÚNICO MÓDULO DE asm/ QUE LEE sim.isa.OPCODE_TABLE, y no contiene ni un
solo literal de opcode. La relación nemónico -> opcode (y, desde la sintaxis
estilo x86 del 2026-09-28, también la gramática de los operandos) se
*deriva* de sim.isa.OPCODE_TABLE; nunca se vuelve a escribir a mano. "La
Parte A es inmutable": dos tablas que pudieran desincronizarse violarían
esa regla.

Cada spec.mnemonic tiene la forma "<BASE> <patrón>", p. ej. "MOV A,[dir]":
la palabra base es lo que escribe el programador, y el patrón (separado por
comas) dice qué forma de operandos elige ese opcode. Varios opcodes
comparten base (las cinco formas de MOV); los operandos deciden cuál es,
igual que en x86.

Ejemplo de cómo se distinguen las cinco formas de MOV:
    MOV A,[200]   -> patrón ("A", "[DIR]")   cargar A desde memoria
    MOV B,[200]   -> patrón ("B", "[DIR]")   cargar B desde memoria
    MOV A,5       -> patrón ("A", "INM")     cargar A con un inmediato
    MOV B,5       -> patrón ("B", "INM")     cargar B con un inmediato
    MOV [200],A   -> patrón ("[DIR]", "A")   guardar A en memoria
"""

from typing import Dict, Tuple

from sim.isa import OPCODE_TABLE, InstructionSpec, Mode

# Huecos ("slots") del patrón, tal como aparecen (en mayúsculas) en
# spec.mnemonic. Cualquier otro slot es el nombre literal de un registro.
SLOT_MEMORY = "[DIR]"   # dirección entre corchetes:   MOV A,[200]
SLOT_IMMEDIATE = "INM"  # valor sin corchetes:         MOV A,5
SLOT_ADDRESS = "DIR"    # dirección sin corchetes (saltos): JNZ LOOP

# Registros que pueden aparecer como operandos ("A", "B"). Se obtienen de
# la tabla, no se escriben a mano.
REGISTERS = frozenset(
    spec.register for spec in OPCODE_TABLE.values() if spec.register is not None
)

# Nemónico completo en mayúsculas -> spec: 16 claves únicas ("MOV A,[DIR]",
# "ADD", ...), una por instrucción de la ISA.
MNEMONIC_TABLE = {spec.mnemonic.upper(): spec for spec in OPCODE_TABLE.values()}

# Directivas: no generan instrucciones. .ORG mueve el puntero de
# ensamblado; .DB escribe bytes de datos.
DIRECTIVES = (".ORG", ".DB")


def base_of(spec: InstructionSpec) -> str:
    """La palabra que escribe el programador: "MOV" para "MOV A,[dir]"."""
    return spec.mnemonic.split()[0].upper()


def operand_pattern(spec: InstructionSpec) -> Tuple[str, ...]:
    """Los slots de operando que espera el spec, en el orden del fuente.

    Si el nemónico los trae escritos, se toman de ahí
    ("MOV [dir],A" -> ("[DIR]", "A")). Si no, se deducen del modo de
    direccionamiento: una instrucción DIRECT recibe una dirección sin
    corchetes (JMP/JZ/JNZ) y las NONE/IMPLICIT no llevan nada (ADD, OUT,
    HLT...).
    """
    # split(None, 1): separa solo en el primer espacio -> ["MOV", "A,[dir]"].
    parts = spec.mnemonic.split(None, 1)
    if len(parts) == 2:
        return tuple(slot.strip().upper() for slot in parts[1].split(","))
    if spec.mode == Mode.DIRECT:
        return (SLOT_ADDRESS,)
    return ()


# Base -> todos los specs que se escriben con esa palabra, en orden de
# opcode. Ej.: "MOV" -> (las 5 formas), "ADD" -> (un solo spec).
FORMS_BY_BASE: Dict[str, Tuple[InstructionSpec, ...]] = {}
for _spec in OPCODE_TABLE.values():
    # Se va extendiendo la tupla de esa base con cada spec nuevo.
    FORMS_BY_BASE[base_of(_spec)] = FORMS_BY_BASE.get(base_of(_spec), ()) + (_spec,)


def lookup(base_text: str) -> Tuple[InstructionSpec, ...]:
    """Sin distinguir mayúsculas. Todas las formas de esa base, o () si no
    existe."""
    return FORMS_BY_BASE.get(base_text.upper(), ())


def is_mnemonic(text: str) -> bool:
    """¿Es una palabra de instrucción (MOV, ADD, JNZ...)?"""
    return text.upper() in FORMS_BY_BASE


def is_directive(text: str) -> bool:
    """¿Es .ORG o .DB?"""
    return text.upper() in DIRECTIVES


def valid_forms_text(base_text: str) -> str:
    """ "MOV A,[dir], MOV B,[dir], ..." — para los mensajes de error. Sale
    de la tabla, así que sigue siendo correcto si la ISA cambiara."""
    return ", ".join(spec.mnemonic for spec in lookup(base_text))
