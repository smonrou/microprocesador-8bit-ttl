"""Fixtures compartidas — compilación de los binarios nativos del firmware.

El firmware es C++; para probarlo sin el Arduino se compila el núcleo junto
al HAL falso y se ejecuta en la PC. No hay `make` en esta máquina, así que el
build lo dirige pytest llamando a g++ directamente.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
SKETCH = RAIZ / "firmware" / "microprocesador"
PRUEBAS = RAIZ / "firmware" / "pruebas"
STUB = PRUEBAS / "stub_arduino"

BANDERAS = ["-std=c++11", "-Wall", "-Wextra", "-O1"]


def _compilador():
    return shutil.which("g++") or shutil.which("clang++")


@pytest.fixture(scope="session")
def compilar(tmp_path_factory):
    """Devuelve compilar(nombre, fuentes) -> ruta del ejecutable.

    Compila una vez por sesión y cachea. Si no hay compilador, salta las
    pruebas con un mensaje claro en vez de fallar.
    """
    compilador = _compilador()
    if compilador is None:
        pytest.skip("no hay g++ ni clang++ en el PATH; se omiten las "
                    "pruebas nativas del firmware")

    destino = tmp_path_factory.mktemp("firmware")
    cache = {}

    def _compilar(nombre, fuentes, extra=()):
        if nombre in cache:
            return cache[nombre]

        salida = destino / (nombre + (".exe" if os.name == "nt" else ""))
        orden = [compilador, *BANDERAS, *extra, "-o", str(salida)]
        orden += [str(fuente) for fuente in fuentes]

        proceso = subprocess.run(orden, capture_output=True, text=True)
        if proceso.returncode != 0:
            pytest.fail(
                f"falló la compilación de '{nombre}':\n"
                f"{' '.join(orden)}\n\n{proceso.stderr}"
            )

        cache[nombre] = salida
        return salida

    return _compilar


@pytest.fixture(scope="session")
def binario_prueba_alu(compilar):
    """Barrido exhaustivo del 74LS181 emulado."""
    return compilar("prueba_alu", [
        SKETCH / "isa.cpp",
        PRUEBAS / "hal_falso.cpp",
        PRUEBAS / "prueba_alu.cpp",
    ])


@pytest.fixture(scope="session")
def binario_arnes(compilar):
    """Núcleo del firmware + HAL falso, ejecutable en la PC."""
    return compilar("arnes", [
        SKETCH / "isa.cpp",
        SKETCH / "nucleo.cpp",
        SKETCH / "formato.cpp",
        PRUEBAS / "hal_falso.cpp",
        PRUEBAS / "arnes.cpp",
    ])


@pytest.fixture(scope="session")
def sketch_compilado(compilar):
    """El sketch entero (incluidos los archivos que solo viven en el Arduino)
    compilado contra un stub de Arduino.h.

    No emula el hardware: sirve para cazar erratas, includes olvidados y
    firmas equivocadas en hal_arduino.cpp, display.cpp, consola.cpp y el
    .ino, que de otro modo quedarían sin verificar hasta tener la placa.
    """
    return compilar(
        "sketch",
        [
            SKETCH / "isa.cpp",
            SKETCH / "nucleo.cpp",
            SKETCH / "formato.cpp",
            SKETCH / "hal_arduino.cpp",
            SKETCH / "display.cpp",
            SKETCH / "consola.cpp",
            SKETCH / "microprocesador.ino",
            STUB / "stub_arduino.cpp",
            STUB / "main_stub.cpp",
        ],
        extra=["-DARDUINO=100", "-I", str(STUB), "-x", "c++"],
    )


@pytest.fixture(scope="session")
def ejecutar_arnes(binario_arnes, tmp_path_factory):
    """Devuelve ejecutar(binary, *args) -> salida parseada del arnés."""
    carpeta = tmp_path_factory.mktemp("imagenes")
    contador = {"n": 0}

    def _ejecutar(imagen, *args):
        contador["n"] += 1
        ruta = carpeta / f"img{contador['n']}.bin"
        ruta.write_bytes(bytes(imagen))

        proceso = subprocess.run(
            [str(binario_arnes), str(ruta), *args],
            capture_output=True, text=True,
            # El firmware emite UTF-8 (el bloque A.9 lleva ─ y →). Sin esto,
            # Python decodificaría con cp1252 en Windows y lo destrozaría.
            encoding="utf-8", errors="replace",
        )
        assert proceso.returncode == 0, (
            f"el arnés falló (código {proceso.returncode}):\n{proceso.stderr}"
        )
        return _parsear(proceso.stdout)

    return _ejecutar


def _parsear(texto):
    """Convierte la salida del arnés en un dict manejable."""
    instrucciones = []
    salidas = []
    pasos = []
    bloques = []
    claves = []
    memoria = None
    fin = {}

    bloque_actual = None
    for linea in texto.splitlines():
        if linea == "<<<BLOQUE":
            bloque_actual = []
            continue
        if linea == ">>>BLOQUE":
            bloques.append("\n".join(bloque_actual))
            bloque_actual = None
            continue
        if bloque_actual is not None:
            bloque_actual.append(linea)
            continue
        if linea.startswith("#"):
            claves.append(linea)
            continue

        if linea.startswith("INSTR "):
            instrucciones.append(_campos(linea[len("INSTR "):]))
        elif linea.startswith("OUT "):
            salidas.append(int(_campos(linea[len("OUT "):])["valor"], 0))
        elif linea.startswith("PASO "):
            pasos.append(linea.split()[1])
        elif linea.startswith("MEM "):
            memoria = [int(valor, 16) for valor in linea.split()[1:]]
        elif linea.startswith("FIN "):
            fin = _campos(linea[len("FIN "):])

    return {
        "instrucciones": instrucciones,
        "salidas": salidas,
        "pasos": pasos,
        "bloques": bloques,
        "claves": claves,
        "memoria": memoria,
        "detenido": fin.get("detenido") == "1",
        "total": int(fin.get("instrucciones", 0)),
        "microciclos": int(fin.get("microciclos", 0)),
        "limite": fin.get("limite") == "1",
        "pulsos_pc": int(fin.get("pulsos_pc", 0)),
        "cargas_pc": int(fin.get("cargas_pc", 0)),
    }


def _campos(texto):
    """`a=1 b=2 op=LDI A` -> {'a':'1','b':'2','op':'LDI A'}."""
    campos = {}
    clave = None
    for token in texto.split():
        if "=" in token:
            clave, valor = token.split("=", 1)
            campos[clave] = valor
        elif clave is not None:
            campos[clave] += " " + token   # nemónicos de dos palabras
    return campos
