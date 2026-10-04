"""Genera, a partir de netlist.py, los dibujos SVG y los datos por fase.

    python -m montaje.generar          # escribe montaje/salida/

Salida:
  fase{N}.svg           vista completa (4 protoboards + Mega); la fase N a
                        color, lo de fases anteriores atenuado, lo de pruebas
                        en magenta punteado. Cada cable de la fase lleva su
                        número, el mismo de las tablas.
  fase{N}_{CHIP}.svg    acercamiento a cada chip que se coloca en la fase,
                        con el destino de cada cable escrito junto al agujero.
  datos.json            pasos, tablas y compras por fase (para las guías).
"""

import html
import json
import math
import os
from collections import defaultdict

from montaje.netlist import (MONTAJE, FASES, COLORES, COLOR_TEMPORAL, PROTOBOARDS,
                             X_RIEL, FILAS, COLS_SUP, Agujero, PinMega, FIN)

P = 12                     # píxeles por paso de 0.1" (2.54 mm)
MM = 2.54                  # mm por paso
ALTO_BB = 21.6             # alto de una protoboard de 830 en pasos (≈55 mm)
ANCHO_BB = 65.0            # ancho en pasos (≈165 mm)
Y_COL = {'j': 4.8, 'i': 5.8, 'h': 6.8, 'g': 7.8, 'f': 8.8,
         'e': 11.8, 'd': 12.8, 'c': 13.8, 'b': 14.8, 'a': 15.8}
Y_RIEL = {'T+': 1.6, 'T-': 2.6, 'B-': 18.8, 'B+': 19.8}
MEGA_W, MEGA_H = 40.0, 21.0
SEP_MEGA = 4.0
OX_BB = MEGA_W + SEP_MEGA + 1.5          # borde izquierdo de las protoboards
OY_MEGA = 2 * ALTO_BB - MEGA_H / 2       # Mega centrado entre BB2 y BB3
MARGEN = 3.0

# Bandas de color de cada resistencia del montaje, por valor.
BANDAS = {'220': ['#d62828', '#d62828', '#6b3d1a'],    # rojo rojo café
          '330': ['#f07d19', '#f07d19', '#6b3d1a'],    # naranja naranja café
          '1 k': ['#6b3d1a', '#1d1d1d', '#d62828']}    # café negro rojo

SALIDA = os.path.join(os.path.dirname(__file__), 'salida')


# ── Geometría ───────────────────────────────────────────────────────────

def pos_mega(pin):
    """Posición (en pasos, coordenadas globales) de un pin del Mega.

    Mega en orientación estándar (USB a la izquierda). Cabecera doble 22-53 en
    el extremo derecho: pares en la columna interna, impares en la externa;
    arriba 5V/5V y abajo GND/GND. Cabecera digital 0-7 en el borde superior.
    Cabecera analógica A0-A15 en el borde inferior, de izquierda a derecha."""
    x0, y0 = MARGEN, OY_MEGA
    if pin == 'GND':
        return (x0 + MEGA_W - 2.2, y0 + 19.0)
    if pin.startswith('A'):
        n = int(pin[1:])
        return (x0 + 17.0 + n + (1 if n >= 8 else 0), y0 + MEGA_H - 1.2)
    n = int(pin)
    if n >= 22:
        col = MEGA_W - 2.2 if n % 2 else MEGA_W - 3.2
        fila = 2.0 + 1 + (n - 22) // 2
        return (x0 + col, y0 + fila)
    return (x0 + 29.0 - n, y0 + 1.2)          # 7 a la izquierda ... 0 a la derecha


def pos(ag):
    if isinstance(ag, PinMega):
        return pos_mega(ag.pin)
    k = PROTOBOARDS.index(ag.bb)
    x = OX_BB + ag.fila
    y = MARGEN + k * ALTO_BB + (Y_RIEL[ag.riel] if ag.riel else Y_COL[ag.col])
    return (x, y)


def largo_cm(c):
    (x1, y1), (x2, y2) = pos(c.a), pos(c.b)
    mm = (abs(x1 - x2) + abs(y1 - y2)) * MM
    extra = 20 + (25 if isinstance(c.a, PinMega) or isinstance(c.b, PinMega) else 0)
    return math.ceil((mm + extra) / 5) * 0.5          # redondeo hacia arriba a 0.5 cm


# ── SVG ─────────────────────────────────────────────────────────────────

def _px(v):
    return f'{v * P:.1f}'


class Svg:
    def __init__(self):
        self.partes = []

    def add(self, s):
        self.partes.append(s)


