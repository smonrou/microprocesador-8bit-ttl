from pathlib import Path

PROGRAMS_DIR = Path(__file__).resolve().parent.parent / "programas"

REFERENCE_PATH = PROGRAMS_DIR / "referencia.asm"
REFERENCE_LABELS_PATH = PROGRAMS_DIR / "referencia_etiquetas.asm"


def read_source(path) -> str:
    # utf-8 explícito, en Windows el default es cp1252
    return Path(path).read_text(encoding="utf-8")


def read_reference_source() -> str:
    return read_source(REFERENCE_PATH)


def read_reference_labels_source() -> str:
    return read_source(REFERENCE_LABELS_PATH)
