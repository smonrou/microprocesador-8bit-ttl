"""Fuente de verdad del montaje físico: qué va en qué agujero, con qué color y
en qué fase.

Geometría de una protoboard de 830 puntos, vista con la fila 1 a la izquierda
y la letra j arriba:

    riel +  (externo, raya roja)       ── superior
    riel −  (interno, raya azul)
    j i h g f   ← mitad superior: cada fila es una tira de 5 agujeros unidos
    ─── canal central ───
    e d c b a   ← mitad inferior: otra tira de 5 por fila
    riel −  (interno, raya azul)       ── inferior
    riel +  (externo, raya roja)

Los chips de 300 mil van con las patas en e/f; el 74LS181 (600 mil) en d/h.
El pin 1 siempre queda en la mitad inferior, en la fila más baja del chip, con
la muesca apuntando hacia la fila 1.

Todo lo demás (dibujos, tablas, checklist, compras) se genera de aquí.
"""

from dataclasses import dataclass, field

from montaje.pinouts import LS181, LS273, LS157, LS244, CANAL_244, CANAL_157

FILAS = 63
COLS_INF = 'abcde'           # de afuera hacia el canal
COLS_SUP = 'fghij'           # del canal hacia afuera
RIELES = ('T+', 'T-', 'B-', 'B+')
PROTOBOARDS = ('BB1', 'BB2', 'BB3', 'BB4')
# Columnas de riel: 10 grupos de 5, con un hueco cada 6 (filas 3-7, 9-13, ...).
X_RIEL = tuple(3 + 6 * g + k for g in range(10) for k in range(5))

# ── Fases ────────────────────────────────────────────────────────────────
FASES = {
    0: 'Preparación, base y alimentación',
    1: 'Etapa de salida: registro de salida, 74LS244 y 8 LEDs',
    2: 'ALU: dos 74LS181 en cascada',
    3: 'Registros A y B',
    4: 'Multiplexor de entrada a A',
    5: 'Arduino Mega',
    6: 'Cierre y verificación final',
}

# ── Código de colores ───────────────────────────────────────────────────
COLORES = {
    'rojo':     ('#d62828', '+5 V'),
    'negro':    ('#1d1d1d', 'GND y habilitaciones atadas a GND'),
    'amarillo': ('#f2c200', 'Bus D: Arduino → REG B y entradas A del mux'),
    'azul':     ('#1f5fd1', 'Bus F: salida de la ALU → Arduino, mux B y registro de salida'),
    'verde':    ('#2e9e44', 'REG A (Q) → ALU A'),
    'blanco':   ('#f4f4f4', 'REG B (Q) → ALU B'),
    'naranja':  ('#f07d19', 'Salida Y del mux → REG A (D)'),
    'gris':     ('#8a8a8a', 'Etapa de salida: REG SALIDA (Q) → 244 → LEDs'),
    'morado':   ('#7b3fb5', 'Control de la ALU: S0–S3, M, C̄n y acarreos'),
    'cafe':     ('#8b5a2b', 'Control de registros: relojes, CLEAR y selección del mux'),
}
COLOR_TEMPORAL = '#e0409a'   # dupont de prueba: se retira al cerrar la fase


# ── Tipos ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Agujero:
    """Un agujero físico. En tira: fila + columna. En riel: riel + x."""
    bb: str
    fila: int = 0
    col: str = ''
    riel: str = ''

    def tira(self):
        """Nodo eléctrico al que pertenece el agujero antes de cablear."""
        if self.riel:
            return (self.bb, self.riel)
        return (self.bb, self.fila, 'sup' if self.col in COLS_SUP else 'inf')

    def __str__(self):
        if self.riel:
            nombre = {'T+': '+ sup', 'T-': '− sup', 'B-': '− inf', 'B+': '+ inf'}[self.riel]
            return f'{self.bb} riel {nombre} (fila {self.fila})'
        return f'{self.bb}-{self.col}{self.fila}'


@dataclass(frozen=True)
class PinMega:
    pin: str      # '22', '2', 'GND'

    def __str__(self):
        return f'Mega {self.pin}' if self.pin == 'GND' else f'Mega pin {self.pin}'