def _protoboard(svg, k, bb, pid='aguj'):
    oy = MARGEN + k * ALTO_BB
    ox = OX_BB
    svg.add(f'<g class="bb"><rect x="{_px(ox)}" y="{_px(oy + 0.15)}" width="{_px(ANCHO_BB)}" '
            f'height="{_px(ALTO_BB - 0.3)}" rx="6" fill="#f3f1ea" stroke="#c9c3b3"/>')
    # canal central
    svg.add(f'<rect x="{_px(ox + 0.5)}" y="{_px(oy + 9.6)}" width="{_px(ANCHO_BB - 1)}" '
            f'height="{_px(1.4)}" fill="#e2ddd0"/>')
    # rayas de riel
    for r, y in Y_RIEL.items():
        color = '#d62828' if '+' in r else '#1f5fd1'
        dy = -0.55 if r in ('T+', 'B-') else 0.55
        if r in ('T+', 'B+'):
            dy = -0.55 if r == 'T+' else 0.55
        else:
            dy = 0.55 if r == 'T-' else -0.55
        svg.add(f'<line x1="{_px(ox + 1.5)}" x2="{_px(ox + ANCHO_BB - 1.5)}" y1="{_px(oy + y + dy)}" '
                f'y2="{_px(oy + y + dy)}" stroke="{color}" stroke-width="1.2" opacity=".75"/>')
        svg.add(f'<text x="{_px(ox + 0.55)}" y="{_px(oy + y + 0.3)}" font-size="9" fill="{color}" '
                f'font-weight="700">{"+" if "+" in r else "−"}</text>')
        for x in X_RIEL:
            svg.add(f'<rect x="{_px(ox + x - 0.17)}" y="{_px(oy + y - 0.17)}" width="4" height="4" '
                    f'fill="#4a4740" rx="0.6"/>')
    # agujeros de las tiras: patrón
    svg.add(f'<rect x="{_px(ox + 0.5)}" y="{_px(oy + Y_COL["j"] - 0.5)}" width="{_px(FILAS)}" '
            f'height="{_px(5)}" fill="url(#{pid})"/>')
    svg.add(f'<rect x="{_px(ox + 0.5)}" y="{_px(oy + Y_COL["e"] - 0.5)}" width="{_px(FILAS)}" '
            f'height="{_px(5)}" fill="url(#{pid})"/>')
    # números de fila y letras
    for f in range(1, FILAS + 1):
        if f == 1 or f % 5 == 0:
            for y in (Y_COL['j'] - 0.95, Y_COL['a'] + 1.25):
                svg.add(f'<text x="{_px(ox + f)}" y="{_px(oy + y)}" font-size="7.5" '
                        f'text-anchor="middle" fill="#8b8574">{f}</text>')
    for c, y in Y_COL.items():
        for x in (ox + 0.05, ox + ANCHO_BB - 0.9):
            svg.add(f'<text x="{_px(x + 0.4)}" y="{_px(oy + y + 0.28)}" font-size="7.5" '
                    f'text-anchor="middle" fill="#8b8574">{c}</text>')
    svg.add(f'<text x="{_px(ox + ANCHO_BB / 2)}" y="{_px(oy + 10.55)}" font-size="11" '
            f'text-anchor="middle" fill="#9a937f" font-weight="700" letter-spacing="3">{bb}</text></g>')


def _mega(svg, pines_usados):
    x0, y0 = MARGEN, OY_MEGA
    svg.add(f'<g class="mega"><rect x="{_px(x0)}" y="{_px(y0)}" width="{_px(MEGA_W)}" height="{_px(MEGA_H)}" '
            f'rx="8" fill="#1f6f8b" stroke="#134556" stroke-width="2"/>')
    svg.add(f'<rect x="{_px(x0 - 1.2)}" y="{_px(y0 + 3)}" width="{_px(6)}" height="{_px(4.8)}" fill="#c9c9c9" stroke="#777"/>'
            f'<text x="{_px(x0 + 1.8)}" y="{_px(y0 + 5.8)}" font-size="9" text-anchor="middle">USB</text>')
    svg.add(f'<text x="{_px(x0 + 17)}" y="{_px(y0 + 11)}" font-size="20" fill="#e8f4f8" text-anchor="middle" '
            f'font-weight="700">ARDUINO MEGA 2560</text>')
    svg.add(f'<text x="{_px(x0 + 17)}" y="{_px(y0 + 13)}" font-size="10" fill="#bfe0ea" text-anchor="middle">'
            f'alimentado por USB · su pin 5V NO se conecta a la protoboard</text>')
    # cabecera doble
    for n in range(22, 54):
        x, y = pos_mega(str(n))
        usado = str(n) in pines_usados
        svg.add(f'<rect x="{_px(x - 0.4)}" y="{_px(y - 0.4)}" width="{_px(0.8)}" height="{_px(0.8)}" '
                f'fill="{"#ffd166" if usado else "#111"}" stroke="#000" stroke-width=".5"/>')
        tx = x + (0.75 if n % 2 else -0.75)
        svg.add(f'<text x="{_px(tx)}" y="{_px(y + 0.3)}" font-size="7.5" fill="#e8f4f8" '
                f'text-anchor="{"start" if n % 2 else "end"}">{n}</text>')
    for etiqueta, dy in (('5V', 2.0), ('GND', 19.0)):
        for col in (MEGA_W - 3.2, MEGA_W - 2.2):
            x, y = x0 + col, y0 + dy
            usado = etiqueta == 'GND' and col == MEGA_W - 2.2 and 'GND' in pines_usados
            svg.add(f'<rect x="{_px(x - 0.4)}" y="{_px(y - 0.4)}" width="{_px(0.8)}" height="{_px(0.8)}" '
                    f'fill="{"#ffd166" if usado else "#111"}"/>')
        svg.add(f'<text x="{_px(x0 + MEGA_W - 4.1)}" y="{_px(y0 + dy + 0.3)}" font-size="7.5" fill="#e8f4f8" '
                f'text-anchor="end">{etiqueta}</text>')
    for n in range(0, 8):
        x, y = pos_mega(str(n))
        usado = str(n) in pines_usados
        svg.add(f'<rect x="{_px(x - 0.4)}" y="{_px(y - 0.4)}" width="{_px(0.8)}" height="{_px(0.8)}" '
                f'fill="{"#ffd166" if usado else "#111"}"/>'
                f'<text x="{_px(x)}" y="{_px(y + 1.5)}" font-size="7.5" fill="#e8f4f8" text-anchor="middle">{n}</text>')
    svg.add(f'<text x="{_px(x0 + 25.5)}" y="{_px(y0 + 3.4)}" font-size="8" fill="#bfe0ea" '
            f'text-anchor="middle">DIGITAL (PWM)</text>')
    for n in range(0, 16):
        x, y = pos_mega(f'A{n}')
        usado = f'A{n}' in pines_usados
        svg.add(f'<rect x="{_px(x - 0.4)}" y="{_px(y - 0.4)}" width="{_px(0.8)}" height="{_px(0.8)}" '
                f'fill="{"#ffd166" if usado else "#111"}"/>'
                f'<text x="{_px(x)}" y="{_px(y - 0.9)}" font-size="7" fill="#e8f4f8" text-anchor="middle">{n}</text>')
    svg.add(f'<text x="{_px(x0 + 25.5)}" y="{_px(y0 + MEGA_H - 3.4)}" font-size="8" fill="#bfe0ea" '
            f'text-anchor="middle">ANALOG IN A0–A15 · A8–A15 = PORTK: lectura del PC</text></g>')


