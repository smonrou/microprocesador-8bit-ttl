"""Construye las páginas HTML (artifacts) de la guía de montaje.

    python -m montaje.paginas            # escribe montaje/salida/pagina_*.html

Cada fase es una página: plano general, acercamiento por chip, pasos con
casillas, prueba con campo de resultado y fallas conocidas. Las casillas y
resultados se guardan en la base de datos del artifact (capacidad db), con
respaldo en el navegador si la base no está disponible.

Los enlaces entre páginas salen de montaje/salida/urls.json (se llena al
publicar).
"""

import html
import json
import os
from collections import Counter, OrderedDict

from montaje.netlist import MONTAJE, FASES, COLORES, COLOR_TEMPORAL, PinMega
from montaje.generar import (SALIDA, escena, vista_chip, cables_de_chip, largo_cm,
                             describir, datos)
from montaje.guias import GUIAS

TITULOS = {0: 'Fase 0 Alimentación', 1: 'Fase 1 Salida', 2: 'Fase 2 ALU', 3: 'Fase 3 Registros',
           4: 'Fase 4 Mux y PC', 5: 'Fase 5 Arduino Mega', 6: 'Fase 6 Cierre'}
CORTOS = {0: 'Alimentación', 1: 'Salida', 2: 'ALU', 3: 'Registros', 4: 'Mux y PC', 5: 'Mega', 6: 'Cierre'}
NOMBRE_COLOR = {'rojo': 'Rojo', 'negro': 'Negro', 'amarillo': 'Amarillo', 'azul': 'Azul', 'verde': 'Verde',
                'blanco': 'Blanco', 'naranja': 'Naranja', 'gris': 'Gris', 'morado': 'Morado',
                'cafe': 'Café', 'temporal': 'Dupont de prueba'}
ORDEN_COLOR = ['rojo', 'negro', 'gris', 'morado', 'azul', 'verde', 'blanco', 'cafe', 'naranja',
               'amarillo', 'temporal']
TIPO_PIEZA = {'cap': 'Capacitor cerámico', 'electrolitico': 'Capacitor electrolítico', 'led': 'LED',
              'resistencia': 'Resistencia', 'dip': 'Dip switch', 'pulsador': 'Pulsador',
              'fuente': 'Fuente'}


def e(s):
    return html.escape(str(s), quote=True)


def hex_color(c):
    return COLOR_TEMPORAL if c == 'temporal' else COLORES[c][0]


def urls():
    try:
        with open(os.path.join(SALIDA, 'urls.json'), encoding='utf-8') as fh:
            return json.load(fh)
    except FileNotFoundError:
        return {}


