"""``python -m depurador`` — abre el panel frontal.

Tkinter se importa aquí dentro (no arriba del paquete) para que importar
``depurador`` desde un test o desde otro script no exija un entorno gráfico.
"""

import sys


def main() -> int:
    try:
        from .gui import main as abrir_ventana
    except ImportError as error:          # pragma: no cover - depende del entorno
        print("No se pudo cargar Tkinter, que es lo único que necesita la "
              f"interfaz: {error}", file=sys.stderr)
        print("En Linux suele bastar con instalar el paquete python3-tk.",
              file=sys.stderr)
        return 1

    abrir_ventana()
    return 0


if __name__ == "__main__":
    sys.exit(main())