def _chip(svg, c, tenue):
    x1, y_sup = pos(c.agujero(c.pinout.pines))
    x2, y_inf = pos(c.agujero(c.mitad))
    op = ' opacity=".45"' if tenue else ''
    svg.add(f'<g class="chip"{op}>')
    svg.add(f'<rect x="{_px(x1 - 0.55)}" y="{_px(y_sup + 0.35)}" width="{_px(x2 - x1 + 1.1)}" '
            f'height="{_px(y_inf - y_sup - 0.7)}" rx="3" fill="#26272b"/>')
    ym = (y_sup + y_inf) / 2
    svg.add(f'<path d="M{_px(x1 - 0.55)} {_px(ym - 0.55)} a{_px(0.55)} {_px(0.55)} 0 0 1 0 {_px(1.1)}" fill="#55565c"/>')
    for p in range(1, c.pinout.pines + 1):
        x, y = pos(c.agujero(p))
        svg.add(f'<rect x="{_px(x - 0.28)}" y="{_px(y - 0.28 + (0.2 if p <= c.mitad else -0.2))}" '
                f'width="{_px(0.56)}" height="{_px(0.56)}" fill="#c8c8c8"/>')
    svg.add(f'<circle cx="{_px(x1 + 0.1)}" cy="{_px(y_inf - 0.95)}" r="2.6" fill="#d9d9d9"/>')
    svg.add(f'<text x="{_px((x1 + x2) / 2)}" y="{_px(ym - 0.2)}" font-size="{11 if c.mitad > 8 else 9.5}" '
            f'fill="#f5f5f5" text-anchor="middle" font-weight="700">{c.nombre}</text>')
    svg.add(f'<text x="{_px((x1 + x2) / 2)}" y="{_px(ym + 0.85)}" font-size="8.5" fill="#bdbdbd" '
            f'text-anchor="middle">{c.pinout.nombre}</text></g>')


def _pieza(svg, p, tenue, temporal):
    op = ' opacity=".45"' if tenue else ''
    pts = [pos(a) for a in p.patas]
    svg.add(f'<g class="pieza"{op}>')
    if p.tipo in ('cap', 'electrolitico'):
        (xa, ya), (xb, yb) = pts
        for (x, y) in pts:
            svg.add(f'<line x1="{_px(x)}" y1="{_px(y)}" x2="{_px((xa + xb) / 2)}" y2="{_px((ya + yb) / 2)}" '
                    f'stroke="#999" stroke-width="1.4"/>')
        if p.tipo == 'cap':
            svg.add(f'<ellipse cx="{_px((xa + xb) / 2 + 0.9)}" cy="{_px((ya + yb) / 2)}" rx="7" ry="6" '
                    f'fill="#e3a72f" stroke="#9c6b10"/>')
        else:
            svg.add(f'<circle cx="{_px((xa + xb) / 2 + 1.4)}" cy="{_px((ya + yb) / 2)}" r="10" fill="#2a4d8f" stroke="#10254d"/>'
                    f'<text x="{_px((xa + xb) / 2 + 1.4)}" y="{_px((ya + yb) / 2 + 0.25)}" font-size="7" fill="#fff" '
                    f'text-anchor="middle">100µF</text>')
    elif p.tipo == 'resistencia':
        (xa, ya), (xb, yb) = pts
        svg.add(f'<line x1="{_px(xa)}" y1="{_px(ya)}" x2="{_px(xb)}" y2="{_px(yb)}" stroke="#9a9a9a" stroke-width="1.6"/>')
        mx, my = (xa + xb) / 2, (ya + yb) / 2
        ang = math.degrees(math.atan2(yb - ya, xb - xa))
        bandas = BANDAS.get(next((v for v in BANDAS if v in p.valor), ''), BANDAS['1 k'])
        svg.add(f'<g transform="translate({_px(mx)} {_px(my)}) rotate({ang:.1f})">'
                f'<rect x="-11" y="-4" width="22" height="8" rx="3.5" fill="#d8c29a" stroke="#8d7a55" stroke-width=".8"/>'
                + ''.join(f'<rect x="{-7 + 4.5 * i}" y="-4" width="2.2" height="8" fill="{b}"/>' for i, b in enumerate(bandas))
                + '</g>')
    elif p.tipo == 'led':
        (xa, ya), (xb, yb) = pts
        svg.add(f'<circle cx="{_px((xa + xb) / 2)}" cy="{_px((ya + yb) / 2 - 1.1)}" r="7.5" fill="#ff4d4d" '
                f'stroke="#8e1b1b" stroke-width="1.2" opacity=".92"/>'
                f'<line x1="{_px(xa)}" y1="{_px(ya)}" x2="{_px(xa)}" y2="{_px(ya - 0.7)}" stroke="#777" stroke-width="1.6"/>'
                f'<line x1="{_px(xb)}" y1="{_px(yb)}" x2="{_px(xb)}" y2="{_px(yb - 0.7)}" stroke="#777" stroke-width="1.6"/>'
                f'<text x="{_px(xa - 0.1)}" y="{_px(ya + 0.95)}" font-size="7" fill="#8e1b1b" text-anchor="middle">+</text>')
    elif p.tipo == 'dip':
        xs = [x for x, _ in pts]
        ys = [y for _, y in pts]
        svg.add(f'<rect x="{_px(min(xs) - 0.5)}" y="{_px(min(ys) + 0.4)}" width="{_px(max(xs) - min(xs) + 1)}" '
                f'height="{_px(max(ys) - min(ys) - 0.8)}" rx="2" fill="#c0392b"/>')
        for x in sorted(set(xs)):
            svg.add(f'<rect x="{_px(x - 0.3)}" y="{_px(min(ys) + 1.0)}" width="{_px(0.6)}" height="{_px(1.0)}" fill="#fff"/>')
        svg.add(f'<text x="{_px(min(xs))}" y="{_px(max(ys) - 0.7)}" font-size="7" fill="#fff">ON ↑ 1</text>')
    elif p.tipo == 'pulsador':
        xs = [x for x, _ in pts]
        ys = [y for _, y in pts]
        svg.add(f'<rect x="{_px(min(xs) - 0.3)}" y="{_px(min(ys) + 0.4)}" width="{_px(max(xs) - min(xs) + 0.6)}" '
                f'height="{_px(max(ys) - min(ys) - 0.8)}" rx="2" fill="#333"/>'
                f'<circle cx="{_px(sum(xs) / 4)}" cy="{_px(sum(ys) / 4)}" r="8" fill="#555" stroke="#111"/>')
    elif p.tipo == 'fuente':
        (xa, ya), (xb, yb) = pts
        for (x, y), col in ((pts[0], '#d62828'), (pts[1], '#1d1d1d')):
            svg.add(f'<path d="M{_px(x)} {_px(y)} C {_px(x)} {_px(y + 3)}, {_px(x - 2)} {_px(y + 4)}, {_px(x - 3)} {_px(y + 5.5)}" '
                    f'stroke="{col}" stroke-width="3.2" fill="none"/>')
        svg.add(f'<rect x="{_px(xa - 7)}" y="{_px(ya + 5)}" width="{_px(6)}" height="{_px(2.2)}" rx="2" fill="#2f7d32"/>'
                f'<text x="{_px(xa - 4)}" y="{_px(ya + 6.4)}" font-size="7.5" fill="#fff" text-anchor="middle">FUENTE 5V</text>')
    svg.add('</g>')


