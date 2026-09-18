"""Verifica que el montaje físico (montaje/netlist.py) sea eléctricamente el
mismo circuito que el firmware y el Proteus validado.

La especificación esperada se construye aquí de forma independiente: pines
del Mega leídos de firmware/microprocesador/pines.h, funciones de cada pin de
montaje/pinouts.py (datasheets TI), y la topología de contexto_proyecto.md.
"""

import os
import re
from collections import defaultdict

import pytest

from montaje.netlist import (MONTAJE, Agujero, PinMega, FASES, COLS_SUP, COLS_INF,
                             X_RIEL, FILAS, FIN)
from montaje.pinouts import CANAL_244, CANAL_157

RAIZ = os.path.dirname(os.path.dirname(__file__))
PINES_H = os.path.join(RAIZ, 'firmware', 'microprocesador', 'pines.h')
FASE_FINAL = max(FASES)


# ── pines.h ─────────────────────────────────────────────────────────────

def _pines_h():
    txt = open(PINES_H, encoding='utf-8').read()
    d = {}
    for puerto, pin, senal in re.findall(r'P([ACL]\d)\s*=\s*pin\s*(\d+)\s*=\s*([A-Za-z0-9̄]+)', txt):
        d[senal.replace('̄', '')] = pin
    defs = dict(re.findall(r'#define\s+(PIN_\w+)\s+(\d+)', txt))
    d['CLK_A'] = defs['PIN_CLOCK_A']
    d['CLK_B'] = defs['PIN_CLOCK_B']
    d['SEL'] = defs['PIN_MUX']
    d['CLEAR'] = defs['PIN_CLEAR']
    d['CARRY'] = defs['PIN_CARRY']
    d['CLK_S'] = defs['PIN_CLOCK_SALIDA']
    return d


PH = _pines_h()


def test_pines_h_se_leyo_completo():
    for k in range(8):
        assert f'D{k}' in PH and f'F{k}' in PH
    for s in ('S0', 'S1', 'S2', 'S3', 'M', 'Cn'):
        assert s in PH
    assert PH['F0'] == '37' and PH['F7'] == '30', 'PORTC desciende'
    assert PH['D0'] == '22' and PH['D7'] == '29', 'PORTA asciende'


# ── Especificación lógica esperada ──────────────────────────────────────

def _esperado():
    """red -> conjunto de miembros 'REF:SEÑAL' o 'MEGA:pin'."""
    r = defaultdict(set)
    alu = lambda k: 'ALU_BAJA' if k < 4 else 'ALU_ALTA'
    mux = lambda k: 'MUX_BAJO' if k < 4 else 'MUX_ALTO'
    for k in range(8):
        ch = CANAL_157[k % 4]
        r[f'D{k}'] |= {f'MEGA:{PH[f"D{k}"]}', f'REG_B:D{k}', f'{mux(k)}:{ch}A'}
        r[f'F{k}'] |= {f'MEGA:{PH[f"F{k}"]}', f'{alu(k)}:F{k % 4}', f'{mux(k)}:{ch}B', f'REG_S:D{k}'}
        r[f'QA{k}'] |= {f'REG_A:Q{k}', f'{alu(k)}:A{k % 4}'}
        r[f'QB{k}'] |= {f'REG_B:Q{k}', f'{alu(k)}:B{k % 4}'}
        r[f'YA{k}'] |= {f'{mux(k)}:{ch}Y', f'REG_A:D{k}'}
        r[f'QS{k}'] |= {f'REG_S:Q{k}', f'BUF:{CANAL_244[k][0]}'}
    for s in ('S0', 'S1', 'S2', 'S3', 'M'):
        r[s] |= {f'MEGA:{PH[s]}', f'ALU_BAJA:{s}', f'ALU_ALTA:{s}'}
    r['CN'] |= {f'MEGA:{PH["Cn"]}', 'ALU_BAJA:CN'}
    r['CARRY_MED'] |= {'ALU_BAJA:CN4', 'ALU_ALTA:CN'}
    r['CARRY'] |= {'ALU_ALTA:CN4', f'MEGA:{PH["CARRY"]}'}
    r['CLK_A'] |= {f'MEGA:{PH["CLK_A"]}', 'REG_A:CLK'}
    r['CLK_B'] |= {f'MEGA:{PH["CLK_B"]}', 'REG_B:CLK'}
    r['CLK_S'] |= {f'MEGA:{PH["CLK_S"]}', 'REG_S:CLK'}
    r['CLEAR'] |= {f'MEGA:{PH["CLEAR"]}', 'REG_A:CLR', 'REG_B:CLR', 'REG_S:CLR'}
    r['SEL'] |= {f'MEGA:{PH["SEL"]}', 'MUX_BAJO:SEL', 'MUX_ALTO:SEL'}
    for c in MONTAJE.chips.values():
        r['VCC'].add(f'{c.ref}:VCC')
        r['GND'].add(f'{c.ref}:GND')
    r['GND'] |= {'MUX_BAJO:G', 'MUX_ALTO:G', 'BUF:1G', 'BUF:2G', 'MEGA:GND'}
    return r


