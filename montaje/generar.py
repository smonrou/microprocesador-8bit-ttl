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

import json
import math
import os
from collections import defaultdict

from montaje.netlist import (MONTAJE, FASES, COLORES, COLOR_TEMPORAL, PROTOBOARDS,
                             X_RIEL, FILAS, Agujero, PinMega, FIN)

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


def _cable(svg, c, estado, numero=True):
    """estado: 'actual', 'previo' o 'temporal'."""
    (x1, y1), (x2, y2) = pos(c.a), pos(c.b)
    color = COLOR_TEMPORAL if c.color == 'temporal' else COLORES[c.color][0]
    op = '.35' if estado == 'previo' else '1'
    # curva suave: los cables largos se arquean un poco para no taparse
    dx, dy = x2 - x1, y2 - y1
    d = math.hypot(dx, dy) or 1
    arco = min(1.2, d * 0.06) * (1 if (c.n % 2) else -1)
    cx, cy = (x1 + x2) / 2 - dy / d * arco, (y1 + y2) / 2 + dx / d * arco
    ruta = f'M{_px(x1)} {_px(y1)} Q{_px(cx)} {_px(cy)} {_px(x2)} {_px(y2)}'
    guion = ' stroke-dasharray="6 4"' if c.temporal else ''
    svg.add(f'<g opacity="{op}"><path d="{ruta}" stroke="#1b1b1b" stroke-width="5" fill="none" '
            f'stroke-linecap="round" opacity=".55"{guion}/>'
            f'<path d="{ruta}" stroke="{color}" stroke-width="3.2" fill="none" stroke-linecap="round"{guion}/>')
    for x, y in ((x1, y1), (x2, y2)):
        svg.add(f'<circle cx="{_px(x)}" cy="{_px(y)}" r="2.6" fill="{color}" stroke="#111" stroke-width=".8"/>')
    if numero and estado != 'previo':
        mx, my = (x1 + 2 * cx + x2) / 4, (y1 + 2 * cy + y2) / 4
        svg.add(f'<circle cx="{_px(mx)}" cy="{_px(my)}" r="7.5" fill="#fff" stroke="{color}" stroke-width="2"/>'
                f'<text x="{_px(mx)}" y="{_px(my + 0.27)}" font-size="{7.5 if c.n < 100 else 6.5}" '
                f'text-anchor="middle" font-weight="700" fill="#111">{c.n}</text>')
    svg.add('</g>')


_ESCENAS = [0]


def escena(fase, vista=None, etiquetas=None):
    """SVG de la fase. vista = (x, y, ancho, alto) en pasos para acercamientos."""
    m = MONTAJE
    _ESCENAS[0] += 1
    pid = f'aguj{_ESCENAS[0]}'
    cables, piezas = m.en_fase(fase)
    svg = Svg()
    ancho = OX_BB + ANCHO_BB + MARGEN
    alto = MARGEN * 2 + 4 * ALTO_BB
    vx, vy, vw, vh = vista or (0, 0, ancho, alto)
    svg.add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{_px(vx)} {_px(vy)} {_px(vw)} {_px(vh)}" '
            f'font-family="IBM Plex Mono, Consolas, monospace" role="img">')
    svg.add(f'<defs><pattern id="{pid}" width="12" height="12" patternUnits="userSpaceOnUse">'
            '<rect x="4" y="4" width="4" height="4" rx=".6" fill="#6d6859"/></pattern></defs>')
    svg.add(f'<rect x="{_px(vx)}" y="{_px(vy)}" width="{_px(vw)}" height="{_px(vh)}" fill="#fbfaf6"/>')
    for k, bb in enumerate(PROTOBOARDS):
        _protoboard(svg, k, bb, pid)
    pines = {c.a.pin for c in cables if isinstance(c.a, PinMega)} | {c.b.pin for c in cables if isinstance(c.b, PinMega)}
    _mega(svg, pines)
    for c in m.chips.values():
        if c.fase <= fase:
            _chip(svg, c, tenue=c.fase < fase)
    for p in piezas:
        _pieza(svg, p, tenue=p.fase < fase, temporal=p.retirar is not None)
    orden = sorted(cables, key=lambda c: (c.fase == fase, c.temporal))
    for c in orden:
        _cable(svg, c, 'actual' if c.fase == fase else 'previo')
    for (x, y, texto, color) in etiquetas or ():
        svg.add(f'<g><rect x="{_px(x + 0.55)}" y="{_px(y - 0.55)}" width="{len(texto) * 5.6 + 6:.0f}" height="12" rx="3" '
                f'fill="#ffffff" stroke="{color}" stroke-width="1.2" opacity=".95"/>'
                f'<text x="{_px(x + 0.8)}" y="{_px(y + 0.28)}" font-size="8.5" fill="#111">{texto}</text></g>')
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
    return str(ag)


def etiquetas_chip(c, fase):
    cables, _ = MONTAJE.en_fase(fase)
    x0, y0, w, h = vista_chip(c)
    et = []
    for cab in cables:
        if cab.fase != fase:
            continue
        for ag, otro in ((cab.a, cab.b), (cab.b, cab.a)):
            if isinstance(ag, PinMega):
                continue
            x, y = pos(ag)
            if ag.bb == c.bb and x0 <= x <= x0 + w and not ag.riel:
                ox, oy = pos(otro)
                if not (x0 <= ox <= x0 + w and y0 <= oy <= y0 + h):
                    color = COLOR_TEMPORAL if cab.color == 'temporal' else COLORES[cab.color][0]
                    et.append((x, y, f'#{cab.n} → {describir(otro)}', color))
    return et


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