# ── Ruteo de cables ─────────────────────────────────────────────────────
#
# Cada cable sale de su agujero en vertical (alejándose del chip), corre en
# horizontal por un carril propio y entra en vertical al otro agujero, como se
# tiende un cable real en la protoboard. Dos tramos horizontales que se solapan
# nunca comparten carril, así que un bus de 8 bits se ve como 8 cables
# paralelos y no como uno solo. Los carriles se asignan una vez para todo el
# montaje: un cable se dibuja igual en todas las fases en que aparece.

TALON = 0.9        # tramo recto mínimo antes del primer codo (pasos)
CARRIL = 0.5       # separación entre carriles paralelos (pasos)
RADIO = 0.35       # radio de los codos (pasos)


def salida(ag):
    """Dirección (dx, dy) en que el cable deja el agujero."""
    if isinstance(ag, PinMega):
        p = ag.pin
        if p.startswith('A'):
            return (0, 1)                     # cabecera analógica: hacia abajo
        if p == 'GND' or int(p) >= 22:
            return (1, 0)                     # cabecera doble: hacia las protoboards
        return (0, -1)                        # cabecera digital 0-7: hacia arriba
    if ag.riel:
        return (0, 1) if ag.riel.startswith('T') else (0, -1)   # hacia las tiras
    return (0, -1) if ag.col in COLS_SUP else (0, 1)            # lejos del chip


class _Carriles:
    def __init__(self):
        self.h = []     # (y, x1, x2)
        self.v = []     # (x, y1, y2)

    @staticmethod
    def _libre(lista, c, a, b):
        return all(abs(c - cc) >= CARRIL * 0.95 or b < aa - 0.4 or a > bb + 0.4
                   for cc, aa, bb in lista)

    def horizontal(self, y0, sentido, x1, x2):
        """Primer carril libre a partir de y0 en el sentido dado (sin reservar)."""
        for k in range(80):
            y = y0 + sentido * (TALON + k * CARRIL)
            if self._libre(self.h, y, x1, x2):
                return y
        return y

    def vertical_cerca(self, x0, y1, y2):
        """Carril vertical libre más cercano a x0, probando a ambos lados."""
        for k in range(80):
            for x in ((x0,) if k == 0 else (x0 + k * CARRIL, x0 - k * CARRIL)):
                if self._libre(self.v, x, y1, y2):
                    return x
        return x0

    def vertical(self, x0, sentido, y1, y2):
        for k in range(80):
            x = x0 + sentido * (TALON + k * CARRIL)
            if self._libre(self.v, x, y1, y2):
                return x
        return x

    def reservar(self, pts):
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            if abs(ya - yb) < 1e-6 and abs(xa - xb) > 1e-6:
                self.h.append((ya, min(xa, xb), max(xa, xb)))
            elif abs(xa - xb) < 1e-6 and abs(ya - yb) > 1e-6:
                self.v.append((xa, min(ya, yb), max(ya, yb)))


