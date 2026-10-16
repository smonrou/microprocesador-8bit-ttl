
from typing import List, Optional


class AssemblerError(Exception):
    """Base de los errores de ensamblado."""

    def __init__(self, message: str, line_number: int, line_text: str = ""):
        self.message = message
        self.line_number = line_number  # empieza en 1
        self.line_text = line_text
        super().__init__(str(self))

    def __str__(self) -> str:
        text = f"línea {self.line_number}: {self.message}"
        if self.line_text.strip():
            text += f"\n    {self.line_text.strip()}"
        return text


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


class OperandFormError(AssemblerError):
    """Forma de operando incompatible con la instrucción."""


class InvalidLiteralError(AssemblerError):
    """Literal numérico mal formado."""


class MemoryOverflowError(AssemblerError):
    """El puntero de ensamblado pasaría de 0xFF."""


class OverlapError(AssemblerError):
    """Dos sentencias escriben la misma dirección."""


class AssemblyFailed(Exception):
    """Agrupa los errores de una fase, ordenados por línea."""

    def __init__(self, errors: List[AssemblerError]):
        self.errors = sorted(errors, key=lambda e: e.line_number)
        count = len(self.errors)
        plural = "es" if count != 1 else ""
        super().__init__(f"{count} error{plural} de ensamblado")

    def __str__(self) -> str:
        header = super().__str__()
        return header + "\n" + "\n".join(str(e) for e in self.errors)


class ErrorCollector:
    """Junta los errores de una fase y los lanza al final.

    Entre fases se aborta: con un nemónico desconocido no se sabe el largo
    de la instrucción y la pasada 1 daría errores de dirección falsos.
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