ESPERADO = _esperado()


# ── Conectividad física ─────────────────────────────────────────────────

class _UF:
    def __init__(self):
        self.p = {}

    def f(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def u(self, a, b):
        self.p[self.f(a)] = self.f(b)


def _nodo(ag):
    if isinstance(ag, PinMega):
        return ('MEGA', ag.pin)
    return ag.tira()


def conectividad(fase):
    uf = _UF()
    cables, _ = MONTAJE.en_fase(fase)
    for c in cables:
        uf.u(_nodo(c.a), _nodo(c.b))
    return uf


def _miembro_nodo(miembro):
    ref, senal = miembro.split(':')
    if ref == 'MEGA':
        return ('MEGA', senal)
    c = MONTAJE.chips[ref]
    return c.agujero(c.pinout.pin_de(senal)).tira()


def test_conectividad_final_igual_a_la_especificacion():
    uf = conectividad(FASE_FINAL)
    comp_de_red = {}
    for red, miembros in ESPERADO.items():
        comps = {uf.f(_miembro_nodo(m)) for m in miembros}
        assert len(comps) == 1, f'la red {red} está partida: {sorted(miembros)}'
        comp_de_red[red] = comps.pop()
    por_comp = defaultdict(list)
    for red, comp in comp_de_red.items():
        por_comp[comp].append(red)
    juntas = [v for v in por_comp.values() if len(v) > 1]
    assert not juntas, f'redes en corto entre sí: {juntas}'


def test_ningun_pin_de_chip_en_una_red_que_no_le_toca():
    uf = conectividad(FASE_FINAL)
    comp_de_red = {red: uf.f(_miembro_nodo(next(iter(m)))) for red, m in ESPERADO.items()}
    red_de_comp = {v: k for k, v in comp_de_red.items()}
    for c in MONTAJE.chips.values():
        for p in range(1, c.pinout.pines + 1):
            comp = uf.f(c.agujero(p).tira())
            red = red_de_comp.get(comp)
            miembro = f'{c.ref}:{c.pinout.senal(p)}'
            if red is not None:
                assert miembro in ESPERADO[red], f'{miembro} quedó conectado a la red {red}'


def test_ninguna_entrada_flotante():
    """Toda entrada de todo chip debe tener al menos un cable en su tira."""
    cables, _ = MONTAJE.en_fase(FASE_FINAL)
    tiras = {_nodo(x) for c in cables for x in (c.a, c.b)}
    for c in MONTAJE.chips.values():
        for p in range(1, c.pinout.pines + 1):
            if c.pinout.tipo(p) in ('in', 'vcc', 'gnd'):
                assert c.agujero(p).tira() in tiras, f'{c.nombre} pin {p} ({c.pinout.senal(p)}) flotante'


@pytest.mark.parametrize('fase', [1, 2, 3, 4])
def test_ninguna_entrada_flotante_durante_las_pruebas(fase):
    """Con los cables de prueba puestos, las entradas de los chips ya colocados
    tampoco pueden quedar al aire (un TTL al aire lee 1 de forma inestable)."""
    cables, _ = MONTAJE.en_fase(fase)
    tiras = {_nodo(x) for c in cables for x in (c.a, c.b)}
    for c in MONTAJE.chips.values():
        if c.fase > fase:
            continue
        for p in range(1, c.pinout.pines + 1):
            if c.pinout.tipo(p) == 'in':
                assert c.agujero(p).tira() in tiras, \
                    f'fase {fase}: {c.nombre} pin {p} ({c.pinout.senal(p)}) flotante'


def test_rieles_unidos_en_una_sola_red_por_polaridad():
    uf = conectividad(0)
    for pol, rieles in (('+', ('T+', 'B+')), ('-', ('T-', 'B-'))):
        comps = {uf.f((bb, r)) for bb in ('BB1', 'BB2', 'BB3', 'BB4') for r in rieles}
        assert len(comps) == 1, f'rieles {pol} no quedaron todos unidos en la fase 0'
    assert uf.f(('BB1', 'T+')) != uf.f(('BB1', 'T-'))


def test_vcc_y_gnd_a_su_riel():
    uf = conectividad(FASE_FINAL)
    vcc = uf.f(('BB1', 'T+'))
    gnd = uf.f(('BB1', 'T-'))
    for c in MONTAJE.chips.values():
        assert uf.f(c.agujero(c.pinout.pin_de('VCC')).tira()) == vcc, c.nombre
        assert uf.f(c.agujero(c.pinout.pin_de('GND')).tira()) == gnd, c.nombre
    assert uf.f(('MEGA', 'GND')) == gnd


def test_cada_chip_tiene_su_desacople_junto_al_vcc():
    for c in MONTAJE.chips.values():
        caps = [p for p in MONTAJE.piezas if p.ref == f'C_{c.ref}']
        assert len(caps) == 1, c.nombre
        patas = caps[0].patas
        assert {a.riel for a in patas} == {'T+', 'T-'} and all(a.bb == c.bb for a in patas)
        fila_vcc = c.agujero(c.pinout.pin_de('VCC')).fila
        assert all(abs(a.fila - fila_vcc) <= 3 for a in patas), f'desacople de {c.nombre} lejos del VCC'
        assert caps[0].fase == c.fase


def test_leds_bit_a_bit():
    uf = conectividad(FASE_FINAL)
    gnd = uf.f(('BB1', 'T-'))
    fila = {}
    for bit in range(8):
        r = next(p for p in MONTAJE.piezas if p.ref == f'R_LED{bit}')
        led = next(p for p in MONTAJE.piezas if p.ref == f'LED{bit}')
        y = MONTAJE.chips['BUF'].agujero(MONTAJE.chips['BUF'].pinout.pin_de(CANAL_244[bit][1])).tira()
        comps_r = {uf.f(a.tira()) for a in r.patas}
        assert uf.f(y) in comps_r, f'la resistencia del bit {bit} no está en la salida del 244'
        anodo, catodo = led.patas
        assert uf.f(anodo.tira()) in comps_r and uf.f(anodo.tira()) != uf.f(y)
        assert uf.f(catodo.tira()) == gnd, f'cátodo del LED {bit} no va a GND'
        fila[bit] = anodo.fila
    assert [fila[b] for b in range(7, -1, -1)] == sorted(fila.values()), 'bit 7 debe quedar a la izquierda'


def test_colores_por_funcion():
    esperado = {'D': 'amarillo', 'F': 'azul', 'QA': 'verde', 'QB': 'blanco', 'YA': 'naranja',
                'QS': 'gris', 'LED': 'gris', 'S': 'morado', 'M': 'morado', 'CN': 'morado',
                'CARRY': 'morado', 'CARRY_MED': 'morado', 'CLK_A': 'cafe', 'CLK_B': 'cafe',
                'CLK_S': 'cafe', 'CLEAR': 'cafe', 'SEL': 'cafe', 'VCC': 'rojo', 'GND': 'negro'}
    for c in MONTAJE.cables:
        if c.temporal:
            assert c.color == 'temporal'
            continue
        grupo = c.red if c.red in esperado else re.sub(r'\d+$', '', c.red)
        assert c.color == esperado[grupo], f'cable {c.n} ({c.que}) debería ser {esperado[grupo]}'


def test_alu_de_600_mil_en_d_y_h():
    for ref in ('ALU_BAJA', 'ALU_ALTA'):
        c = MONTAJE.chips[ref]
        assert {c.agujero(p).col for p in range(1, 25)} == {'d', 'h'}


def test_ningun_agujero_con_dos_cosas_a_la_vez():
    for fase in FASES:
        cables, piezas = MONTAJE.en_fase(fase)
        vistos = {}
        for c in MONTAJE.chips.values():
            for p in range(1, c.pinout.pines + 1):
                vistos[c.agujero(p)] = f'{c.ref}:{p}'
        for obj, patas in [(f'cable {c.n}', (c.a, c.b)) for c in cables] + [(p.ref, p.patas) for p in piezas]:
            for ag in patas:
                if isinstance(ag, PinMega):
                    continue
                assert ag not in vistos, f'fase {fase}: {ag} lo usan {vistos[ag]} y {obj}'
                vistos[ag] = obj


def test_agujeros_existen():
    for c in MONTAJE.cables:
        for ag in (c.a, c.b):
            if isinstance(ag, PinMega):
                continue
            if ag.riel:
                assert ag.fila in X_RIEL
            else:
                assert 1 <= ag.fila <= FILAS and ag.col in COLS_SUP + COLS_INF


def test_pines_del_mega_una_vez():
    usados = [x.pin for c in MONTAJE.cables for x in (c.a, c.b) if isinstance(x, PinMega) and x.pin != 'GND']
    assert len(usados) == len(set(usados))
    assert len(usados) == 8 + 8 + 6 + 1 + 5, 'D, F, control ALU, acarreo y 5 de registros/mux'


def test_pruebas_retiradas_antes_del_mega():
    cables, piezas = MONTAJE.en_fase(5)
    assert not [c.n for c in cables if c.temporal]
    assert not [p.ref for p in piezas if p.retirar is not None]


def test_mega_no_alimenta_la_protoboard():
    assert not any(isinstance(x, PinMega) and x.pin in ('5V', 'VIN', '3V3')
                   for c in MONTAJE.cables for x in (c.a, c.b))