CSS = r"""
:root{
  --ink:#1b2420; --ink-soft:#4c5a52; --paper:#f1f3ee; --surface:#e6e9e1; --card:#fafbf8;
  --line:#c7cdc0; --accent:#c4791f; --accent-soft:#f0e3cc; --signal:#2f7d78; --signal-soft:#dbe9e6;
  --danger:#a8432e; --danger-soft:#f3dfd7; --ok:#2e7d4f; --ok-soft:#dcefe2; --temp:#c2317f;
  --board:#fbfaf6;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --ink:#e7ece4; --ink-soft:#aab5a9; --paper:#111713; --surface:#1a211b; --card:#151b16;
    --line:#343f35; --accent:#e6a24c; --accent-soft:#3a2f1c; --signal:#5fb8b0; --signal-soft:#1b2f2c;
    --danger:#e2795d; --danger-soft:#3a2420; --ok:#6cc58e; --ok-soft:#18301f; --temp:#ef6fb3;
    --board:#e9e7df;
  }
}
:root[data-theme="dark"]{
  --ink:#e7ece4; --ink-soft:#aab5a9; --paper:#111713; --surface:#1a211b; --card:#151b16;
  --line:#343f35; --accent:#e6a24c; --accent-soft:#3a2f1c; --signal:#5fb8b0; --signal-soft:#1b2f2c;
  --danger:#e2795d; --danger-soft:#3a2420; --ok:#6cc58e; --ok-soft:#18301f; --temp:#ef6fb3;
  --board:#e9e7df;
}
*{box-sizing:border-box}
html{color-scheme:light dark}
body{margin:0;background:var(--paper);color:var(--ink);font-family:'IBM Plex Sans',system-ui,sans-serif;
  line-height:1.55;padding-inline:16px;padding-block:0 80px}
h1,h2,h3{font-family:'IBM Plex Sans Condensed',system-ui,sans-serif;font-weight:700;text-wrap:balance;margin:0}
code,.mono{font-family:'IBM Plex Mono',ui-monospace,monospace;font-variant-numeric:tabular-nums}
code{font-size:.92em;background:var(--surface);padding:1px 5px;border-radius:3px}
a{color:var(--accent)}
.wrap{max-width:1120px;margin:0 auto}
header.top{padding:36px 0 22px;border-bottom:1px solid var(--line)}
.eyebrow{font-family:'IBM Plex Mono',monospace;font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--accent)}
h1{font-size:clamp(28px,4.4vw,42px);margin:6px 0 10px}
.lede{font-size:17px;color:var(--ink-soft);max-width:70ch;margin:0}
nav.fases{display:flex;flex-wrap:wrap;gap:6px;margin-top:18px}
nav.fases a,nav.fases span{font-family:'IBM Plex Mono',monospace;font-size:12.5px;padding:4px 10px;border:1px solid var(--line);
  border-radius:99px;color:var(--ink-soft);text-decoration:none}
nav.fases .aqui{border-color:var(--accent);color:var(--accent);font-weight:600}
.progreso{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:var(--paper);padding:10px 0;border-bottom:1px solid var(--line);
  display:flex;align-items:center;gap:14px;font-size:13px}
.barra{flex:1;height:8px;background:var(--surface);border-radius:99px;overflow:hidden}
.barra i{display:block;height:100%;width:0;background:var(--ok);transition:width .3s}
.estado-db{font-family:'IBM Plex Mono',monospace;font-size:11.5px;color:var(--ink-soft)}
section{padding-top:40px}
section>h2{font-size:23px;display:flex;align-items:baseline;gap:10px}
section>h2 .n{font-family:'IBM Plex Mono',monospace;font-size:14px;color:var(--accent)}
.dek{color:var(--ink-soft);max-width:72ch;margin:6px 0 16px}
.callout{display:flex;gap:12px;padding:12px 16px;border-radius:4px;margin:10px 0;font-size:14.5px;max-width:80ch}
.callout.warn{background:var(--danger-soft);border-left:3px solid var(--danger)}
.callout.note{background:var(--signal-soft);border-left:3px solid var(--signal)}
.callout .m{font-family:'IBM Plex Mono',monospace;font-weight:700;flex-shrink:0}
.callout.warn .m{color:var(--danger)} .callout.note .m{color:var(--signal)}
.tabla{overflow-x:auto;border:1px solid var(--line);border-radius:4px;margin:12px 0 18px;background:var(--card)}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{padding:7px 10px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
thead th{background:var(--surface);font-family:'IBM Plex Sans Condensed',sans-serif;font-weight:600;font-size:12px;
  letter-spacing:.04em;text-transform:uppercase;color:var(--ink-soft);white-space:nowrap}
tbody tr:last-child td{border-bottom:none}
tr.hecho td{opacity:.55} tr.hecho td:first-child{opacity:1}
td.num{font-family:'IBM Plex Mono',monospace;font-weight:700;white-space:nowrap}
td.ag{font-family:'IBM Plex Mono',monospace;white-space:nowrap;font-weight:600}
td.ag small,td.que small{display:block;font-weight:400;color:var(--ink-soft);font-family:'IBM Plex Sans',sans-serif;font-size:12.5px;white-space:normal}
td.cm{font-family:'IBM Plex Mono',monospace;white-space:nowrap;text-align:right}
.sw{display:inline-flex;align-items:center;gap:6px;white-space:nowrap}
.sw i{width:26px;height:9px;border-radius:5px;border:1px solid rgba(0,0,0,.45);display:inline-block}
.sw.t i{background-image:repeating-linear-gradient(90deg,var(--temp) 0 6px,transparent 6px 9px)!important}
.tag{font-family:'IBM Plex Mono',monospace;font-size:11px;padding:1px 6px;border-radius:99px;background:var(--danger-soft);color:var(--temp);white-space:nowrap}
input[type=checkbox]{width:20px;height:20px;accent-color:var(--ok);cursor:pointer}
input[type=text]{width:100%;min-width:130px;font:inherit;font-size:13.5px;padding:5px 7px;border:1px solid var(--line);border-radius:3px;background:var(--paper);color:var(--ink)}
input:focus-visible,button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
figure{margin:14px 0}
.plano{border:1px solid var(--line);border-radius:4px;background:var(--board);overflow:auto;max-height:82vh}
.plano svg{display:block;width:100%;height:auto}
.plano.real svg{width:1320px;max-width:none}
.botones{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}
button{font:inherit;font-size:13px;padding:5px 12px;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:4px;cursor:pointer}
button:hover{border-color:var(--accent)}
figcaption{font-size:13px;color:var(--ink-soft);margin-top:8px;max-width:80ch}
.leyenda{display:flex;flex-wrap:wrap;gap:8px 16px;font-size:13px;margin:10px 0}
.chips{display:grid;gap:18px}
.chipcard{border:1px solid var(--line);border-radius:4px;background:var(--card);padding:14px}
.chipcard h3{font-size:18px;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.chipcard .datos{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:6px 18px;margin:10px 0;font-size:14px}
.chipcard .datos b{font-family:'IBM Plex Mono',monospace}
.chipcard .plano{max-height:none}
ul.lista-cables{list-style:none;padding:0;margin:0 0 6px;display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:4px 18px;font-size:13.5px}
ul.lista-cables li{display:flex;flex-wrap:wrap;align-items:center;gap:6px}
ol.manual{padding-left:0;list-style:none;display:grid;gap:8px;max-width:80ch}
ol.manual li{display:flex;gap:10px;align-items:flex-start}
.material{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}
.material .tabla{margin:0}
footer{margin-top:48px;padding-top:16px;border-top:1px solid var(--line);font-size:13px;color:var(--ink-soft)}
@media (max-width:640px){ th,td{padding:6px 7px} .lede{font-size:15.5px} }
@media (prefers-reduced-motion:reduce){ .barra i{transition:none} }
"""

