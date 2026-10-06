"""Acceso a los programas .asm canónicos que vienen con el proyecto."""

from pathlib import Path

# Carpeta programas/, un nivel por encima de asm/.
PROGRAMS_DIR = Path(__file__).resolve().parent.parent / "programas"

REFERENCE_PATH = PROGRAMS_DIR / "referencia.asm"
REFERENCE_LABELS_PATH = PROGRAMS_DIR / "referencia_etiquetas.asm"


def read_source(path) -> str:
    # utf-8 explícito: en Windows el valor por defecto es cp1252 y estos
    # archivos contienen ó/í/á.
    return Path(path).read_text(encoding="utf-8")


def read_reference_source() -> str:
    """A.7 literal, con direcciones numéricas como en el documento congelado."""
    return read_source(REFERENCE_PATH)


def read_reference_labels_source() -> str:
    """El mismo programa, escrito con etiquetas de datos en vez de
    direcciones numéricas."""
    return read_source(REFERENCE_LABELS_PATH)