def _cuerpos_chips():
    """Rectángulos (x1, y1, x2, y2) en pasos de cada chip, entre sus dos filas de patas."""
    out = []
    for c in MONTAJE.chips.values():
        xa, ya = pos(c.agujero(1))
        xb, yb = pos(c.agujero(c.pinout.pines))
        x1, x2 = sorted((xa, xb))
        # las patas están en fila1 .. fila1+mitad-1; el cuerpo entre las dos columnas
        xs = [pos(c.agujero(p))[0] for p in range(1, c.pinout.pines + 1)]
        ys = [pos(c.agujero(p))[1] for p in range(1, c.pinout.pines + 1)]
        out.append((min(xs) - 0.45, min(ys) + 0.2, max(xs) + 0.45, max(ys) - 0.2))
    return out


CUERPOS = _cuerpos_chips()


def _cruces(pts):
    """Cuántos tramos pasan por encima del cuerpo de un chip."""
    n = 0
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        for x1, y1, x2, y2 in CUERPOS:
            if abs(xa - xb) < 1e-6:           # vertical
                if x1 < xa < x2 and min(ya, yb) < y2 and max(ya, yb) > y1:
                    n += 1
            elif abs(ya - yb) < 1e-6:         # horizontal
                if y1 < ya < y2 and min(xa, xb) < x2 and max(xa, xb) > x1:
                    n += 1
            else:                             # diagonal (no debería haber)
                n += 0
    return n


ANCHO_TOTAL = OX_BB + ANCHO_BB + MARGEN
ALTO_TOTAL = MARGEN * 2 + 4 * ALTO_BB
CUERPO_MEGA = (MARGEN, OY_MEGA, MARGEN + MEGA_W, OY_MEGA + MEGA_H)


def _sobre_mega(pts):
    """Largo de los tramos que cruzan la placa del Mega (sin contar el primero
    y el último, que salen de sus pines)."""
    x1, y1, x2, y2 = CUERPO_MEGA
    total = 0.0
    for (xa, ya), (xb, yb) in list(zip(pts, pts[1:]))[1:-1]:
        if abs(xa - xb) < 1e-6 and x1 < xa < x2:
            total += max(0.0, min(max(ya, yb), y2) - max(min(ya, yb), y1))
        elif abs(ya - yb) < 1e-6 and y1 < ya < y2:
            total += max(0.0, min(max(xa, xb), x2) - max(min(xa, xb), x1))
    return total


def _costo(pts):
    largo = sum(math.hypot(xb - xa, yb - ya) for (xa, ya), (xb, yb) in zip(pts, pts[1:]))
    fuera = sum(1 for x, y in pts if not (0.4 < x < ANCHO_TOTAL - 0.4 and 0.4 < y < ALTO_TOTAL - 0.4))
    return (_cruces(pts) * 1000 + fuera * 5000 + _sobre_mega(pts) * 20
            + largo + (len(pts) - 2) * 1.5)


def _limpia(pts):
    """Quita puntos repetidos y codos colineales."""
    out = [pts[0]]
    for p in pts[1:]:
        if math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > 1e-6:
            out.append(p)
    i = 1
    while i < len(out) - 1:
        (xa, ya), (xb, yb), (xc, yc) = out[i - 1], out[i], out[i + 1]
        if (abs(xa - xb) < 1e-6 and abs(xb - xc) < 1e-6) or (abs(ya - yb) < 1e-6 and abs(yb - yc) < 1e-6):
            out.pop(i)
        else:
            i += 1
    return out


def _columnas_libres(y1, y2, cerca):
    """x candidatas para un tramo vertical entre y1 y y2 que no pisa chips:
    los bordes de cada chip que estorba, más las x dadas."""
    xs = set(cerca)
    for x1, cy1, x2, cy2 in CUERPOS:
        if min(y1, y2) < cy2 and max(y1, y2) > cy1:
            xs.add(x1 - 0.55)
            xs.add(x2 + 0.55)
    return sorted(xs, key=lambda x: min(abs(x - c) for c in cerca))[:8]


def _ruta(c, carriles):
    p0, p3 = pos(c.a), pos(c.b)
    d0, d3 = salida(c.a), salida(c.b)
    if d3[0] and not d0[0]:
        p0, p3, d0, d3 = p3, p0, d3, d0     # el extremo horizontal (Mega) va primero
    x0, y0 = p0
    x3, y3 = p3
    candidatas = []

    if d0[0]:
        # Mega → protoboard: horizontal al hueco, vertical por un carril propio
        # hasta un carril junto al destino, y entrada vertical.
        yB = carriles.horizontal(y3, d3[1], min(x0, x3), max(x0, x3))
        yB2 = carriles.horizontal(y3, -d3[1], min(x0, x3), max(x0, x3))
        for yy in (yB, yB2):
            xg = carriles.vertical(x0, d0[0], min(y0, yy), max(y0, yy))
            candidatas.append([p0, (xg, y0), (xg, yy), (x3, yy), p3])
    else:
        if abs(x0 - x3) < 0.05:
            candidatas.append([p0, p3])
        xa, xb = min(x0, x3), max(x0, x3)
        yA = carriles.horizontal(y0, d0[1], xa, xb)
        yB = carriles.horizontal(y3, d3[1], xa, xb)
        candidatas.append([p0, (x0, yA), (x3, yA), p3])
        candidatas.append([p0, (x0, yB), (x3, yB), p3])
        # rodeo: carril propio en cada extremo y una columna libre entre ambos
        for xf in _columnas_libres(yA, yB, (x0, x3, (x0 + x3) / 2)):
            ya = carriles.horizontal(y0, d0[1], min(x0, xf), max(x0, xf))
            yb = carriles.horizontal(y3, d3[1], min(x3, xf), max(x3, xf))
            xv = carriles.vertical_cerca(xf, min(ya, yb), max(ya, yb))
            candidatas.append([p0, (x0, ya), (xv, ya), (xv, yb), (x3, yb), p3])

    mejor = _limpia(min(candidatas, key=lambda r: _costo(_limpia(r))))
    carriles.reservar(mejor)
    return mejor