JS = r"""
(function(){
  const FASE = document.body.dataset.fase;
  const CLAVE = 'montaje-fase-' + FASE;
  let estado = {marcas:{}, resultados:{}};
  let db = null, ref = null, pendiente = null, escribiendo = false;
  const info = document.getElementById('estado-db');

  function leerLocal(){ try{ const s = localStorage.getItem(CLAVE); if(s) return JSON.parse(s); }catch(e){} return null; }
  function guardarLocal(){ try{ localStorage.setItem(CLAVE, JSON.stringify(estado)); }catch(e){} }

  function pintar(){
    let total = 0, hechos = 0;
    document.querySelectorAll('input[type=checkbox][data-id]').forEach(cb => {
      const id = cb.dataset.id; cb.checked = !!estado.marcas[id];
      const tr = cb.closest('tr, li'); if(tr) tr.classList.toggle('hecho', cb.checked);
      total++; if(cb.checked) hechos++;
    });
    document.querySelectorAll('input[type=text][data-id]').forEach(t => {
      if(document.activeElement !== t) t.value = estado.resultados[t.dataset.id] || '';
    });
    const pct = total ? Math.round(100*hechos/total) : 0;
    document.getElementById('barra').style.width = pct + '%';
    document.getElementById('cuenta').textContent = hechos + ' de ' + total + ' marcados';
  }

  async function escribir(){
    guardarLocal();
    if(!ref) return;
    if(escribiendo){ pendiente = true; return; }
    escribiendo = true;
    try{ await ref.set({marcas: estado.marcas, resultados: estado.resultados, actualizado: new Date().toISOString()});
         info.textContent = 'guardado en el artifact'; }
    catch(e){ info.textContent = 'no se pudo guardar en el artifact (queda en este navegador)'; }
    escribiendo = false;
    if(pendiente){ pendiente = false; escribir(); }
  }
  let t = null;
  function programar(){ clearTimeout(t); t = setTimeout(escribir, 500); }

  document.addEventListener('change', ev => {
    const el = ev.target;
    if(el.matches('input[type=checkbox][data-id]')){ if(el.checked) estado.marcas[el.dataset.id] = true; else delete estado.marcas[el.dataset.id]; pintar(); programar(); }
  });
  document.addEventListener('input', ev => {
    const el = ev.target;
    if(el.matches('input[type=text][data-id]')){ const v = el.value.trim(); if(v) estado.resultados[el.dataset.id] = el.value; else delete estado.resultados[el.dataset.id]; programar(); }
  });
  document.querySelectorAll('[data-escala]').forEach(b => b.addEventListener('click', () => {
    const p = document.getElementById(b.dataset.escala); p.classList.toggle('real');
    b.textContent = p.classList.contains('real') ? 'Ajustar al ancho' : 'Ver a tamaño real';
  }));

  const local = leerLocal(); if(local) estado = Object.assign({marcas:{}, resultados:{}}, local);
  pintar();

  if(window.claude && window.claude.use){
    window.claude.use('db').then(d => {
      if(!d){ info.textContent = 'guardado solo en este navegador'; return; }
      db = d; ref = db.doc('avance/fase' + FASE);
      info.textContent = 'sincronizando…';
      ref.onSnapshot(snap => {
        if(snap.exists){ const v = snap.data(); estado = {marcas: Object.assign({}, v.marcas || {}), resultados: Object.assign({}, v.resultados || {})}; guardarLocal(); pintar(); }
        info.textContent = 'guardado en el artifact';
      }, err => { info.textContent = 'sin conexión a la base (queda en este navegador)'; });
    }).catch(() => { info.textContent = 'guardado solo en este navegador'; });
  } else { info.textContent = 'guardado solo en este navegador'; }
})();
"""


def fuentes():
    return ('<link rel="preconnect" href="https://fonts.googleapis.com">'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700'
            '&family=IBM+Plex+Sans+Condensed:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap">')


