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


FORMS_BY_BASE: Dict[str, Tuple[InstructionSpec, ...]] = {}
for _spec in OPCODE_TABLE.values():
    # Se va extendiendo la tupla de esa base con cada spec nuevo.
    FORMS_BY_BASE[base_of(_spec)] = FORMS_BY_BASE.get(base_of(_spec), ()) + (_spec,)


def lookup(base_text: str) -> Tuple[InstructionSpec, ...]:
    """Sin distinguir mayúsculas. Todas las formas de esa base, o () si no
    existe."""
    return FORMS_BY_BASE.get(base_text.upper(), ())


def is_mnemonic(text: str) -> bool:
    """Es una palabra de instrucción (MOV, ADD, JNZ...)?"""
    return text.upper() in FORMS_BY_BASE


def is_directive(text: str) -> bool:
    """Es .ORG o .DB?"""
    return text.upper() in DIRECTIVES


def valid_forms_text(base_text: str) -> str:
    """ "MOV A,[dir], MOV B,[dir], ..." — para los mensajes de error. Sale
    de la tabla, así que sigue siendo correcto si la ISA cambiara."""
    return ", ".join(spec.mnemonic for spec in lookup(base_text))
