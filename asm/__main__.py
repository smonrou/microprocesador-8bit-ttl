import argparse
import sys
from pathlib import Path

from .assembler import assemble
from .errors import AssemblyFailed

ENCODING = "utf-8"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m asm",
        description="Ensamblador de dos pasadas para el microprocesador de 8 bits.",
    )
    parser.add_argument("source", help="archivo fuente .asm")
    parser.add_argument(
        "-o", "--output-dir", default=None, help="carpeta de salida (por defecto, la del fuente)"
    )
    parser.add_argument(
        "--listing-only",
        action="store_true",
        help="imprime el listado en pantalla sin escribir archivos",
    )
    return parser


def _force_utf8_console() -> None:
    # la consola de Windows usa cp1252 y rompe los acentos
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding=ENCODING)
            except (OSError, ValueError):
                pass


def main(argv=None) -> int:
    _force_utf8_console()
    args = build_parser().parse_args(argv)
    source_path = Path(args.source)

    try:
        source_text = source_path.read_text(encoding=ENCODING)
    except OSError as error:
        print(f"no se pudo leer '{source_path}': {error}", file=sys.stderr)
        return 1

    try:
        result = assemble(source_text)
    except AssemblyFailed as failure:
        print(str(failure), file=sys.stderr)
        return 1

    if args.listing_only:
        print(result.listing)
        _print_warnings(result)
        return 0

    output_dir = Path(args.output_dir) if args.output_dir else source_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = source_path.stem

    bin_path = output_dir / f"{stem}.bin"
    lst_path = output_dir / f"{stem}.lst"
    load_path = output_dir / f"{stem}.load"

    bin_path.write_bytes(result.binary)
    lst_path.write_text(result.listing + "\n", encoding=ENCODING)
    # bloques: menos líneas que pegar, y caben en el buffer de 64 bytes del Arduino
    load_path.write_text(result.load_script_bloques + "\n", encoding=ENCODING)

    emitted = sum(end - start + 1 for start, end in result.spans)
    spans_text = ", ".join(f"0x{start:02X}–0x{end:02X}" for start, end in result.spans)
    print(f"{emitted} bytes emitidos ({spans_text})")
    print(f"  {bin_path}")
    print(f"  {lst_path}")
    print(f"  {load_path}")
    _print_warnings(result)
    return 0


def _print_warnings(result) -> None:
    for warning in result.warnings:
        print(f"aviso: {warning}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
