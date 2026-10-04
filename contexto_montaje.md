# Contexto del montaje físico — para retomar la conversación

> Sesión del 2026-09-17 (histórico), con correcciones puntuales hasta 2026-10-01. Este archivo resume lo decidido y lo pendiente para seguir más adelante (con Claude o sin él) sin tener que reconstruir la conversación. **Para el estado real del montaje (qué se armó, mediciones, problemas) manda `montaje/bitacora_montaje.md`**: a 2026-10-02 las 6 fases están probadas y el procesador funciona completo. Dos cambios posteriores a esta sesión: el PC pasó a hardware (2× 74LS161, 2026-09-25) y el buffer de salida real es un **74LS240**, no el 244 (2026-09-28). La especificación congelada sigue siendo `contexto_proyecto.md`; el razonamiento de diseño, `proyecto_microprocesador_8bits.md`.

## Cómo retomar

1. Lee este archivo y `montaje/bitacora_montaje.md` (qué se armó y qué dieron las pruebas).
2. Las guías paso a paso son artifacts de claude.ai (links abajo). Las casillas y los resultados que se marcan ahí se guardan en la base de datos de cada artifact: documento `avance/fase{N}` con campos `marcas` y `resultados`. Claude los puede leer (herramienta ArtifactData, acción `get`) y pasarlos a la bitácora.
3. Si algo del montaje cambia, **se cambia en `montaje/netlist.py`** y se regenera todo:
   ```
   python -m pytest tests/test_montaje.py -v   # el montaje sigue siendo el circuito correcto
   python -m montaje.generar                   # planos SVG + datos.json
   python -m montaje.paginas                   # páginas HTML de las guías
   ```
   y se vuelven a publicar las páginas en las **mismas URLs** (`montaje/salida/urls.json`). Nunca se corrigen las guías a mano.

## Guías publicadas (artifacts)

| Guía | Link |
|---|---|
| Índice | https://claude.ai/artifact/4YDStVh8xM15Zxtyc1AgQE |
| Fase 0 · Alimentación | https://claude.ai/artifact/Lz3Gcy2F6wgJpQeLqwysSF |
| Fase 1 · Salida | https://claude.ai/artifact/MhKsW5Wu5Zy6q6dgDhpyrZ |
| Fase 2 · ALU | https://claude.ai/artifact/FjTbYyfb3M2PRDjEggrfVo |
| Fase 3 · Registros | https://claude.ai/artifact/Tg8jgcV5L1cbpsGkFw6Jd4 |
| Fase 4 · Multiplexor | https://claude.ai/artifact/9eajKKMk6WGTS7pKxnpGBx |
| Fase 5 · Arduino Mega | https://claude.ai/artifact/U2PCDCou3fc7hgg4teGUCk |
| Fase 6 · Cierre | https://claude.ai/artifact/HiRFmeVUpYudrBvFQYKwLJ |

## Qué se decidió en esta sesión (y por qué)

| Tema | Decisión | Razón |
|---|---|---|
| Entrega | **En protoboards** (C.1 resuelto) | Lo aceptó el ingeniero |
| Simulación extra (Wokwi, Fritzing) | **Descartada** | Proteus ya valida la lógica end-to-end; Wokwi no trae los 74LS y habría que emularlos otra vez |
| Salida del procesador | **8 LEDs** (opción A), bit 7 a la izquierda | Misma información que los 8 dígitos de 7 segmentos con 3 chips, 2 displays y 8 transistores menos. C.4 (ánodo/cátodo común) desapareció |
| Etapa de salida | **74LS273 (guarda) + 74LS244 (corriente)** — *en el montaje real se usó el 74LS240 (2026-09-28)* | El 273 solo entrega 0.4 mA en alto; el 244 hasta 15 mA (datasheet TI SDLS144D). 74LS534/564 harían todo en un chip pero no se consiguen en Guatemala. El 74LS240 (el que se tiene en físico) tiene el mismo pinout pero invierte: los LEDs van de +5 V a la salida (+5 V → LED → 330 Ω → Y) y encienden con bit = 1 |
| LEDs | Con el 244: **rojos, verdes o amarillos**, 220 Ω (150 Ω si tenues). Con el 240 (montaje real): cualquier color, 330 Ω | En alto el 244 da 2.4–3.4 V; azul/blanco (~3 V) no encienden. El 240 hunde la corriente desde +5 V y no tiene esa limitación |
| Protoboards | **4 de 830 puntos** sobre base rígida, Mega atornillado a la izquierda | BB1 mux y PC (2× 74LS161) · BB2 registros A/B (+ zona de pruebas) · BB3 ALU · BB4 salida y LEDs |
| Cable | **22 AWG sólido**, 10 colores, uno por función; rojo/negro solo alimentación | Código en `montaje/netlist.py` (`COLORES`). Nada de dupont en lo definitivo: dupont solo para pruebas |
| 74LS181 | **DIP-24 ancho (600 mil)**, patas en columnas **d y h** | Medido por el usuario: entre las filas de patas quedan 3 agujeros + el canal |
| Pinout del 181 | **Pin 23 = A1, pin 22 = B1** | Datasheet TI SDLS136. §6.5 del registro de diseño los tenía cruzados; corregido (también en Obsidian) |
| Orden de fases | 0 alimentación → **1 salida** → 2 ALU → 3 registros → 4 mux → 5 Mega → 6 cierre | Los LEDs de la salida son la pantalla para probar todo lo demás sin Arduino |
| Pruebas sin Arduino | Dip switch de 8 (pull-up 1 kΩ: **OFF = 1, ON = 0**) + pulsador como reloj manual, en BB2 filas 44–57 | Se retiran al cerrar la fase 4 |
| Colocación de chips | Filas elegidas por minimizar largo de cable (búsqueda por coordenadas) y relajadas a mano | 3633 → 3225 pasos de cable; al menos 4 filas entre chips y nada antes de la fila 6 |
| Imágenes | SVG generados desde los datos, no IA (Gemini descartado) | Un generador de imágenes inventa agujeros |