def nav(fase_actual, u):
    items = []
    idx = u.get('indice')
    items.append(f'<a href="{e(idx)}">Índice</a>' if idx else '<span>Índice</span>')
    for f in FASES:
        texto = f'{f} · {CORTOS[f]}'
        if f == fase_actual:
            items.append(f'<span class="aqui" aria-current="page">{texto}</span>')
        elif u.get(str(f)):
            items.append(f'<a href="{e(u[str(f)])}">{texto}</a>')
        else:
            items.append(f'<span>{texto}</span>')
    return '<nav class="fases" aria-label="Fases">' + ''.join(items) + '</nav>'


def swatch(color):
    t = ' t' if color == 'temporal' else ''
    return f'<span class="sw{t}"><i style="background:{hex_color(color)}"></i>{NOMBRE_COLOR[color]}</span>'


def callouts(lista):
    out = []
    for tipo, texto in lista:
        marca = '!' if tipo == 'warn' else 'i'
        out.append(f'<div class="callout {tipo}"><span class="m">{marca}</span><div>{texto}</div></div>')
    return ''.join(out)


def punta(ag):
    if isinstance(ag, PinMega):
        return f'<td class="ag">{e(ag)}<small>cabecera del Arduino</small></td>'
    return f'<td class="ag">{e(ag)}<small>{e(describir(ag))}</small></td>'


def tabla_cables(cables):
    filas = []
    for c in cables:
        tag = ' <span class="tag">prueba</span>' if c.temporal else ''
        filas.append(
            f'<tr><td><input type="checkbox" data-id="cable-{c.n}" aria-label="Cable {c.n} puesto"></td>'
            f'<td class="num">#{c.n}</td><td>{swatch(c.color)}</td>{punta(c.a)}{punta(c.b)}'
            f'<td class="cm">{largo_cm(c):.1f} cm</td><td class="que">{e(c.que)}{tag}</td></tr>')
    return ('<div class="tabla"><table><thead><tr><th></th><th>#</th><th>Color</th><th>Desde</th><th>Hasta</th>'
            '<th>Largo</th><th>Qué es</th></tr></thead><tbody>' + ''.join(filas) + '</tbody></table></div>')


def grupos_cables(cables):
    """Agrupa por función en el orden en que conviene ponerlos."""
    g = OrderedDict()
    nombres = {'rojo': 'Alimentación +5 V', 'negro': 'Tierra y habilitaciones a GND'}
    for col in ORDEN_COLOR:
        sel = [c for c in cables if c.color == col]
        if sel:
            titulo = nombres.get(col) or (COLORES[col][1] if col in COLORES else
                                          'Cables de prueba (dupont, se retiran al terminar la fase)')
            g[col] = (titulo, sel)
    return g


def material(fase):
    m = MONTAJE
    chips = [c for c in m.chips.values() if c.fase == fase]
    piezas = [p for p in m.piezas if p.fase == fase and p.tipo != 'fuente']
    cables = [c for c in m.cables if c.fase == fase]
    bloques = []
    if chips:
        cnt = Counter(c.pinout.nombre for c in chips)
        filas = ''.join(f'<tr><td class="num">{n}</td><td>{e(k)}</td></tr>' for k, n in cnt.items())
        bloques.append(f'<div class="tabla"><table><thead><tr><th>Cant.</th><th>Integrado</th></tr></thead><tbody>{filas}</tbody></table></div>')
    if piezas:
        cnt = Counter((TIPO_PIEZA[p.tipo], p.valor, p.retirar is not None) for p in piezas)
        filas = ''.join(f'<tr><td class="num">{n}</td><td>{e(t)}</td><td>{e(v)}{" <span class=tag>prueba</span>" if tmp else ""}</td></tr>'
                        for (t, v, tmp), n in cnt.items())
        bloques.append(f'<div class="tabla"><table><thead><tr><th>Cant.</th><th>Pieza</th><th>Valor</th></tr></thead><tbody>{filas}</tbody></table></div>')
    if cables:
        por = OrderedDict()
        for col in ORDEN_COLOR:
            sel = [c for c in cables if c.color == col]
            if sel:
                por[col] = (len(sel), sum(largo_cm(c) for c in sel))
        filas = ''.join(f'<tr><td>{swatch(col)}</td><td class="num">{n}</td><td class="cm">{cm:.0f} cm</td></tr>'
                        for col, (n, cm) in por.items())
        bloques.append(f'<div class="tabla"><table><thead><tr><th>Cable</th><th>Cant.</th><th>Total</th></tr></thead><tbody>{filas}</tbody></table></div>')
    return '<div class="material">' + ''.join(bloques) + '</div>'