@dataclass
class Chip:
    ref: str
    nombre: str
    pinout: object
    bb: str
    fila1: int
    fase: int
    rol: str
    girado: bool = False   # True: pin 1 arriba a la derecha (muesca hacia la fila 63)

    @property
    def mitad(self):
        return self.pinout.pines // 2

    @property
    def col_inf(self):
        return 'e' if self.pinout.ancho == 3 else 'd'

    @property
    def col_sup(self):
        return 'f' if self.pinout.ancho == 3 else 'h'

    def agujero(self, pin):
        n = self.mitad
        if not self.girado:
            if pin <= n:
                return Agujero(self.bb, self.fila1 + pin - 1, self.col_inf)
            return Agujero(self.bb, self.fila1 + (self.pinout.pines - pin), self.col_sup)
        # girado 180°: pin 1 arriba a la derecha, los pines bajan hacia la izquierda
        if pin <= n:
            return Agujero(self.bb, self.fila1 + n - pin, self.col_sup)
        return Agujero(self.bb, self.fila1 + pin - n - 1, self.col_inf)

    def libres(self, pin):
        """Agujeros libres de la tira del pin, del más externo al más interno."""
        a = self.agujero(pin)
        if a.col in COLS_INF:
            cols = COLS_INF[:COLS_INF.index(a.col)]
        else:
            cols = COLS_SUP[COLS_SUP.index(a.col) + 1:][::-1]
        return [Agujero(self.bb, a.fila, c) for c in cols]

    def filas(self):
        return range(self.fila1, self.fila1 + self.mitad)


@dataclass
class Pieza:
    """Componente de dos o más patas que no es un chip."""
    ref: str
    tipo: str            # 'cap', 'electrolitico', 'led', 'resistencia', 'dip', 'pulsador'
    valor: str
    patas: tuple         # agujeros
    fase: int
    retirar: int = None  # fase al final de la cual se quita (temporales)
    nota: str = ''


@dataclass
class Cable:
    n: int
    a: object            # Agujero o PinMega
    b: object
    color: str
    fase: int
    que: str             # descripción humana
    red: str
    retirar: int = None  # temporales
    condicional: str = ''

    @property
    def temporal(self):
        return self.retirar is not None


FIN = 99   # "hasta el final": fase de retiro de lo que se queda para siempre


@dataclass
class Montaje:
    chips: dict = field(default_factory=dict)
    piezas: list = field(default_factory=list)
    cables: list = field(default_factory=list)
    # Agujero -> [(fase_ini, fase_fin, quién)]. Un agujero puede reutilizarse
    # cuando lo que lo ocupaba (un cable de prueba) ya se retiró.
    ocupacion: dict = field(default_factory=dict)

    def libre(self, ag, ini, fin):
        return all(fin < a or b < ini for a, b, _ in self.ocupacion.get(ag, ()))

    def ocupar(self, ag, ini, fin, quien):
        if not self.libre(ag, ini, fin):
            raise ValueError(f'{ag} ya está ocupado en fases {ini}-{fin}: '
                             f'{self.ocupacion[ag]}; lo quiere {quien}')
        self.ocupacion.setdefault(ag, []).append((ini, fin, quien))

    def en_fase(self, fase):
        """Cables y piezas físicamente presentes durante la fase dada."""
        cab = [c for c in self.cables if c.fase <= fase <= (c.retirar if c.temporal else FIN)]
        pie = [p for p in self.piezas if p.fase <= fase <= (p.retirar if p.retirar is not None else FIN)]
        return cab, pie


# ── Construcción ─────────────────────────────────────────────────────────

def _x_riel(x_deseada):
    return min(X_RIEL, key=lambda x: (abs(x - x_deseada), x))


# Colocación: ref -> (fila más baja que ocupa el chip, girado).
COLOCACION = {
    # Resultado de minimizar el largo total de cable (búsqueda por coordenadas
    # sobre filas y giro de cada chip), relajado a mano: nada antes de la
    # fila 6 (ahí pasan los puentes de alimentación) y al menos 4 filas libres
    # entre chips de la misma protoboard para que quepan los cables.
    'MUX_BAJO': (8, False), 'MUX_ALTO': (20, False),
    'REG_B': (6, False), 'REG_A': (20, False),
    'ALU_BAJA': (6, False), 'ALU_ALTA': (22, False),
    'REG_S': (10, False), 'BUF': (25, False),
}