def _rutas():
    """Rutas de todo el montaje, calculadas una vez y en orden estable: por
    fase, y dentro de la fase del cable más corto al más largo (los cortos se
    quedan los carriles pegados a los agujeros)."""
    carriles = _Carriles()

    def largo(c):
        (x1, y1), (x2, y2) = pos(c.a), pos(c.b)
        return abs(x1 - x2) + abs(y1 - y2)

    rutas = {}
    for c in sorted(MONTAJE.cables, key=lambda c: (c.fase, largo(c), c.n)):
        rutas[c.n] = _ruta(c, carriles)
    return rutas


RUTAS = _rutas()


def _trazo(pts):
    """Polilínea con codos redondeados, en píxeles."""
    if len(pts) == 2:
        (x1, y1), (x2, y2) = pts
        return f'M{_px(x1)} {_px(y1)} L{_px(x2)} {_px(y2)}'
    d = [f'M{_px(pts[0][0])} {_px(pts[0][1])}']
    for i in range(1, len(pts) - 1):
        (xa, ya), (xb, yb), (xc, yc) = pts[i - 1], pts[i], pts[i + 1]
        la = math.hypot(xb - xa, yb - ya) or 1
        lc = math.hypot(xc - xb, yc - yb) or 1
        r = min(RADIO, la / 2, lc / 2)
        e1 = (xb - (xb - xa) / la * r, yb - (yb - ya) / la * r)
        e2 = (xb + (xc - xb) / lc * r, yb + (yc - yb) / lc * r)
        d.append(f'L{_px(e1[0])} {_px(e1[1])} Q{_px(xb)} {_px(yb)} {_px(e2[0])} {_px(e2[1])}')
    d.append(f'L{_px(pts[-1][0])} {_px(pts[-1][1])}')
    return ' '.join(d)


def _punto_en(pts, s):
    """Punto a distancia s (pasos) a lo largo de la polilínea."""
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        l = math.hypot(xb - xa, yb - ya)
        if s <= l:
            t = s / l if l else 0
            return (xa + (xb - xa) * t, ya + (yb - ya) * t)
        s -= l
    return pts[-1]


def _largo_ruta(pts):
    return sum(math.hypot(xb - xa, yb - ya) for (xa, ya), (xb, yb) in zip(pts, pts[1:]))


def _color(c):
    return COLOR_TEMPORAL if c.color == 'temporal' else COLORES[c.color][0]


def _borde(color):
    """Borde del número: un cable blanco necesita un borde que se vea."""
    return '#7a7a7a' if color.lower() in ('#fff', '#ffffff', '#f4f4f4', '#f5f5f5', '#f2f2f2', '#eeeeee') else color


def _cable(svg, c, estado):
    """estado: 'actual' o 'previo'. Solo el trazo; puntas y números van aparte."""
    ruta = _trazo(RUTAS[c.n])
    color = _color(c)
    if estado == 'previo':
        svg.add(f'<path d="{ruta}" stroke="{color}" stroke-width="2.2" fill="none" '
                f'stroke-linecap="round" stroke-linejoin="round" opacity=".28"/>')
        return
    guion = ' stroke-dasharray="6 4"' if c.temporal else ''
    svg.add(f'<g><path d="{ruta}" stroke="#fbfaf6" stroke-width="6.6" fill="none" stroke-linecap="round" '
            f'stroke-linejoin="round"/>'
            f'<path d="{ruta}" stroke="#1b1b1b" stroke-width="4.6" fill="none" stroke-linecap="round" '
            f'stroke-linejoin="round" opacity=".5"/>'
            f'<path d="{ruta}" stroke="{"#ffffff" if c.temporal else color}" stroke-width="3.1" fill="none" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
            + (f'<path d="{ruta}" stroke="{color}" stroke-width="3.1" fill="none" stroke-linecap="butt" '
               f'stroke-linejoin="round"{guion}/>' if c.temporal else '')
            + '</g>')


def _puntas(svg, cables):
    """Los extremos van encima de todos los cables: ninguno queda tapado."""
    for c in cables:
        color = _color(c)
        for x, y in (RUTAS[c.n][0], RUTAS[c.n][-1]):
            svg.add(f'<circle cx="{_px(x)}" cy="{_px(y)}" r="3.6" fill="{color}" stroke="#ffffff" '
                    f'stroke-width="1.4"/><circle cx="{_px(x)}" cy="{_px(y)}" r="4.6" fill="none" '
                    f'stroke="#111" stroke-width=".8"/>')