def seccion_chips(fase):
    chips = [c for c in MONTAJE.chips.values() if c.fase == fase]
    if not chips:
        return ''
    cards = []
    for c in chips:
        x, y, w, h = vista_chip(c)
        vista = (x - 3, y, w + 6, h)
        svg = escena(fase, vista)
        en_vista = cables_de_chip(c, fase, vista)
        lista = ''
        if en_vista:
            filas_l = ''.join(
                f'<li><b class="mono">#{cab.n}</b> {swatch(cab.color)} <span class="mono">{e(ag)}</span> → '
                f'{e(describir(otro))}{" <span class=tag>prueba</span>" if cab.temporal else ""}</li>'
                for cab, ag, otro in en_vista)
            lista = (f'<p class="dek" style="margin:12px 0 6px">Cables de esta fase que llegan a este recorte '
                     f'(el número está junto a cada extremo en el dibujo):</p><ul class="lista-cables">{filas_l}</ul>')
        filas_pin = []
        for pin in range(1, c.pinout.pines + 1):
            tira = c.agujero(pin).tira()
            conex = []
            for cab in MONTAJE.cables:
                for ag, otro in ((cab.a, cab.b), (cab.b, cab.a)):
                    if not isinstance(ag, PinMega) and not ag.riel and ag.tira() == tira:
                        destino = describir(otro) if not getattr(otro, 'riel', '') else str(otro)
                        marca = ' <span class="tag">prueba</span>' if cab.temporal else ''
                        fase_txt = '' if cab.fase == fase else f' <small>(fase {cab.fase})</small>'
                        conex.append(f'{swatch(cab.color)} <b>#{cab.n}</b> {e(ag)} → {e(destino)}{marca}{fase_txt}')
            for p in (x for x in MONTAJE.piezas if len(x.patas) == 2):
                for ag, otro in ((p.patas[0], p.patas[1]), (p.patas[1], p.patas[0])):
                    if not getattr(ag, 'riel', '') and ag.tira() == tira:
                        marca = ' <span class="tag">prueba</span>' if p.retirar is not None else ''
                        fase_txt = '' if p.fase == fase else f' <small>(fase {p.fase})</small>'
                        conex.append(f'<b>{e(TIPO_PIEZA[p.tipo])} {e(p.valor)}</b> ({e(p.ref)}) '
                                     f'{e(ag)} → {e(otro)}{marca}{fase_txt}')
            tipo = c.pinout.tipo(pin)
            if not conex:
                conex = ['<span style="color:var(--ink-soft)">sin conexión (salida que no se usa)</span>'
                         if tipo in ('out', 'oc') else '<b style="color:var(--danger)">¡falta!</b>']
            filas_pin.append(f'<tr><td class="num">{pin}</td><td class="mono">{e(c.pinout.senal(pin))}</td>'
                             f'<td class="ag">{e(c.agujero(pin))}</td><td>{"<br>".join(conex)}</td></tr>')
        tabla_pines = ('<details><summary style="cursor:pointer;margin-top:10px;font-weight:600">Tabla de pines de '
                       f'{e(c.nombre)}: qué llega a cada pata (todas las fases)</summary><div class="tabla"><table><thead><tr>'
                       '<th>Pin</th><th>Señal</th><th>Agujero</th><th>Qué hay en su tira</th></tr></thead><tbody>'
                       + ''.join(filas_pin) + '</tbody></table></div></details>')
        ult_inf = c.agujero(c.mitad)
        pin_n = c.agujero(c.pinout.pines)
        ancho = ('600 mil: patas en <b>d</b> y <b>h</b>' if c.pinout.ancho == 6
                 else '300 mil: patas en <b>e</b> y <b>f</b>, a los lados del canal')
        cards.append(f'''
<div class="chipcard">
  <h3><input type="checkbox" data-id="chip-{c.ref}" aria-label="{e(c.nombre)} colocado">{e(c.nombre)}
      <span class="mono" style="font-size:14px;color:var(--ink-soft)">{e(c.pinout.nombre)} · {e(c.rol)}</span></h3>
  <div class="datos">
    <div>Protoboard<br><b>{c.bb}</b></div>
    <div>Pin 1 (punto)<br><b>{e(c.agujero(1))}</b></div>
    <div>Pin {c.mitad}<br><b>{e(ult_inf)}</b></div>
    <div>Pin {c.pinout.pines}<br><b>{e(pin_n)}</b></div>
    <div>Ancho<br>{ancho}</div>
    <div>Muesca<br>hacia la <b>fila 1</b> (izquierda)</div>
  </div>
  <div class="plano">{svg}</div>
  {lista}
  {tabla_pines}
</div>''')
    return (f'<section id="chips"><h2><span class="n">A</span>Colocar los integrados</h2>'
            f'<p class="dek">Sin fuente. Inserta cada chip en su lugar y comprueba los tres agujeros de la tabla '
            f'antes de presionarlo a fondo.</p><div class="chips">{"".join(cards)}</div></section>')


