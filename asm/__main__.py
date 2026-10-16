"""
python -m asm programa.asm

Escribe tres archivos junto al fuente (o en la carpeta de -o):
  .bin   256 bytes crudos, la imagen de memoria
  .lst   listado de ensamblado + tabla de símbolos, para la documentación
  .load  comandos LOADB <dir> <bytes...> para el monitor serie del Arduino (B.3)
"""

import argparse
import sys
from pathlib import Path

from .assembler import assemble
from .errors import AssemblyFailed

ENCODING = "utf-8"


def build_parser() -> argparse.ArgumentParser:
    """Define los argumentos que acepta el comando."""
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
    """La consola de Windows usa cp1252 por defecto, que estropea los
    acentos y guiones de nuestros mensajes. Desde Python 3.7 se puede
    cambiar la codificación de los streams."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding=ENCODING)
            except (OSError, ValueError):
                pass   # si no se puede, se sigue con la codificación que haya


def main(argv=None) -> int:
    """Punto de entrada. Devuelve el código de salida: 0 = bien, 1 = error."""
    _force_utf8_console()
    args = build_parser().parse_args(argv)
    source_path = Path(args.source)

    # 1. Leer el fuente.
    try:
        source_text = source_path.read_text(encoding=ENCODING)
    except OSError as error:
        print(f"no se pudo leer '{source_path}': {error}", file=sys.stderr)
        return 1

    # 2. Ensamblar. Si hay errores se imprimen todos juntos y se termina.
    try:
        result = assemble(source_text)
    except AssemblyFailed as failure:
        print(str(failure), file=sys.stderr)
        return 1

    # 3a. Modo --listing-only: mostrar el listado y no escribir archivos.
    if args.listing_only:
        print(result.listing)
        _print_warnings(result)
        if args.run:
            _run(result)
        return 0

    # 3b. Modo normal: escribir .bin, .lst y .load.
    output_dir = Path(args.output_dir) if args.output_dir else source_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = source_path.stem   # nombre del fuente sin extensión

    bin_path = output_dir / f"{stem}.bin"
    lst_path = output_dir / f"{stem}.lst"
    load_path = output_dir / f"{stem}.load"

    bin_path.write_bytes(result.binary)
    lst_path.write_text(result.listing + "\n", encoding=ENCODING)
    # Formato de bloques: menos líneas que pegar en el monitor serial, y cada
    # una cabe holgada en el buffer de recepción de 64 bytes del Arduino.
    load_path.write_text(result.load_script_bloques + "\n", encoding=ENCODING)

    # Resumen: cuántos bytes se emitieron y en qué tramos de memoria.
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
    """Los avisos van a stderr para no mezclarse con el listado."""
    for warning in result.warnings:
        print(f"aviso: {warning}", file=sys.stderr)


def _run(result) -> None:
    """Ensamblar y luego ejecutar en el simulador de B.1: la demo de punta a
    punta más simple posible."""
    # Imports aquí: el simulador solo se carga si se pidió --run.
    from sim.cpu import CPU
    from sim.exceptions import CycleLimitExceeded
    from sim.memory import Memory

    # Cargar la imagen de 256 bytes en una memoria nueva y ejecutar.
    memory = Memory()
    memory.load_bytes(result.binary)
    cpu = CPU(memory)
    try:
        cpu.run()
    except CycleLimitExceeded as error:
        # Protección contra bucles infinitos (programa sin HLT, por ejemplo).
        print(f"ejecución abortada: {error}", file=sys.stderr)
        return

    print(f"\nSalida (OUT): {cpu.output}")
    print(
        f"Estado final: A=0x{cpu.a:02X}  B=0x{cpu.b:02X}  "
        f"PC=0x{cpu.pc:02X}  Z={cpu.z}  C={cpu.c}"
    )


if __name__ == "__main__":
    sys.exit(main())
