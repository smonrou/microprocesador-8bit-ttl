"""Reverse index over the frozen ISA table.

THE ONLY MODULE IN asm/ THAT READS sim.isa.OPCODE_TABLE, and it contains zero
opcode literals. The mnemonic->opcode mapping — and, since the x86-style
syntax of 2026-09-28, the operand grammar too — is *derived* from
sim.isa.OPCODE_TABLE, never restated. "Parte A es inmutable": two tables
that can drift apart would violate that rule. Guarded by
tests/test_asm_mnemonics.py.

Each spec.mnemonic is "<BASE> <pattern>", e.g. "MOV A,[dir]": the base word
is what the programmer writes, and the comma-separated pattern says which
operand shapes select that opcode. Several opcodes share one base (the five
MOV forms); the operands decide between them, as in x86.
"""

from typing import Dict, Tuple

from sim.isa import OPCODE_TABLE, InstructionSpec, Mode

# Pattern slots, as they appear (uppercased) in spec.mnemonic.
SLOT_MEMORY = "[DIR]"   # address between brackets:   MOV A,[200]
SLOT_IMMEDIATE = "INM"  # bare value:                 MOV A,5
SLOT_ADDRESS = "DIR"    # bare address (jumps):       JNZ LOOP

# Registers that can appear as literal operands. Derived, not hardcoded.
REGISTERS = frozenset(
    spec.register for spec in OPCODE_TABLE.values() if spec.register is not None
)

# Uppercase full mnemonic -> spec: 16 unique keys ("MOV A,[DIR]", "ADD", ...).
MNEMONIC_TABLE = {spec.mnemonic.upper(): spec for spec in OPCODE_TABLE.values()}

DIRECTIVES = (".ORG", ".DB")


def base_of(spec: InstructionSpec) -> str:
    """The word the programmer writes: "MOV" for "MOV A,[dir]"."""
    return spec.mnemonic.split()[0].upper()


def operand_pattern(spec: InstructionSpec) -> Tuple[str, ...]:
    """Operand slots the spec expects, in source order.

    Explicit in the mnemonic when present ("MOV [dir],A" -> ("[DIR]", "A")).
    Otherwise implied by the Mode: a DIRECT instruction takes one bare
    address (JMP/JZ/JNZ), NONE/IMPLICIT take nothing.
    """
    parts = spec.mnemonic.split(None, 1)
    if len(parts) == 2:
        return tuple(slot.strip().upper() for slot in parts[1].split(","))
    if spec.mode == Mode.DIRECT:
        return (SLOT_ADDRESS,)
    return ()


# Base -> every spec written with it, in opcode order.
FORMS_BY_BASE: Dict[str, Tuple[InstructionSpec, ...]] = {}
for _spec in OPCODE_TABLE.values():
    FORMS_BY_BASE[base_of(_spec)] = FORMS_BY_BASE.get(base_of(_spec), ()) + (_spec,)


def lookup(base_text: str) -> Tuple[InstructionSpec, ...]:
    """Case-insensitive. Every form of that base, or () if unknown."""
    return FORMS_BY_BASE.get(base_text.upper(), ())


def is_mnemonic(text: str) -> bool:
    return text.upper() in FORMS_BY_BASE


def is_directive(text: str) -> bool:
    return text.upper() in DIRECTIVES


def valid_forms_text(base_text: str) -> str:
    """ "MOV A,[dir], MOV B,[dir], ..." — for error messages. Derived from
    the table, so it stays correct if the ISA ever changes."""
    return ", ".join(spec.mnemonic for spec in lookup(base_text))
