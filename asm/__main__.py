"""CLI: python -m asm programa.asm

Writes three artifacts next to the source (or into -o):
  .bin   256 raw bytes, the memory image
  .lst   assembly listing + symbol table, for the documentation
  .load  LOAD <dir> <byte> commands for the Arduino serial monitor (B.3)

All text files are opened with an explicit utf-8 encoding: the Windows
default is cp1252 and both sources and listings contain ó/í/á.
"""

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
    parser.add_argument(
        "--run",
        action="store_true",
        help="ensambla y ejecuta el resultado en el simulador (B.1)",
    )
    return parser


def _force_utf8_console() -> None:
    """The Windows console defaults to cp1252, which mangles the accents and
    dashes in our messages. Python 3.7+ can retarget the streams."""
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
        if args.run:
            _run(result)
        return 0

    output_dir = Path(args.output_dir) if args.output_dir else source_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = source_path.stem

    bin_path = output_dir / f"{stem}.bin"
    lst_path = output_dir / f"{stem}.lst"
    load_path = output_dir / f"{stem}.load"

    bin_path.write_bytes(result.binary)
    lst_path.write_text(result.listing + "\n", encoding=ENCODING)
    # Formato de bloques: menos líneas que pegar en el monitor serial, y cada
    # una cabe holgada en el buffer de recepción de 64 bytes del Arduino.
    load_path.write_text(result.load_script_bloques + "\n", encoding=ENCODING)

    emitted = sum(end - start + 1 for start, end in result.spans)
    spans_text = ", ".join(f"0x{start:02X}–0x{end:02X}" for start, end in result.spans)
    print(f"{emitted} bytes emitidos ({spans_text})")
    print(f"  {bin_path}")
    print(f"  {lst_path}")
    print(f"  {load_path}")
    _print_warnings(result)

    if args.run:
        _run(result)
    return 0


def _print_warnings(result) -> None:
    for warning in result.warnings:
        print(f"aviso: {warning}", file=sys.stderr)


def _run(result) -> None:
    """Assemble-then-execute on the B.1 simulator — the cheapest possible
    end-to-end demo."""
    from sim.cpu import CPU
    from sim.exceptions import CycleLimitExceeded
    from sim.memory import Memory

    memory = Memory()
    memory.load_bytes(result.binary)
    cpu = CPU(memory)
    try:
        cpu.run()
    except CycleLimitExceeded as error:
        print(f"ejecución abortada: {error}", file=sys.stderr)
        return

    print(f"\nSalida (OUT): {cpu.output}")
    print(
        f"Estado final: A=0x{cpu.a:02X}  B=0x{cpu.b:02X}  "
        f"PC=0x{cpu.pc:02X}  Z={cpu.z}  C={cpu.c}"
    )


if __name__ == "__main__":
    sys.exit(main())
