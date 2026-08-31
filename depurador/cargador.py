"""Lectura de un archivo ``.load`` generado por ``python -m asm``.

El ``.load`` es un guion de comandos seriales (``LOADB 0x00 0x30 0x00 ...``),
uno por línea. El depurador lo manda línea por línea ESPERANDO la confirmación
``OK``/``ERR`` de cada una antes de mandar la siguiente: el buffer de recepción
del Arduino son 64 bytes y pegar el archivo entero de golpe perdería comandos
EN SILENCIO (ver el comentario de ``firmware/microprocesador/consola.h``).

Módulo puro: solo lee un archivo y devuelve texto. No abre puertos.
"""

import io
import os
from typing import List

CODIFICACION = "utf-8"


def leer_lineas(ruta: str) -> List[str]:
    """Las líneas ejecutables de un ``.load``, sin vacías ni comentarios.

    Se descartan las líneas en blanco (no son comandos: el firmware las ignora,
    pero mandarlas es tráfico inútil) y las que empiezan por ``;`` o ``#``, por
    si alguien anota el archivo a mano.
    """
    with io.open(ruta, "r", encoding=CODIFICACION) as archivo:
        return lineas_de_texto(archivo.read())


def lineas_de_texto(texto: str) -> List[str]:
    """Igual que ``leer_lineas`` pero sobre un texto ya en memoria."""
    lineas = []
    for cruda in texto.splitlines():
        linea = cruda.strip()
        if not linea or linea.startswith(";") or linea.startswith("#"):
            continue
        lineas.append(linea)
    return lineas


def ruta_load_de(ruta_asm: str) -> str:
    """``programas/referencia.asm`` -> ``programas/referencia.load``."""
    raiz, _ = os.path.splitext(ruta_asm)
    return raiz + ".load"