def seccion_piezas(fase):
    piezas = [p for p in MONTAJE.piezas if p.fase == fase]
    if not piezas:
        return ''
    filas = []
    for p in piezas:
        tag = ' <span class="tag">prueba</span>' if p.retirar is not None else ''
        filas.append(f'<tr><td><input type="checkbox" data-id="pieza-{p.ref}" aria-label="{e(p.ref)} puesta"></td>'
                     f'<td class="num">{e(p.ref)}</td><td>{e(TIPO_PIEZA[p.tipo])} · {e(p.valor)}{tag}</td>'
                     f'<td class="ag">{"<br>".join(e(a) for a in p.patas)}</td><td class="que">{e(p.nota)}</td></tr>')
    return (f'<section id="piezas"><h2><span class="n">B</span>Componentes</h2>'
            f'<p class="dek">Capacitores de desacople pegados al VCC de su chip, resistencias y LEDs. Corta las patas '
            f'a ~8 mm para que queden a ras.</p>'
            '<div class="tabla"><table><thead><tr><th></th><th>Ref.</th><th>Pieza</th><th>Agujeros</th><th>Nota</th></tr></thead><tbody>'
            + ''.join(filas) + '</tbody></table></div></section>')


def seccion_cables(fase):
    cables = [c for c in MONTAJE.cables if c.fase == fase]
    if not cables:
        return ''
    partes = [f'<section id="cables"><h2><span class="n">C</span>Cables</h2>'
              f'<p class="dek">En este orden: primero alimentación y tierras, luego las señales. El número (#) es el mismo '
              f'que aparece en el plano. Cada agujero dice debajo qué pin de qué chip hay en esa tira.</p>']
    for col, (titulo, sel) in grupos_cables(cables).items():
        partes.append(f'<h3 style="font-size:17px;margin:18px 0 4px">{swatch(col)} &nbsp;{e(titulo)} '
                      f'<span class="mono" style="font-size:13px;color:var(--ink-soft)">· {len(sel)}</span></h3>')
        partes.append(tabla_cables(sel))
    partes.append('</section>')
    return ''.join(partes)


def seccion_prueba(fase, g):
    if not g['prueba']:
        return ''
    filas = []
    for i, (accion, esperado) in enumerate(g['prueba'], 1):
        filas.append(f'<tr><td><input type="checkbox" data-id="prueba-{i}" aria-label="Prueba {i} correcta"></td>'
                     f'<td class="num">{i}</td><td>{accion}</td><td>{esperado}</td>'
                     f'<td><input type="text" id="res-{i}" data-id="res-{i}" placeholder="lo que viste / mediste"></td></tr>')
    nota = f'<div class="callout note"><span class="m">i</span><div>{g["nota_prueba"]}</div></div>' if g.get('nota_prueba') else ''
    return (f'<section id="prueba"><h2><span class="n">D</span>Prueba de la fase</h2>'
            f'<p class="dek">No pases a la siguiente fase hasta que todas estén marcadas. Escribe lo que viste en cada '
            f'una: queda guardado y lo paso a la bitácora.</p>{nota}'
            '<div class="tabla"><table><thead><tr><th>OK</th><th>#</th><th>Haz esto</th><th>Debe pasar</th><th>Resultado</th></tr></thead><tbody>'
            + ''.join(filas) + '</tbody></table></div></section>')


def seccion_fallas(g):
    if not g['fallas']:
        return ''
    filas = ''.join(f'<tr><td>{s}</td><td>{c}</td><td>{a}</td></tr>' for s, c, a in g['fallas'])
    return ('<section id="fallas"><h2><span class="n">E</span>Si algo falla</h2>'
            '<div class="tabla"><table><thead><tr><th>Síntoma</th><th>Causa probable</th><th>Qué revisar</th></tr></thead><tbody>'
            + filas + '</tbody></table></div></section>')


def seccion_cierre(fase, g):
    ret_c = [c for c in MONTAJE.cables if c.temporal and c.retirar == fase]
    ret_p = [p for p in MONTAJE.piezas if p.retirar == fase]
    items = ''.join(f'<li><input type="checkbox" data-id="cierre-{i}" aria-label="Hecho"><span>{t}</span></li>'
                    for i, t in enumerate(g['cierre'], 1))
    retiro = ''
    if ret_c or ret_p:
        cab = ', '.join(f'#{c.n}' for c in ret_c)
        pie = ', '.join(p.ref for p in ret_p)
        retiro = (f'<li><input type="checkbox" data-id="retiro" aria-label="Retirado"><span><b>Retira</b>'
                  f'{": cables " + cab if cab else ""}{"; piezas " + pie if pie else ""}.</span></li>')
    return (f'<section id="cierre"><h2><span class="n">F</span>Al cerrar la fase</h2>'
            f'<ol class="manual">{retiro}{items}</ol></section>')


