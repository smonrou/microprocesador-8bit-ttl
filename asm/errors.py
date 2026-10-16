
from typing import List, Optional


class AssemblerError(Exception):
    """Base de todos los errores de ensamblado. Siempre lleva una línea fuente."""

    def __init__(self, message: str, line_number: int, line_text: str = ""):
        self.message = message          # descripción del problema
        self.line_number = line_number  # línea del .asm (empieza en 1)
        self.line_text = line_text      # texto original de esa línea
        super().__init__(str(self))

    def __str__(self) -> str:
        # Formato: "línea N: mensaje" y, debajo, la línea fuente indentada
        # para que el usuario vea exactamente qué escribió.
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


# ── Categorías adicionales (necesarias por .ORG y por el parseo) ──────────

class OperandFormError(AssemblerError):
    """Forma de operando incompatible con la instrucción (p. ej. corchetes
    donde no van, un '#' de la sintaxis antigua, o un registro mal puesto)."""


class InvalidLiteralError(AssemblerError):
    """Literal numérico mal formado."""


class MemoryOverflowError(AssemblerError):
    """El puntero de ensamblado pasaría de 0xFF."""


class OverlapError(AssemblerError):
    """Dos sentencias escriben la misma dirección (peligro que introduce .ORG)."""


class AssemblyFailed(Exception):
    """Error agregado que se lanza al final de una fase que acumuló errores.

    Es lo que recibe quien llama a assemble(): un solo error que contiene
    la lista completa, ordenada por número de línea.
    """

    def __init__(self, errors: List[AssemblerError]):
        self.errors = sorted(errors, key=lambda e: e.line_number)
        count = len(self.errors)
        plural = "es" if count != 1 else ""
        super().__init__(f"{count} error{plural} de ensamblado")

    def __str__(self) -> str:
        # Encabezado ("3 errores de ensamblado") + un error por línea.
        header = super().__str__()
        return header + "\n" + "\n".join(str(e) for e in self.errors)


class ErrorCollector:
    """Acumula los errores de una fase y los lanza al terminarla.

    Por qué: *dentro* de una fase se juntan todos, para que cinco errores de
    tipeo aparezcan de una vez y no de uno en uno. Pero *entre* fases se
    aborta: un nemónico desconocido tiene un largo desconocido (1 o 2
    bytes), así que seguir a la pasada 1 produciría errores de dirección
    fantasma que solo confundirían.
    """

    def __init__(self):
        self.errors: List[AssemblerError] = []

    def add(self, error: AssemblerError) -> None:
        self.errors.append(error)

    def raise_if_any(self) -> None:
        # Se llama en la frontera de la fase: si hubo errores, se corta aquí.
        if self.errors:
            raise AssemblyFailed(self.errors)

    def __bool__(self) -> bool:
        # Permite escribir "if collector:" para saber si hubo errores.
        return bool(self.errors)