def _numeros(svg, cables):
    """Número del cable junto a cada extremo, sobre su propio trazo, sin pisar
    otro número ni otra punta."""
    ocupado = []            # rectángulos (x1, y1, x2, y2) en px

    def choca(r):
        return any(not (r[2] < o[0] or r[0] > o[2] or r[3] < o[1] or r[1] > o[3]) for o in ocupado)

    for c in cables:
        for x, y in (RUTAS[c.n][0], RUTAS[c.n][-1]):
            ocupado.append((x * P - 5, y * P - 5, x * P + 5, y * P + 5))

    for c in sorted(cables, key=lambda c: _largo_ruta(RUTAS[c.n])):
        pts = RUTAS[c.n]
        total = _largo_ruta(pts)
        texto = str(c.n)
        w, h = 5 + 4.4 * len(texto), 10.5
        if total < 3.2:
            puntos = [[total / 2 + d for d in (0, -0.4, 0.4, -0.8, 0.8) if 0.5 < total / 2 + d < total - 0.5]
                      or [total / 2]]
        else:
            pasos = [1.2 + 0.35 * i for i in range(40)]
            puntos = [[s for s in pasos if s < total / 2] or [total / 2],
                      [total - s for s in pasos if s < total / 2] or [total / 2]]
        for candidatos in puntos:
            mejor = None
            # sobre el trazo primero; si no cabe, un poco a un lado del trazo
            posiciones = [_punto_en(pts, s) for s in candidatos]
            posiciones += [(x + dx, y) for x, y in posiciones[:12] for dx in (-0.75, 0.75)]
            for x, y in posiciones:
                r = (x * P - w / 2 - 1, y * P - h / 2 - 1, x * P + w / 2 + 1, y * P + h / 2 + 1)
                solape = sum(max(0, min(r[2], o[2]) - max(r[0], o[0])) * max(0, min(r[3], o[3]) - max(r[1], o[1]))
                             for o in ocupado)
                if mejor is None or solape < mejor[0]:
                    mejor = (solape, x, y, r)
                if solape == 0:
                    break
            _, x, y, r = mejor
            ocupado.append(r)
            color = _color(c)
            svg.add(f'<g><rect x="{x * P - w / 2:.1f}" y="{y * P - h / 2:.1f}" width="{w:.1f}" height="{h}" rx="5" '
                    f'fill="#fff" stroke="{_borde(color)}" stroke-width="1.8"/>'
                    f'<text x="{x * P:.1f}" y="{y * P + 3.1:.1f}" font-size="8" text-anchor="middle" '
                    f'font-weight="700" fill="#111">{texto}</text></g>')


_ESCENAS = [0]