def pagina_fase(fase, u):
    g = GUIAS[fase]
    svg = escena(fase)
    leyenda = ''.join(f'<span>{swatch(c)}</span>' for c in ORDEN_COLOR)
    manual = ''
    if g['manual']:
        manual = ('<section id="manual"><h2><span class="n">0</span>Preparación</h2><ol class="manual">'
                  + ''.join(f'<li><input type="checkbox" data-id="manual-{i}" aria-label="Hecho"><span>{t}</span></li>'
                            for i, t in enumerate(g['manual'], 1)) + '</ol></section>')
    return f'''<title>{TITULOS[fase]}</title>
{fuentes()}
<style>{CSS}</style>
<body data-fase="{fase}">
<div class="wrap">
<header class="top">
  <div class="eyebrow">Montaje físico · microprocesador 8 bits · fase {fase} de 6</div>
  <h1>{e(FASES[fase])}</h1>
  <p class="lede">{g['objetivo']}</p>
  {nav(fase, u)}
</header>
<div class="progreso"><span id="cuenta" class="mono">0 marcados</span><div class="barra"><i id="barra"></i></div>
  <span id="estado-db" class="estado-db">cargando…</span></div>

<section id="antes"><h2>Antes de empezar</h2>{callouts(g['antes'])}</section>

<section id="material"><h2>Material de esta fase</h2>{material(fase)}</section>

<section id="plano"><h2>Plano</h2>
  <p class="dek">Vista de arriba, fila 1 a la izquierda, letra j arriba. En color lo de esta fase; atenuado lo de fases
  anteriores; en magenta punteado los cables de prueba. Cada cable lleva su número junto a <b>los dos extremos</b>
  (el mismo de las tablas), y el punto con borde blanco marca el agujero exacto donde entra.</p>
  <div class="leyenda">{leyenda}</div>
  <div class="botones"><button type="button" data-escala="plano-general">Ver a tamaño real</button></div>
  <figure><div class="plano" id="plano-general">{svg}</div>
  <figcaption>Cada cable sale en vertical de su agujero, corre por un carril propio (nunca encima de otro paralelo) y
  rodea los chips en vez de pasarles por encima, como se tiende en físico: plano y pegado a la protoboard.</figcaption></figure>
</section>
{manual}
{seccion_chips(fase)}
{seccion_piezas(fase)}
{seccion_cables(fase)}
{seccion_prueba(fase, g)}
{seccion_fallas(g)}
{seccion_cierre(fase, g)}
<footer>Generado desde <code>montaje/netlist.py</code> (única fuente de verdad del montaje, verificada por
<code>tests/test_montaje.py</code> contra <code>pines.h</code> y los datasheets de TI). Si cambia algo del montaje se
regenera todo desde ahí.</footer>
</div>
<script>{JS}</script>
</body>'''


