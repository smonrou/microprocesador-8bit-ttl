"""Access to the canonical .asm sources shipped with the project."""

from pathlib import Path

PROGRAMS_DIR = Path(__file__).resolve().parent.parent / "programas"

REFERENCE_PATH = PROGRAMS_DIR / "referencia.asm"
REFERENCE_LABELS_PATH = PROGRAMS_DIR / "referencia_etiquetas.asm"


def read_source(path) -> str:
    # Explicit utf-8: the default on Windows is cp1252 and these files
    # contain ó/í/á.
    return Path(path).read_text(encoding="utf-8")


def read_reference_source() -> str:
    """A.7 verbatim, with numeric addresses as in the frozen document."""
    return read_source(REFERENCE_PATH)


def read_reference_labels_source() -> str:
    """Same program written with data labels instead of raw addresses."""
    return read_source(REFERENCE_LABELS_PATH)
