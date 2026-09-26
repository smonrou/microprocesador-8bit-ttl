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
    # PORTK: Q del contador de programa, por los pines analógicos A8-A15.
    for puerto, pin, senal in re.findall(r'P(K\d)\s*=\s*(A\d+)\s*=\s*(PC\d)', txt):
        d[senal] = pin
    defs = dict(re.findall(r'#define\s+(PIN_\w+)\s+(\d+)', txt))
    d['CLK_A'] = defs['PIN_CLOCK_A']
    d['CLK_B'] = defs['PIN_CLOCK_B']
    d['SEL'] = defs['PIN_MUX']
    d['CLEAR'] = defs['PIN_CLEAR']
    d['CARRY'] = defs['PIN_CARRY']
    d['CLK_S'] = defs['PIN_CLOCK_SALIDA']
    d['CLK_PC'] = defs['PIN_CLOCK_PC']
    d['LOAD_PC'] = defs['PIN_CARGA_PC']
    return d


PH = _pines_h()


def test_pines_h_se_leyo_completo():
    for k in range(8):
        assert f'D{k}' in PH and f'F{k}' in PH
    for s in ('S0', 'S1', 'S2', 'S3', 'M', 'Cn'):
        assert s in PH
    assert PH['F0'] == '37' and PH['F7'] == '30', 'PORTC desciende'
    assert PH['D0'] == '22' and PH['D7'] == '29', 'PORTA asciende'
    assert [PH[f'PC{k}'] for k in range(8)] == [f'A{8 + k}' for k in range(8)], 'PORTK asciende'


# ── Especificación lógica esperada ──────────────────────────────────────

def _esperado():
    """red -> conjunto de miembros 'REF:SEÑAL' o 'MEGA:pin'."""
    r = defaultdict(set)
    alu = lambda k: 'ALU_BAJA' if k < 4 else 'ALU_ALTA'
    mux = lambda k: 'MUX_BAJO' if k < 4 else 'MUX_ALTO'
    pc = lambda k: 'PC_BAJO' if k < 4 else 'PC_ALTO'
    for k in range(8):
        ch = CANAL_157[k % 4]
        # El bus D también es la entrada de carga paralela del PC (saltos).
        r[f'D{k}'] |= {f'MEGA:{PH[f"D{k}"]}', f'REG_B:D{k}', f'{mux(k)}:{ch}A', f'{pc(k)}:P{k % 4}'}
        r[f'PC{k}'] |= {f'{pc(k)}:Q{k % 4}', f'MEGA:{PH[f"PC{k}"]}'}
        # El bus F llega al Mega a través de una resistencia de 330 Ω en serie
        # (protección contra contención), así que del lado del Mega es otra red.
        r[f'F{k}'] |= {f'{alu(k)}:F{k % 4}', f'{mux(k)}:{ch}B', f'REG_S:D{k}'}
        r[f'F_MEGA{k}'] |= {f'MEGA:{PH[f"F{k}"]}'}
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
    r['CLEAR'] |= {f'MEGA:{PH["CLEAR"]}', 'REG_A:CLR', 'REG_B:CLR', 'REG_S:CLR',
                   'PC_BAJO:CLR', 'PC_ALTO:CLR'}
    r['CLK_PC'] |= {f'MEGA:{PH["CLK_PC"]}', 'PC_BAJO:CLK', 'PC_ALTO:CLK'}
    r['LOAD_PC'] |= {f'MEGA:{PH["LOAD_PC"]}', 'PC_BAJO:LOAD', 'PC_ALTO:LOAD'}
    r['RCO_PC'] |= {'PC_BAJO:RCO', 'PC_ALTO:ENT'}
    r['SEL'] |= {f'MEGA:{PH["SEL"]}', 'MUX_BAJO:SEL', 'MUX_ALTO:SEL'}
    for c in MONTAJE.chips.values():
        r['VCC'].add(f'{c.ref}:VCC')
        r['GND'].add(f'{c.ref}:GND')
    r['GND'] |= {'MUX_BAJO:G', 'MUX_ALTO:G', 'BUF:1G', 'BUF:2G', 'MEGA:GND'}
    # El PC cuenta siempre que recibe un flanco: ENP de los dos y ENT del
    # bajo fijos en alto; el ENT del alto viene del RCO del bajo.
    r['VCC'] |= {'PC_BAJO:ENP', 'PC_BAJO:ENT', 'PC_ALTO:ENP'}
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


