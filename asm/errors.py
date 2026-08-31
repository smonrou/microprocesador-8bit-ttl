"""Assembler error hierarchy.

Mirrors sim/exceptions.py in shape: one base class carrying the shared
context, one subclass per error category the B.2 spec requires.

The line number lives in the base class, not in each call site — B.2 makes
"reportar con número de línea" a hard requirement for every error.
"""

from typing import List, Optional


class AssemblerError(Exception):
    """Base for every assembly-time error. Always carries a source line."""

    def __init__(self, message: str, line_number: int, line_text: str = ""):
        self.message = message
        self.line_number = line_number
        self.line_text = line_text
        super().__init__(str(self))

    def __str__(self) -> str:
        text = f"línea {self.line_number}: {self.message}"
        if self.line_text.strip():
            text += f"\n    {self.line_text.strip()}"
        return text


# ── Categorías exigidas por el spec de B.2 ────────────────────────────────

class UnknownMnemonicError(AssemblerError):
    """Nemónico desconocido."""


class UndefinedLabelError(AssemblerError):
    """Etiqueta usada pero nunca definida."""


class DuplicateLabelError(AssemblerError):
    """Etiqueta definida más de una vez."""


class OperandRangeError(AssemblerError):
    """Operando fuera de rango (>255 o negativo)."""


class OperandCountError(AssemblerError):
    """Instrucción de 2 bytes sin operando, o de 1 byte con operando."""


class ProgramZoneError(AssemblerError):
    """Instrucción emitida fuera de la zona de programa (0x00-0xBF)."""


# ── Categorías adicionales (ver plan: necesarias por .ORG y por el parseo) ──

class OperandFormError(AssemblerError):
    """Forma de operando incompatible con el modo (# donde no va, o falta #)."""


class InvalidLiteralError(AssemblerError):
    """Literal numérico mal formado."""


class MemoryOverflowError(AssemblerError):
    """El puntero de ensamblado pasaría de 0xFF."""


class OverlapError(AssemblerError):
    """Dos sentencias escriben la misma dirección (peligro que introduce .ORG)."""


class AssemblyFailed(Exception):
    """Aggregate raised at the end of a phase that collected errors."""

    def __init__(self, errors: List[AssemblerError]):
        self.errors = sorted(errors, key=lambda e: e.line_number)
        count = len(self.errors)
        plural = "es" if count != 1 else ""
        super().__init__(f"{count} error{plural} de ensamblado")

    def __str__(self) -> str:
        header = super().__str__()
        return header + "\n" + "\n".join(str(e) for e in self.errors)


class ErrorCollector:
    """Accumulates errors within one phase; raises at the phase boundary.

    Rationale (plan): collect-all *within* a phase so five typos surface at
    once, but abort *between* phases — an unknown mnemonic has unknown
    length, so continuing into pass 1 would emit phantom address errors.
    """

    def __init__(self):
        self.errors: List[AssemblerError] = []

    def add(self, error: AssemblerError) -> None:
        self.errors.append(error)

    def raise_if_any(self) -> None:
        if self.errors:
            raise AssemblyFailed(self.errors)

    def __bool__(self) -> bool:
        return bool(self.errors)