## Pendientes

- [ ] **Exoneración:** preguntar al ingeniero si la entrega en protoboard conserva la elegibilidad para exonerar (antes había dicho que no; ver §14 del registro de diseño). La aceptación de la protoboard (C.1, 2026-09-17) supera la duda A.1.5, pero sin confirmar por escrito.
- [ ] **Antes de la fase 0:** confirmar que las protoboards quedan con la fila 1 a la izquierda y la **j arriba**. Si queda la **a** arriba, hay que regenerar los planos en espejo (pedírselo a Claude).
- [x] **C.5 (acarreo en SUB):** resuelto el 2026-09-29, coincide con el firmware (`CARRY_SUB_INVERTIDO 0`). Se midió en la fase 2 (C̄n+4 de la ALU ALTA en 5−3, 3−5, 5−5). Si sale al revés de lo que supone el firmware: `CARRY_SUB_INVERTIDO 1` en `firmware/microprocesador/isa.h` antes de la fase 5, y actualizar `contexto_proyecto.md` Parte C.
- [ ] **Proteus:** pasar la salida a LEDs (273 → 244/240 → LEDs). Pasos en `simulacion_vs_fisico.md` §5.
- [x] **Firmware:** el manejo de los pines 3–6 (SEL0–SEL2, BLANK del diseño viejo) quedó comentado en `display.cpp` y `pines.h`; `display.h` y `firmware/diagnostico_display/` conservan la descripción del 74LS151/74LS138 como historia.

## Limitaciones conocidas de las guías

- Los cables se dibujan en recto de agujero a agujero; en físico van planos y rodean los chips. El largo de las tablas ya incluye 20 mm de puntas (y 25 mm más si llegan al Mega).
- La posición de los pines en el dibujo del Mega es esquemática: vale la serigrafía de la placa.
- La convención de rieles del plano es **+ exterior, − interior**; si la protoboard real los trae al revés, se cablea por la raya de color, no por la posición.

## Archivos de esta sesión

| Archivo | Qué es |
|---|---|
| `montaje/pinouts.py` | Pinouts de 181, 273, 157, 161 y 240 (datasheets TI) |
| `montaje/netlist.py` | **Fuente de verdad**: colocación, cada cable y pieza con agujero, color y fase |
| `montaje/generar.py` | Planos SVG y `datos.json` |
| `montaje/guias.py` | Texto de cada fase: objetivo, avisos, pruebas, fallas |
| `montaje/paginas.py` | Páginas HTML de las guías (lo que se publica como artifact) |
| `montaje/salida/` | Salida generada; `urls.json` guarda las URLs de los artifacts |
| `montaje/bitacora_montaje.md` | Bitácora del montaje (llenar mientras se arma) |
| `tests/test_montaje.py` | Verifica el montaje contra `pines.h` y una especificación lógica independiente |
| `simulacion_vs_fisico.md` | Qué simplifica Proteus y BOM físico completo |

También se actualizaron `contexto_proyecto.md` (A.2 salida en LEDs, C.1 y C.4 resueltos), `proyecto_microprocesador_8bits.md` (§13.4, §14, §15, §17, §21 nueva, §6.5 corregida), `instrucciones.md` y `progreso-simulacion.md`. La bóveda de Obsidian está en `proyecto/Microprocesador 8 Bits/` (la carpeta hermana de `Progra/`, `../Microprocesador 8 Bits/` desde aquí), fuera del repositorio, y se actualiza por separado; el repositorio (`Progra/`) es la copia canónica.
