"""Depurador — panel frontal en Python/Tkinter para el microprocesador de 8 bits.

El paquete se divide deliberadamente en piezas puras (probables sin pantalla)
y una única pieza que sí necesita Tkinter:

- ``protocolo``          formato/parseo del protocolo serial (espejo de
                         ``firmware/unidad_control/formato.cpp`` y ``consola.cpp``)
- ``formato_numerico``   un byte en binario/hexadecimal/con signo/sin signo
- ``desensamblador``     bytes de memoria -> mnemónico + operando (vía ``isa``)
- ``cargador``           lectura de un archivo ``.load`` generado por ``python -m asm``
- ``isa``                tabla de opcodes del ISA
- ``pruebas_rapidas``    pasos dictados -> ``.asm`` + bytes
- ``transporte``         Transporte serie real con pyserial
- ``gui``                la ventana Tkinter (solo cableado, sin lógica propia)

Importar ``depurador`` no arrastra Tkinter ni pyserial: ``gui`` y
``transporte.TransporteSerial`` los importan de forma perezosa.
"""

__all__ = [
    "cargador",
    "desensamblador",
    "formato_numerico",
    "isa",
    "protocolo",
    "pruebas_rapidas",
    "transporte",
]
