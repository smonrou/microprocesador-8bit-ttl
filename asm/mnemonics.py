from typing import Dict, Tuple

from .isa import OPCODE_TABLE, InstructionSpec, Mode

# slots del patrón; cualquier otro es el nombre de un registro
SLOT_MEMORY = "[DIR]"   # MOV A,[200]
SLOT_IMMEDIATE = "INM"  # MOV A,5
SLOT_ADDRESS = "DIR"    # JNZ LOOP

REGISTERS = frozenset(
    spec.register for spec in OPCODE_TABLE.values() if spec.register is not None
)

MNEMONIC_TABLE = {spec.mnemonic.upper(): spec for spec in OPCODE_TABLE.values()}

DIRECTIVES = (".ORG", ".DB")


def base_of(spec: InstructionSpec) -> str:
    """La palabra que escribe el programador: "MOV" para "MOV A,[dir]"."""
    return spec.mnemonic.split()[0].upper()


def operand_pattern(spec: InstructionSpec) -> Tuple[str, ...]:
    """Slots de operando del spec: "MOV [dir],A" -> ("[DIR]", "A")."""
    parts = spec.mnemonic.split(None, 1)
    if len(parts) == 2:
        return tuple(slot.strip().upper() for slot in parts[1].split(","))
    if spec.mode == Mode.DIRECT:
        return (SLOT_ADDRESS,)
    return ()


FORMS_BY_BASE: Dict[str, Tuple[InstructionSpec, ...]] = {}
for _spec in OPCODE_TABLE.values():
    FORMS_BY_BASE[base_of(_spec)] = FORMS_BY_BASE.get(base_of(_spec), ()) + (_spec,)


def lookup(base_text: str) -> Tuple[InstructionSpec, ...]:
    return FORMS_BY_BASE.get(base_text.upper(), ())


def is_mnemonic(text: str) -> bool:
    return text.upper() in FORMS_BY_BASE


def is_directive(text: str) -> bool:
    return text.upper() in DIRECTIVES


def valid_forms_text(base_text: str) -> str:
    return ", ".join(spec.mnemonic for spec in lookup(base_text))