def pagina_indice(u):
    d = datos()
    filas = []
    for f in FASES:
        n_c = sum(1 for c in MONTAJE.cables if c.fase == f and not c.temporal)
        n_t = sum(1 for c in MONTAJE.cables if c.fase == f and c.temporal)
        chips = ', '.join(c.nombre for c in MONTAJE.chips.values() if c.fase == f) or '—'
        enlace = f'<a href="{e(u[str(f)])}">{e(FASES[f])}</a>' if u.get(str(f)) else e(FASES[f])
        filas.append(f'<tr><td class="num">{f}</td><td>{enlace}</td><td>{e(chips)}</td>'
                     f'<td class="cm">{n_c}</td><td class="cm">{n_t}</td></tr>')
    compras = ''.join(f'<tr><td>{swatch(col)}</td><td>{e(COLORES[col][1])}</td><td class="cm">{m:.1f} m</td></tr>'
                      for col, m in d['metros_por_color'].items())
    placa = ''.join(
        f'<tr><td class="num">{bb}</td><td>{e(", ".join(c.nombre for c in MONTAJE.chips.values() if c.bb == bb))}</td></tr>'
        for bb in ('BB1', 'BB2', 'BB3', 'BB4'))
    svg = escena(max(FASES))
    return f'''<title>Montaje en Protoboard</title>
{fuentes()}
<style>{CSS}</style>
<body data-fase="indice">
<div class="wrap">
<header class="top">
  <div class="eyebrow">Montaje físico · microprocesador 8 bits</div>
  <h1>Montaje en 4 protoboards</h1>
  <p class="lede">Guía del montaje final: 10 integrados TTL en 4 protoboards de 830 puntos y el Arduino Mega, sobre una
  base rígida, con cable sólido 22 AWG en 10 colores, uno por función. Se arma en 7 fases y cada una termina con una
  prueba: no se pasa a la siguiente sin aprobarla.</p>
  {nav(-1, u)}
</header>
<div class="progreso" hidden><span id="cuenta"></span><div class="barra"><i id="barra"></i></div><span id="estado-db"></span></div>

<section><h2>Así queda</h2>
  <div class="botones"><button type="button" data-escala="plano-final">Ver a tamaño real</button></div>
  <figure><div class="plano" id="plano-final">{svg}</div>
  <figcaption>Montaje terminado (fase 6): {d["totales"]["cables_definitivos"]} cables definitivos.</figcaption></figure>
</section>

<section><h2>Fases</h2>
  <div class="tabla"><table><thead><tr><th>#</th><th>Fase</th><th>Integrados</th><th>Cables</th><th>Prueba</th></tr></thead>
  <tbody>{"".join(filas)}</tbody></table></div>
  <div class="callout note"><span class="m">i</span><div><b>Por qué la salida va antes que la ALU:</b> sus 8 LEDs, con el
  74LS240 detrás, son la pantalla con la que se prueban la ALU, los registros y el mux sin el Arduino. Así cada chip se
  verifica en cuanto se pone, y un error se encuentra en la fase en que se cometió.</div></div>
</section>

<section><h2>Qué va en cada protoboard</h2>
  <div class="tabla"><table><thead><tr><th>Protoboard</th><th>Integrados</th></tr></thead><tbody>{placa}
  <tr><td class="num">Mega</td><td>A la izquierda de BB2/BB3, USB hacia afuera, cabecera 22–53 hacia las protoboards; A8–A15 (abajo) leen el PC</td></tr>
  </tbody></table></div>
</section>

<section><h2>Código de colores</h2>
  <p class="dek">Un color por función, sin excepciones: así un cable mal puesto se ve a simple vista. Los cables de prueba
  son dupont (magenta en los planos) para que nunca se confundan con el cableado final.</p>
  <div class="tabla"><table><thead><tr><th>Color</th><th>Función</th><th>Comprar</th></tr></thead><tbody>{compras}</tbody></table></div>
  <p class="dek">Metros de cable sólido 22 AWG: suma de los largos de la guía más 30 % de margen para errores de corte.</p>
</section>

<section><h2>Herramientas y material que no es de una sola fase</h2>
  <div class="tabla"><table><tbody>
  <tr><td>Multímetro con continuidad (pitido)</td><td>Se usa en todas las fases</td></tr>
  <tr><td>Pelacables para 22 AWG y pinzas de corte</td><td>Pelado de 8 mm en cada punta</td></tr>
  <tr><td>Pinzas de punta fina</td><td>Para doblar y colocar cables cortos</td></tr>
  <tr><td>Fuente 5 V ≥1 A + adaptador jack hembra a bornera</td><td>Alimenta las protoboards; el Mega va por USB. <b>5 V regulada</b>: 6 V directo no (ver fase 0)</td></tr>
  <tr><td>Base de MDF o acrílico ~35 × 25 cm, 4 separadores M3 de 10 mm con tornillos</td><td>Fija las protoboards y el Mega</td></tr>
  <tr><td>Kit dupont macho-macho (cualquier color)</td><td>Solo para las pruebas; se retiran</td></tr>
  <tr><td>Dip switch de 8, pulsador de 4 patas, 9 resistencias de 1 kΩ</td><td>Banco de pruebas de las fases 1–4; <b>se retiran</b> al cerrar la fase 4</td></tr>
  <tr><td>15 resistencias más: 8 de 330 Ω y 7 de 1 kΩ</td><td>Protecciones de la fase 5, <b>permanentes</b>: son aparte de las 9 del banco de pruebas</td></tr>
  <tr><td>Cinta de enmascarar y marcador</td><td>Rótulos de protoboards y chips</td></tr>
  </tbody></table></div>
</section>

<footer>Todo se genera desde <code>montaje/netlist.py</code> y se verifica con <code>tests/test_montaje.py</code>.
Bitácora del montaje: <code>montaje/bitacora_montaje.md</code>.</footer>
</div>
<script>
document.querySelectorAll('[data-escala]').forEach(b => b.addEventListener('click', () => {{
  const p = document.getElementById(b.dataset.escala); p.classList.toggle('real');
  b.textContent = p.classList.contains('real') ? 'Ajustar al ancho' : 'Ver a tamaño real';
}}));
</script>
</body>'''


def main():
    os.makedirs(SALIDA, exist_ok=True)
    u = urls()
    for f in FASES:
        with open(os.path.join(SALIDA, f'pagina_fase{f}.html'), 'w', encoding='utf-8') as fh:
            fh.write(pagina_fase(f, u))
    with open(os.path.join(SALIDA, 'pagina_indice.html'), 'w', encoding='utf-8') as fh:
        fh.write(pagina_indice(u))
    print('páginas en', SALIDA)


if __name__ == '__main__':
    main()