def test_bus_f_con_resistencia_en_serie_al_mega():
    """Cada bit del bus F llega al Mega a través de 330 Ω, no directo: si un
    pin del Mega quedara como salida, la resistencia limita la contención
    contra la 74LS181 en vez de que se queme uno de los dos."""
    uf = conectividad(FASE_FINAL)
    piezas = {p.ref: p for p in MONTAJE.piezas}
    reg_s = MONTAJE.chips['REG_S']
    for k in range(8):
        r = piezas[f'R_F{k}']
        assert r.valor == '330 Ω' and r.retirar is None, f'R_F{k} no es permanente de 330 Ω'
        tiras = {a.tira() for a in r.patas}
        pin = reg_s.agujero(reg_s.pinout.pin_de(f'D{k}')).tira()
        assert pin in tiras, f'R_F{k} no toca el pin D{k} de REG SALIDA'
        otra = (tiras - {pin}).pop()
        assert uf.f(otra) != uf.f(pin), f'R_F{k} está puenteada: sus dos patas en la misma red'
        assert uf.f(otra) == uf.f(('MEGA', PH[f'F{k}'])), \
            f'R_F{k} no queda en el camino al pin {PH[f"F{k}"]} del Mega'


def test_control_con_resistencia_de_reposo():
    """CLEAR, SEL y los tres relojes no pueden colgar solo del Mega: sus pines
    flotan mientras el Mega resetea y durante cada carga de firmware."""
    esperado = {'R_CLEAR': ('REG_A', 'CLR', '+'), 'R_SEL': ('MUX_BAJO', 'SEL', '-'),
                'R_CLK_A': ('REG_A', 'CLK', '-'), 'R_CLK_B': ('REG_B', 'CLK', '-'),
                'R_CLK_S': ('REG_S', 'CLK', '-'),
                'R_CLK_PC': ('PC_BAJO', 'CLK', '-'), 'R_LOAD_PC': ('PC_BAJO', 'LOAD', '+')}
    piezas = {p.ref: p for p in MONTAJE.piezas}
    for ref, (chip, senal, polaridad) in esperado.items():
        p = piezas[ref]
        assert p.valor == '1 kΩ' and p.retirar is None, f'{ref} no es permanente de 1 kΩ'
        c = MONTAJE.chips[chip]
        pin = c.agujero(c.pinout.pin_de(senal)).tira()
        assert pin in {a.tira() for a in p.patas}, f'{ref} no toca {chip}:{senal}'
        rieles = [a.riel for a in p.patas if a.riel]
        assert len(rieles) == 1 and rieles[0].endswith(polaridad), \
            f'{ref} tiene que ir a un riel {polaridad}, no a {rieles}'


def test_ninguna_pieza_puentea_dos_pines_de_chip():
    """La reserva de agujeros es hueco por hueco, así que una pata de pieza
    puede caer en la tira de un pin sin que nada se queje. Con las dos patas
    en tiras de pines distintos, la pieza cortocircuita dos señales."""
    de_pin = {}
    for c in MONTAJE.chips.values():
        for p in range(1, c.pinout.pines + 1):
            de_pin[c.agujero(p).tira()] = f'{c.ref}:{c.pinout.senal(p)}'
    for p in MONTAJE.piezas:
        tocados = {de_pin[a.tira()] for a in p.patas if not a.riel and a.tira() in de_pin}
        assert len(tocados) <= 1, f'{p.ref} toca los pines {sorted(tocados)}'