def escena(fase, vista=None, leyenda=None):
    """SVG de la fase. vista = (x, y, ancho, alto) en pasos para acercamientos.
    leyenda: filas (n, color, texto) que se dibujan en un panel bajo la vista."""
    m = MONTAJE
    _ESCENAS[0] += 1
    pid = f'aguj{_ESCENAS[0]}'
    cables, piezas = m.en_fase(fase)
    svg = Svg()
    ancho = OX_BB + ANCHO_BB + MARGEN
    alto = MARGEN * 2 + 4 * ALTO_BB
    vx, vy, vw, vh = vista or (0, 0, ancho, alto)
    FILA_LEY, COL_LEY = 1.25, 21.0
    cols_ley = max(1, int(vw // COL_LEY)) if leyenda else 1
    filas_ley = math.ceil(len(leyenda) / cols_ley) if leyenda else 0
    vh_total = vh + (filas_ley * FILA_LEY + 1.2 if leyenda else 0)
    svg.add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{_px(vx)} {_px(vy)} {_px(vw)} {_px(vh_total)}" '
            f'font-family="IBM Plex Mono, Consolas, monospace" role="img">')
    svg.add(f'<defs><pattern id="{pid}" width="12" height="12" patternUnits="userSpaceOnUse">'
            '<rect x="4" y="4" width="4" height="4" rx=".6" fill="#6d6859"/></pattern>'
            f'<clipPath id="{pid}c"><rect x="{_px(vx)}" y="{_px(vy)}" width="{_px(vw)}" height="{_px(vh)}"/></clipPath></defs>')
    svg.add(f'<rect x="{_px(vx)}" y="{_px(vy)}" width="{_px(vw)}" height="{_px(vh_total)}" fill="#fbfaf6"/>')
    svg.add(f'<g clip-path="url(#{pid}c)">')
    for k, bb in enumerate(PROTOBOARDS):
        _protoboard(svg, k, bb, pid)
    pines = {c.a.pin for c in cables if isinstance(c.a, PinMega)} | {c.b.pin for c in cables if isinstance(c.b, PinMega)}
    _mega(svg, pines)
    for c in m.chips.values():
        if c.fase <= fase:
            _chip(svg, c, tenue=c.fase < fase)
    for p in piezas:
        _pieza(svg, p, tenue=p.fase < fase, temporal=p.retirar is not None)
    previos = [c for c in cables if c.fase != fase]
    actuales = [c for c in cables if c.fase == fase]
    for c in previos:
        _cable(svg, c, 'previo')
    # los largos debajo, los cortos encima; los de prueba al final
    for c in sorted(actuales, key=lambda c: (c.temporal, -_largo_ruta(RUTAS[c.n]))):
        _cable(svg, c, 'actual')
    _puntas(svg, actuales)
    _numeros(svg, actuales)
    svg.add('</g>')
    if leyenda:
        y0 = vy + vh + 0.9
        svg.add(f'<line x1="{_px(vx)}" x2="{_px(vx + vw)}" y1="{_px(vy + vh)}" y2="{_px(vy + vh)}" stroke="#c9c3b3"/>')
        for i, (n, color, texto) in enumerate(leyenda):
            col, fila = divmod(i, filas_ley)
            x, y = vx + 0.6 + col * (vw / cols_ley), y0 + fila * FILA_LEY
            svg.add(f'<g><rect x="{_px(x)}" y="{_px(y - 0.45)}" width="{5 + 4.4 * len(str(n)):.1f}" height="10.5" '
                    f'rx="5" fill="#fff" stroke="{_borde(color)}" stroke-width="1.8"/>'
                    f'<text x="{x * P + (5 + 4.4 * len(str(n))) / 2:.1f}" y="{_px(y + 0.2)}" font-size="8" '
                    f'text-anchor="middle" font-weight="700" fill="#111">{n}</text>'
                    f'<text x="{_px(x + 2.0)}" y="{_px(y + 0.22)}" font-size="8" fill="#222">{html.escape(texto)}</text></g>')
    svg.add('</svg>')
    return '\n'.join(svg.partes)


def vista_chip(c):
    """Recorte alrededor de un chip: filas vecinas y todo el alto de su protoboard."""
    k = PROTOBOARDS.index(c.bb)
    x = OX_BB + c.fila1 - 5
    return (x, MARGEN + k * ALTO_BB - 0.5, c.mitad + 12, ALTO_BB + 1)


def describir(ag, desde=None):
    """Texto corto de qué hay en el otro extremo (para etiquetas y tablas)."""
    if isinstance(ag, PinMega):
        return str(ag)
    for ref, c in MONTAJE.chips.items():
        for p in range(1, c.pinout.pines + 1):
            if c.agujero(p).tira() == ag.tira() and not ag.riel:
                return f'{c.nombre} {c.pinout.senal(p)} (pin {p})'
    if not ag.riel:
        for pz in MONTAJE.piezas:
            for i, pata in enumerate(pz.patas):
                if not getattr(pata, 'riel', '') and pata.tira() == ag.tira():
                    if pz.tipo == 'dip':
                        return f'{ag} (dip switch, bit {i % 8})'
                    if pz.tipo == 'pulsador':
                        return f'{ag} (pulsador)'
    return str(ag)


def cables_de_chip(c, fase, vista=None):
    """Cables de la fase con un extremo dentro del recorte del chip:
    (cable, agujero de adentro, extremo opuesto), ordenados por número."""
    x0, y0, w, h = vista or vista_chip(c)
    out = []
    for cab in MONTAJE.cables:
        if cab.fase != fase:
            continue
        for ag, otro in ((cab.a, cab.b), (cab.b, cab.a)):
            if isinstance(ag, PinMega):
                continue
            x, y = pos(ag)
            if x0 <= x <= x0 + w and y0 <= y <= y0 + h:
                out.append((cab, ag, otro))
                break
    return sorted(out, key=lambda t: t[0].n)


def etiquetas_chip(c, fase, vista=None):
    """Filas del panel de leyenda de un acercamiento."""
    return [(cab.n, _color(cab), f'{ag} → {describir(otro)}')
            for cab, ag, otro in cables_de_chip(c, fase, vista)]


# ── Datos por fase ─────────────────────────────────────────────────────

def extremo(ag):
    if isinstance(ag, PinMega):
        return str(ag)
    return str(ag)


def datos():
    m = MONTAJE
    fases = []
    for f in FASES:
        cables = [c for c in m.cables if c.fase == f]
        retirar = [c for c in m.cables if c.temporal and c.retirar == f]
        chips = [c for c in m.chips.values() if c.fase == f]
        piezas = [p for p in m.piezas if p.fase == f]
        piezas_ret = [p for p in m.piezas if p.retirar == f]
        fases.append({
            'n': f, 'titulo': FASES[f],
            'chips': [{'ref': c.ref, 'nombre': c.nombre, 'parte': c.pinout.nombre, 'bb': c.bb,
                       'pin1': str(c.agujero(1)), 'pinN': str(c.agujero(c.pinout.pines)),
                       'ultimo_inf': str(c.agujero(c.mitad)), 'pines': c.pinout.pines,
                       'ancho': '600 mil (ancho)' if c.pinout.ancho == 6 else '300 mil',
                       'rol': c.rol} for c in chips],
            'piezas': [{'ref': p.ref, 'tipo': p.tipo, 'valor': p.valor,
                        'patas': [str(a) for a in p.patas], 'nota': p.nota,
                        'temporal': p.retirar is not None} for p in piezas],
            'cables': [{'n': c.n, 'desde': extremo(c.a), 'hasta': extremo(c.b), 'color': c.color,
                        'que': c.que, 'cm': largo_cm(c), 'temporal': c.temporal,
                        'desde_es': describir(c.a), 'hasta_es': describir(c.b)} for c in cables],
            'retirar_cables': [c.n for c in retirar],
            'retirar_piezas': [p.ref for p in piezas_ret],
        })
    compras = defaultdict(float)
    for c in m.cables:
        if not c.temporal:
            compras[c.color] += largo_cm(c)
    return {'fases': fases,
            'colores': {k: {'hex': v[0], 'uso': v[1]} for k, v in COLORES.items()},
            'metros_por_color': {k: round(v / 100 * 1.3 + 0.5, 1) for k, v in sorted(compras.items())},
            'totales': {'cables_definitivos': sum(1 for c in m.cables if not c.temporal),
                        'cables_prueba': sum(1 for c in m.cables if c.temporal)}}


def main():
    os.makedirs(SALIDA, exist_ok=True)
    for f in FASES:
        with open(os.path.join(SALIDA, f'fase{f}.svg'), 'w', encoding='utf-8') as fh:
            fh.write(escena(f))
        for c in MONTAJE.chips.values():
            if c.fase == f:
                with open(os.path.join(SALIDA, f'fase{f}_{c.ref}.svg'), 'w', encoding='utf-8') as fh:
                    fh.write(escena(f, vista_chip(c), etiquetas_chip(c, f)))
    with open(os.path.join(SALIDA, 'datos.json'), 'w', encoding='utf-8') as fh:
        json.dump(datos(), fh, ensure_ascii=False, indent=1)
    print('generado en', SALIDA)


if __name__ == '__main__':
    main()