def construir(colocacion=None):
    colocacion = colocacion or COLOCACION
    m = Montaje()
    usados_mega = set()

    def chip(ref, nombre, pinout, bb, _fila, fase, rol):
        fila1, girado = colocacion[ref]
        c = Chip(ref, nombre, pinout, bb, fila1, fase, rol, girado)
        m.chips[ref] = c
        for p in range(1, pinout.pines + 1):
            m.ocupar(c.agujero(p), 0, FIN, f'{ref} pin {p}')
        return c

    def pieza(ref, tipo, valor, patas, fase, retirar=None, nota=''):
        for ag in patas:
            if ag.riel:
                continue            # ya reservado por riel()
            m.ocupar(ag, fase, retirar if retirar is not None else FIN, ref)
        m.piezas.append(Pieza(ref, tipo, valor, tuple(patas), fase, retirar, nota))

    def libre_en_tira(candidatos, ini, fin, quien):
        for ag in candidatos:
            if m.libre(ag, ini, fin):
                m.ocupar(ag, ini, fin, quien)
                return ag
        raise ValueError(f'sin agujero libre (fases {ini}-{fin}) para {quien}: '
                         f'{[str(c) for c in candidatos]}')

    def riel(bb, r, x_deseada, quien, ini=0, fin=FIN):
        orden = sorted(X_RIEL, key=lambda x: (abs(x - x_deseada), x))
        return libre_en_tira([Agujero(bb, x, riel=r) for x in orden], ini, fin, quien)

    def punta(ep, ini, fin, quien):
        """Convierte un extremo lógico en un agujero concreto."""
        kind = ep[0]
        if kind == 'pin':
            _, ref, senal = ep
            c = m.chips[ref]
            pin = senal if isinstance(senal, int) else c.pinout.pin_de(senal)
            return libre_en_tira(c.libres(pin), ini, fin, quien)
        if kind == 'tira':
            _, bb, fila, cols = ep
            return libre_en_tira([Agujero(bb, fila, c) for c in cols], ini, fin, quien)
        if kind == 'riel':
            _, bb, r, x = ep
            return riel(bb, r, x, quien, ini, fin)
        if kind == 'mega':
            p = ep[1]
            if p != 'GND' and p in usados_mega:
                raise ValueError(f'pin {p} del Mega usado dos veces')
            usados_mega.add(p)
            return PinMega(p)
        raise ValueError(ep)

    def cable(a, b, color, fase, que, red, retirar=None, condicional=''):
        n = len(m.cables) + 1
        fin = retirar if retirar is not None else FIN
        ag_a = punta(a, fase, fin, f'cable {n}')
        ag_b = punta(b, fase, fin, f'cable {n}')
        m.cables.append(Cable(n, ag_a, ag_b, color, fase, que, red, retirar, condicional))

    # ── Colocación de chips ──────────────────────────────────────────────
    # BB1: mux. BB2: registros A y B + zona de pruebas. BB3: ALU. BB4: salida.
    chip('MUX_BAJO', 'MUX BAJO', LS157, 'BB1', 12, 4, 'mux 2:1 bits 0-3')
    chip('MUX_ALTO', 'MUX ALTO', LS157, 'BB1', 30, 4, 'mux 2:1 bits 4-7')
    chip('REG_A', 'REG A', LS273, 'BB2', 10, 3, 'registro A')
    chip('REG_B', 'REG B', LS273, 'BB2', 28, 3, 'registro B')
    chip('ALU_BAJA', 'ALU BAJA', LS181, 'BB3', 10, 2, 'ALU bits 0-3')
    chip('ALU_ALTA', 'ALU ALTA', LS181, 'BB3', 30, 2, 'ALU bits 4-7')
    chip('REG_S', 'REG SALIDA', LS273, 'BB4', 8, 1, 'registro de salida')
    chip('BUF', '74LS244', LS244, 'BB4', 24, 1, 'buffer de los LEDs')

    # ── Fase 0: alimentación ─────────────────────────────────────────────
    # Cada protoboard: + superior ↔ + inferior y − ↔ − en las dos puntas.
    # Entre protoboards vecinas: rieles inferiores de la de arriba ↔ rieles
    # superiores de la de abajo, también en las dos puntas.
    for bb in PROTOBOARDS:
        for x in (X_RIEL[0], X_RIEL[-1]):
            cable(('riel', bb, 'T+', x), ('riel', bb, 'B+', x), 'rojo', 0,
                  f'{bb}: une + superior con + inferior', 'VCC')
            cable(('riel', bb, 'T-', x + 1), ('riel', bb, 'B-', x + 1), 'negro', 0,
                  f'{bb}: une − superior con − inferior', 'GND')
    for arriba, abajo in zip(PROTOBOARDS, PROTOBOARDS[1:]):
        for x in (X_RIEL[1], X_RIEL[-2]):
            cable(('riel', arriba, 'B+', x + 1), ('riel', abajo, 'T+', x + 1), 'rojo', 0,
                  f'+ de {arriba} con + de {abajo}', 'VCC')
            cable(('riel', arriba, 'B-', x), ('riel', abajo, 'T-', x), 'negro', 0,
                  f'− de {arriba} con − de {abajo}', 'GND')

    # Entrada de la fuente (adaptador jack → bornera) y electrolítico, en BB2.
    ent_p = riel('BB2', 'B+', 21, 'entrada fuente +')
    ent_n = riel('BB2', 'B-', 21, 'entrada fuente −')
    m.piezas.append(Pieza('FUENTE', 'fuente', '5 V ≥1 A', (ent_p, ent_n), 0,
                          nota='cable rojo de la bornera al riel +, negro al riel −'))
    pieza('C_ENT', 'electrolitico', '100 µF 16 V',
          (riel('BB2', 'B+', 24, 'C_ENT +'), riel('BB2', 'B-', 24, 'C_ENT −')), 0,
          nota='pata larga (+) al riel +, franja (−) al riel −')

    # ── Alimentación y desacople de cada chip (en su fase) ──────────────
    for c in m.chips.values():
        vcc = c.pinout.pin_de('VCC')
        gnd = c.pinout.pin_de('GND')
        x_vcc = c.agujero(vcc).fila
        x_gnd = c.agujero(gnd).fila
        cable(('pin', c.ref, vcc), ('riel', c.bb, 'T+', x_vcc), 'rojo', c.fase,
              f'{c.nombre}: VCC (pin {vcc}) a +5 V', 'VCC')
        cable(('pin', c.ref, gnd), ('riel', c.bb, 'B-', x_gnd), 'negro', c.fase,
              f'{c.nombre}: GND (pin {gnd}) a tierra', 'GND')
        pieza(f'C_{c.ref}', 'cap', '0.1 µF (104)',
              (riel(c.bb, 'T+', x_vcc + 1, f'C_{c.ref}'), riel(c.bb, 'T-', x_vcc + 1, f'C_{c.ref}')),
              c.fase, nota=f'desacople de {c.nombre}, pegado a su VCC')

    # Habilitaciones que van fijas a GND.
    for ref in ('MUX_BAJO', 'MUX_ALTO'):
        c = m.chips[ref]
        cable(('pin', ref, 'G'), ('riel', c.bb, 'T-', c.agujero(15).fila), 'negro', c.fase,
              f'{c.nombre}: G̅ (pin 15) a GND — mux siempre habilitado', 'GND')
    buf = m.chips['BUF']
    cable(('pin', 'BUF', '1G'), ('riel', 'BB4', 'B-', buf.agujero(1).fila), 'negro', 1,
          '74LS244: 1G̅ (pin 1) a GND — bits 0-3 siempre habilitados', 'GND')
    cable(('pin', 'BUF', '2G'), ('riel', 'BB4', 'T-', buf.agujero(19).fila), 'negro', 1,
          '74LS244: 2G̅ (pin 19) a GND — bits 4-7 siempre habilitados', 'GND')

    # ── Fase 1: salida ───────────────────────────────────────────────────
    # LEDs: bit 7 a la izquierda. Cada bit usa dos filas: L (señal) y L+1
    # (cátodo). La resistencia cruza el canal de d a g en la fila L; el LED va
    # de h L (ánodo, pata larga) a h L+1 (cátodo); un puente negro de j L+1 al
    # riel − superior.
    FILA_LED0 = 38
    filas_led = {}
    for i, bit in enumerate(range(7, -1, -1)):
        L = FILA_LED0 + 3 * i
        filas_led[bit] = L
        pieza(f'R_LED{bit}', 'resistencia', '220 Ω',
              (Agujero('BB4', L, 'd'), Agujero('BB4', L, 'g')), 1,
              nota=f'bit {bit}: cruza el canal central')
        pieza(f'LED{bit}', 'led', 'LED rojo/verde/amarillo',
              (Agujero('BB4', L, 'h'), Agujero('BB4', L + 1, 'h')), 1,
              nota=f'bit {bit}: pata larga (ánodo) en h{L}, pata corta (cátodo) en h{L + 1}')
        cable(('tira', 'BB4', L + 1, 'ji'), ('riel', 'BB4', 'T-', L + 1), 'negro', 1,
              f'LED bit {bit}: cátodo a GND', 'GND')
        a_in, y_out = CANAL_244[bit]
        cable(('pin', 'REG_S', f'Q{bit}'), ('pin', 'BUF', a_in), 'gris', 1,
              f'REG SALIDA Q{bit} → 74LS244 {a_in}', f'QS{bit}')
        cable(('pin', 'BUF', y_out), ('tira', 'BB4', L, 'abc'), 'gris', 1,
              f'74LS244 {y_out} → resistencia del LED bit {bit}', f'LED{bit}')

    # ── Zona de pruebas (temporal) en BB2, filas 44-60 ─────────────────
    # Dip switch de 8: interruptor k une e(R_k) con f(R_k). Lado f a GND,
    # lado e con pull-up de 1 kΩ al riel + inferior: OFF = 1, ON = 0.
    FILA_DIP = 44
    pieza('DIP', 'dip', 'dip switch de 8',
          tuple(Agujero('BB2', FILA_DIP + k, 'e') for k in range(8)) +
          tuple(Agujero('BB2', FILA_DIP + k, 'f') for k in range(8)),
          1, retirar=4, nota='interruptor 1 en la fila 44 = bit 0; ON = 0, OFF = 1')
    for k in range(8):
        R = FILA_DIP + k
        pieza(f'R_PU{k}', 'resistencia', '1 kΩ', (Agujero('BB2', R, 'a'), riel('BB2', 'B+', R, f'R_PU{k}', 1, 4)),
              1, retirar=4, nota=f'pull-up del bit {k} del dip switch')
        cable(('tira', 'BB2', R, 'jihg'), ('riel', 'BB2', 'T-', R), 'temporal', 1,
              f'dip switch bit {k}: lado común a GND', 'GND', retirar=4)
    FILA_BOTON = 55
    pieza('BOTON', 'pulsador', 'pulsador 4 patas',
          (Agujero('BB2', FILA_BOTON, 'e'), Agujero('BB2', FILA_BOTON + 2, 'e'),
           Agujero('BB2', FILA_BOTON, 'f'), Agujero('BB2', FILA_BOTON + 2, 'f')),
          1, retirar=4, nota='cruza el canal; verifica con el multímetro que une e↔f solo al presionar')
    pieza('R_BOTON', 'resistencia', '1 kΩ',
          (Agujero('BB2', FILA_BOTON, 'a'), riel('BB2', 'B+', FILA_BOTON, 'R_BOTON', 1, 4)),
          1, retirar=4, nota='pull-up del reloj manual: suelto = 1, presionado = 0')
    cable(('tira', 'BB2', FILA_BOTON, 'jihg'), ('riel', 'BB2', 'T-', FILA_BOTON), 'temporal', 1,
          'pulsador: lado f a GND', 'GND', retirar=4)
    DIP = lambda k: ('tira', 'BB2', FILA_DIP + k, 'bcd')
    BOTON = ('tira', 'BB2', FILA_BOTON, 'bcd')

    # Fase 1: el dip switch carga REG SALIDA; el botón es su reloj.
    for k in range(8):
        cable(DIP(k), ('pin', 'REG_S', f'D{k}'), 'temporal', 1,
              f'PRUEBA: dip bit {k} → REG SALIDA D{k}', f'F{k}', retirar=1)
    cable(BOTON, ('pin', 'REG_S', 'CLK'), 'temporal', 1,
          'PRUEBA: pulsador → reloj de REG SALIDA', 'CLK_S', retirar=4)
    cable(('pin', 'REG_S', 'CLR'), ('riel', 'BB4', 'B+', m.chips['REG_S'].fila1), 'temporal', 1,
          'PRUEBA: CLEAR de REG SALIDA a + (inactivo)', 'CLEAR', retirar=2)

    # ── Fase 2: ALU ──────────────────────────────────────────────────────
    for s in ('S0', 'S1', 'S2', 'S3', 'M'):
        cable(('pin', 'ALU_BAJA', s), ('pin', 'ALU_ALTA', s), 'morado', 2,
              f'{s}: ALU BAJA → ALU ALTA (control en paralelo)', s)
    cable(('pin', 'ALU_BAJA', 'CN4'), ('pin', 'ALU_ALTA', 'CN'), 'morado', 2,
          'Acarreo: C̄n+4 de ALU BAJA (pin 16) → C̄n de ALU ALTA (pin 7)', 'CARRY_MED')
    for k in range(8):
        alu = 'ALU_BAJA' if k < 4 else 'ALU_ALTA'
        cable(('pin', alu, f'F{k % 4}'), ('pin', 'REG_S', f'D{k}'), 'azul', 2,
              f'F{k}: {m.chips[alu].nombre} F{k % 4} → REG SALIDA D{k}', f'F{k}')
    for k in range(8):
        alu = 'ALU_BAJA' if k < 4 else 'ALU_ALTA'
        cable(DIP(k), ('pin', alu, f'A{k % 4}'), 'temporal', 2,
              f'PRUEBA: dip bit {k} → A{k} ({m.chips[alu].nombre} A{k % 4})', f'QA{k}', retirar=2)
        cable(('pin', alu, f'B{k % 4}'), ('riel', 'BB3', 'T+' if k % 4 else 'B+', m.chips[alu].agujero(
            m.chips[alu].pinout.pin_de(f'B{k % 4}')).fila), 'temporal', 2,
              f'PRUEBA: B{k} a un riel (+ = 1, − = 0; se mueve en cada caso)', f'QB{k}', retirar=2)
    for s in ('S0', 'S1', 'S2', 'S3', 'M', 'CN'):
        c = m.chips['ALU_BAJA']
        cable(('pin', 'ALU_BAJA', s), ('riel', 'BB3', 'B+', c.agujero(c.pinout.pin_de(s)).fila),
              'temporal', 2, f'PRUEBA: {s} de ALU BAJA a un riel (se mueve según la operación)',
              s, retirar=4)

    # ── Fase 3: registros ───────────────────────────────────────────────
    for k in range(8):
        alu = 'ALU_BAJA' if k < 4 else 'ALU_ALTA'
        cable(('pin', 'REG_A', f'Q{k}'), ('pin', alu, f'A{k % 4}'), 'verde', 3,
              f'REG A Q{k} → {m.chips[alu].nombre} A{k % 4}', f'QA{k}')
        cable(('pin', 'REG_B', f'Q{k}'), ('pin', alu, f'B{k % 4}'), 'blanco', 3,
              f'REG B Q{k} → {m.chips[alu].nombre} B{k % 4}', f'QB{k}')
    cable(('pin', 'REG_A', 'CLR'), ('pin', 'REG_B', 'CLR'), 'cafe', 3,
          'CLEAR: REG A → REG B', 'CLEAR')
    cable(('pin', 'REG_B', 'CLR'), ('pin', 'REG_S', 'CLR'), 'cafe', 3,
          'CLEAR: REG B → REG SALIDA', 'CLEAR')
    cable(('pin', 'REG_A', 'CLR'), ('riel', 'BB2', 'B+', m.chips['REG_A'].fila1), 'temporal', 3,
          'PRUEBA: CLEAR a + (inactivo) mientras no esté el Mega', 'CLEAR', retirar=4)
    cable(BOTON, ('pin', 'REG_A', 'CLK'), 'temporal', 3,
          'PRUEBA: pulsador → reloj de REG A (conecta solo el reloj que vayas a pulsar)', 'CLK_A', retirar=4)
    cable(BOTON, ('pin', 'REG_B', 'CLK'), 'temporal', 3,
          'PRUEBA: pulsador → reloj de REG B (conecta solo el reloj que vayas a pulsar)', 'CLK_B', retirar=4)
    for k in range(8):
        cable(DIP(k), ('pin', 'REG_A', f'D{k}'), 'temporal', 3,
              f'PRUEBA: dip bit {k} → REG A D{k}', f'YA{k}', retirar=3)
        cable(DIP(k), ('pin', 'REG_B', f'D{k}'), 'temporal', 3,
              f'PRUEBA: dip bit {k} → REG B D{k}', f'D{k}', retirar=4)

    # ── Fase 4: mux ──────────────────────────────────────────────────────
    for k in range(8):
        mux = 'MUX_BAJO' if k < 4 else 'MUX_ALTO'
        alu = 'ALU_BAJA' if k < 4 else 'ALU_ALTA'
        ch = CANAL_157[k % 4]
        cable(('pin', mux, f'{ch}Y'), ('pin', 'REG_A', f'D{k}'), 'naranja', 4,
              f'{m.chips[mux].nombre} {ch}Y → REG A D{k}', f'YA{k}')
        cable(('pin', alu, f'F{k % 4}'), ('pin', mux, f'{ch}B'), 'azul', 4,
              f'F{k}: {m.chips[alu].nombre} F{k % 4} → {m.chips[mux].nombre} {ch}B', f'F{k}')
        cable(('pin', 'REG_B', f'D{k}'), ('pin', mux, f'{ch}A'), 'amarillo', 4,
              f'D{k}: REG B D{k} → {m.chips[mux].nombre} {ch}A', f'D{k}')
    cable(('pin', 'MUX_BAJO', 'SEL'), ('pin', 'MUX_ALTO', 'SEL'), 'cafe', 4,
          'SEL: MUX BAJO → MUX ALTO', 'SEL')
    cable(('pin', 'MUX_BAJO', 'SEL'), ('riel', 'BB1', 'B-', m.chips['MUX_BAJO'].fila1), 'temporal', 4,
          'PRUEBA: SEL a un riel (− = dip switch, + = resultado de la ALU)', 'SEL', retirar=4)

    # ── Fase 5: Arduino Mega ────────────────────────────────────────────
    for k in range(8):
        cable(('mega', str(22 + k)), ('pin', 'REG_B', f'D{k}'), 'amarillo', 5,
              f'D{k}: Mega pin {22 + k} → REG B D{k}', f'D{k}')
    for k in range(8):
        cable(('pin', 'REG_S', f'D{k}'), ('mega', str(37 - k)), 'azul', 5,
              f'F{k}: REG SALIDA D{k} (mismo nodo que F{k}) → Mega pin {37 - k}', f'F{k}')
    for s, p in (('S0', 49), ('S1', 48), ('S2', 47), ('S3', 46), ('M', 45), ('CN', 44)):
        cable(('mega', str(p)), ('pin', 'ALU_BAJA', s), 'morado', 5,
              f'{s}: Mega pin {p} → ALU BAJA', s)
    cable(('pin', 'ALU_ALTA', 'CN4'), ('mega', '2'), 'morado', 5,
          'Acarreo final: C̄n+4 de ALU ALTA (pin 16) → Mega pin 2', 'CARRY')
    cable(('mega', '41'), ('pin', 'REG_A', 'CLK'), 'cafe', 5, 'CLK A: Mega pin 41 → REG A pin 11', 'CLK_A')
    cable(('mega', '40'), ('pin', 'REG_B', 'CLK'), 'cafe', 5, 'CLK B: Mega pin 40 → REG B pin 11', 'CLK_B')
    cable(('mega', '7'), ('pin', 'REG_S', 'CLK'), 'cafe', 5, 'CLK S: Mega pin 7 → REG SALIDA pin 11', 'CLK_S')
    cable(('mega', '38'), ('pin', 'REG_A', 'CLR'), 'cafe', 5, 'CLEAR: Mega pin 38 → REG A pin 1', 'CLEAR')
    cable(('mega', '39'), ('pin', 'MUX_BAJO', 'SEL'), 'cafe', 5, 'SEL: Mega pin 39 → MUX BAJO pin 1', 'SEL')
    cable(('mega', 'GND'), ('riel', 'BB3', 'T-', 4), 'negro', 5,
          'GND común: Mega GND → riel − (sin esto nada funciona)', 'GND')

    m.filas_led = filas_led
    m.fila_dip = FILA_DIP
    m.fila_boton = FILA_BOTON
    return m


MONTAJE = construir()
