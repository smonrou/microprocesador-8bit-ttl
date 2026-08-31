"""Reverse index over the frozen ISA table.

THE ONLY MODULE IN asm/ THAT IMPORTS sim.isa, and it contains zero opcode
literals. The mnemonic->opcode mapping is *derived* from
sim.isa.OPCODE_TABLE, never restated. "Parte A es inmutable": two tables
that can drift apart would violate that rule. Guarded by
tests/test_asm_mnemonics.py.
"""

from typing import Optional

from sim.isa import OPCODE_TABLE, InstructionSpec

# Uppercase mnemonic -> spec. Keys come verbatim from the frozen table,
# so "LDI A" and "LDI B" (two words, distinct opcodes) appear as-is.
MNEMONIC_TABLE = {spec.mnemonic.upper(): spec for spec in OPCODE_TABLE.values()}

# Derived, not hardcoded: today it's 2 ("LDI A"). A hypothetical 3-word
# mnemonic added to the ISA would need no change here.
MAX_MNEMONIC_WORDS = max(len(spec.mnemonic.split()) for spec in OPCODE_TABLE.values())

DIRECTIVES = (".ORG", ".DB")


def lookup(mnemonic_text: str) -> Optional[InstructionSpec]:
    """Case-insensitive lookup. Returns None if unknown."""
    return MNEMONIC_TABLE.get(mnemonic_text.upper())


def is_mnemonic(text: str) -> bool:
    return text.upper() in MNEMONIC_TABLE


def is_directive(text: str) -> bool:
    return text.upper() in DIRECTIVES


def completion_hint(token: str) -> Optional[str]:
    """If `token` is the first word of a multi-word mnemonic, describe the
    valid full forms. Derived from the table, so it stays correct if the
    ISA ever changes."""
    prefix = token.upper() + " "
    matches = sorted(key for key in MNEMONIC_TABLE if key.startswith(prefix))
    if not matches:
        return None
    options = ", ".join(matches)
    return f"'{token}' requiere registro ({options})"
