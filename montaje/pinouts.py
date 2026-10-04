"""Pinouts DIP de los integrados del montaje, vista superior.

Fuentes (Texas Instruments):
  SN74LS181  SDLS136 (escaneo, "DW OR N PACKAGE (TOP VIEW)").  Encapsulado N
             de 24 pines ANCHO (600 mil): confirmado además en físico por el
             usuario (sus patas quedan a 3 agujeros + el canal central).
  SN74LS273  SDLS090, texto del diagrama de pines.
  SN74LS157  pinout verificado contra el símbolo de Proteus en la guía
             "Mux 74LS157" (E = pin 15, igual que G del datasheet).
  SN74LS240  SDLS144D (mismo datasheet que el 244), sección 5 "Pin Configuration
             and Functions". Mismo pinout que el 244; las salidas Y invierten.
  SN74LS161A SDLS060, "D, J OR N PACKAGE (TOP VIEW)". Las entradas de datos
             A-D del datasheet se llaman P0-P3 aquí y QA-QD, Q0-Q3. CLR y
             LOAD son activos en bajo (/CLR y /LOAD en el datasheet).

Convención de datos: el proyecto usa lógica activa en alto en A/B/F del 181
(la tabla de control de contexto_proyecto.md A.3 ya está escrita así), de modo
que Ā0 del datasheet se llama A0 aquí.

⚠ proyecto_microprocesador_8bits.md §6.5 tenía 22/23 cruzados (22=A1,
23=B1). El datasheet dice 23 = A1 y 22 = B1, que es lo que usó el cableado de
Proteus que funcionó. Aquí manda el datasheet.

Tipos de pin:
  'in'   entrada: debe pertenecer a una red (nunca flotante)
  'out'  salida: puede quedar sin usar
  'oc'   salida de colector abierto: puede quedar sin usar
  'vcc' / 'gnd'  alimentación
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Pinout:
    nombre: str
    pines: int
    ancho: int            # separación entre filas de patas, en pasos de 0.1"
    senales: dict         # número de pin -> (señal, tipo)

    def tipo(self, pin):
        return self.senales[pin][1]

    def senal(self, pin):
        return self.senales[pin][0]

    def pin_de(self, senal):
        for p, (s, _) in self.senales.items():
            if s == senal:
                return p
        raise KeyError(f'{self.nombre} no tiene la señal {senal}')


LS181 = Pinout('74LS181', 24, 6, {
    1: ('B0', 'in'),   2: ('A0', 'in'),   3: ('S3', 'in'),   4: ('S2', 'in'),
    5: ('S1', 'in'),   6: ('S0', 'in'),   7: ('CN', 'in'),   8: ('M', 'in'),
    9: ('F0', 'out'), 10: ('F1', 'out'), 11: ('F2', 'out'), 12: ('GND', 'gnd'),
    13: ('F3', 'out'), 14: ('A=B', 'oc'), 15: ('P', 'out'), 16: ('CN4', 'out'),
    17: ('G', 'out'),  18: ('B3', 'in'),  19: ('A3', 'in'),  20: ('B2', 'in'),
    21: ('A2', 'in'),  22: ('B1', 'in'),  23: ('A1', 'in'),  24: ('VCC', 'vcc'),
})

LS273 = Pinout('74LS273', 20, 3, {
    1: ('CLR', 'in'),  2: ('Q0', 'out'),  3: ('D0', 'in'),   4: ('D1', 'in'),
    5: ('Q1', 'out'),  6: ('Q2', 'out'),  7: ('D2', 'in'),   8: ('D3', 'in'),
    9: ('Q3', 'out'), 10: ('GND', 'gnd'), 11: ('CLK', 'in'), 12: ('Q4', 'out'),
    13: ('D4', 'in'), 14: ('D5', 'in'),  15: ('Q5', 'out'), 16: ('Q6', 'out'),
    17: ('D6', 'in'), 18: ('D7', 'in'),  19: ('Q7', 'out'), 20: ('VCC', 'vcc'),
})

LS157 = Pinout('74LS157', 16, 3, {
    1: ('SEL', 'in'),  2: ('1A', 'in'),   3: ('1B', 'in'),   4: ('1Y', 'out'),
    5: ('2A', 'in'),   6: ('2B', 'in'),   7: ('2Y', 'out'),  8: ('GND', 'gnd'),
    9: ('3Y', 'out'), 10: ('3B', 'in'),  11: ('3A', 'in'),  12: ('4Y', 'out'),
    13: ('4B', 'in'), 14: ('4A', 'in'),  15: ('G', 'in'),   16: ('VCC', 'vcc'),
})

LS240 = Pinout('74LS240', 20, 3, {
    1: ('1G', 'in'),   2: ('1A1', 'in'),  3: ('2Y4', 'out'), 4: ('1A2', 'in'),
    5: ('2Y3', 'out'), 6: ('1A3', 'in'),  7: ('2Y2', 'out'), 8: ('1A4', 'in'),
    9: ('2Y1', 'out'), 10: ('GND', 'gnd'), 11: ('2A1', 'in'), 12: ('1Y4', 'out'),
    13: ('2A2', 'in'), 14: ('1Y3', 'out'), 15: ('2A3', 'in'), 16: ('1Y2', 'out'),
    17: ('2A4', 'in'), 18: ('1Y1', 'out'), 19: ('2G', 'in'),  20: ('VCC', 'vcc'),
})

LS161 = Pinout('74LS161', 16, 3, {
    1: ('CLR', 'in'),  2: ('CLK', 'in'),   3: ('P0', 'in'),   4: ('P1', 'in'),
    5: ('P2', 'in'),   6: ('P3', 'in'),   7: ('ENP', 'in'),  8: ('GND', 'gnd'),
    9: ('LOAD', 'in'), 10: ('ENT', 'in'), 11: ('Q3', 'out'), 12: ('Q2', 'out'),
    13: ('Q1', 'out'), 14: ('Q0', 'out'), 15: ('RCO', 'out'), 16: ('VCC', 'vcc'),
})

# Bit de salida de cada canal del 240: bits 0-3 por la mitad 1, 4-7 por la 2.
CANAL_240 = {0: ('1A1', '1Y1'), 1: ('1A2', '1Y2'), 2: ('1A3', '1Y3'), 3: ('1A4', '1Y4'),
             4: ('2A1', '2Y1'), 5: ('2A2', '2Y2'), 6: ('2A3', '2Y3'), 7: ('2A4', '2Y4')}

# Canal del 157 para cada bit dentro de su nibble.
CANAL_157 = {0: '1', 1: '2', 2: '3', 3: '4'}