def _cruzan(a, b, c, d):
    def lado(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return ((lado(c, d, a) > 0) != (lado(c, d, b) > 0)
            and (lado(a, b, c) > 0) != (lado(a, b, d) > 0))


def test_ninguna_pieza_se_monta_sobre_otra_ni_sobre_un_chip():
    """Dos piezas que se cruzan no caben: son cuerpos rígidos apoyados en la
    protoboard, no cables que se puedan rodear. La reserva de agujeros no lo
    ve porque mira huecos, no el camino entre ellos."""
    from montaje.generar import pos

    dos = [p for p in MONTAJE.piezas if len(p.patas) == 2]
    seg = {p.ref: tuple(pos(a) for a in p.patas) for p in dos}
    for i, p in enumerate(dos):
        for q in dos[i + 1:]:
            if p.patas[0].bb != q.patas[0].bb or set(p.patas) & set(q.patas):
                continue
            assert not _cruzan(*seg[p.ref], *seg[q.ref]), f'{p.ref} se cruza con {q.ref}'
    for p in dos:
        for c in MONTAJE.chips.values():
            if c.bb != p.patas[0].bb:
                continue
            xs = [pos(c.agujero(n))[0] for n in range(1, c.pinout.pines + 1)]
            ys = [pos(c.agujero(n))[1] for n in range(1, c.pinout.pines + 1)]
            esq = [(min(xs), min(ys)), (max(xs), min(ys)), (max(xs), max(ys)), (min(xs), max(ys))]
            for u, v in zip(esq, esq[1:] + esq[:1]):
                assert not _cruzan(*seg[p.ref], u, v), f'{p.ref} pasa sobre {c.nombre}'


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
    esperado = {'D': 'amarillo', 'F': 'azul', 'F_MEGA': 'azul', 'QA': 'verde', 'QB': 'blanco', 'YA': 'naranja',
                'QS': 'gris', 'LED': 'gris', 'PC': 'gris', 'S': 'morado', 'M': 'morado', 'CN': 'morado',
                'CARRY': 'morado', 'CARRY_MED': 'morado', 'CLK_A': 'cafe', 'CLK_B': 'cafe',
                'CLK_S': 'cafe', 'CLEAR': 'cafe', 'SEL': 'cafe', 'CLK_PC': 'cafe', 'LOAD_PC': 'cafe',
                'RCO_PC': 'cafe', 'VCC': 'rojo', 'GND': 'negro'}
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
    assert len(usados) == 8 + 8 + 6 + 1 + 5 + 2 + 8, \
        'D, F, control ALU, acarreo, 5 de registros/mux, 2 de control del PC y 8 de lectura del PC'


def test_pruebas_retiradas_antes_del_mega():
    cables, piezas = MONTAJE.en_fase(5)
    assert not [c.n for c in cables if c.temporal]
    assert not [p.ref for p in piezas if p.retirar is not None]


def test_mega_no_alimenta_la_protoboard():
    assert not any(isinstance(x, PinMega) and x.pin in ('5V', 'VIN', '3V3')
                   for c in MONTAJE.cables for x in (c.a, c.b))


def test_el_pc_es_un_contador_fisico_en_cascada():
    """El PC no puede ser una variable del Arduino: son dos 74LS161 cuyo
    acarreo (RCO) habilita al alto, para que 0x0F + 1 = 0x10 y 0xFF + 1 = 0x00
    sin que el Arduino calcule nada."""
    for ref in ('PC_BAJO', 'PC_ALTO'):
        assert MONTAJE.chips[ref].pinout.nombre == '74LS161'
    uf = conectividad(FASE_FINAL)
    vcc = uf.f(('BB1', 'T+'))
    rco = _miembro_nodo('PC_BAJO:RCO')
    assert uf.f(_miembro_nodo('PC_ALTO:ENT')) == uf.f(rco) != vcc, \
        'el ENT de PC ALTO tiene que venir del RCO de PC BAJO, no de +5 V'
