"""Texto de las guías por fase: objetivo, avisos, pruebas y fallas.

Los agujeros, cables y piezas NO se escriben aquí: salen de netlist.py.
Aquí solo va lo que un humano tiene que hacer o comprobar.

Convención del dip switch de pruebas (ver netlist.py): cada interruptor tiene
pull-up de 1 kΩ, así que OFF = 1 y ON = 0. Interruptor 1 = bit 0.
"""

DIP = ('Recuerda: en el dip switch <b>OFF = 1</b> y <b>ON = 0</b> (cada interruptor '
       'tiene pull-up). El interruptor 1 es el bit 0.')

GUIAS = {
    0: {
        'objetivo': 'Dejar la base armada: las 4 protoboards pegadas en orden, el Mega '
                    'atornillado y los 16 rieles unidos en una sola red de +5 V y otra de GND, '
                    'con la fuente y el electrolítico de entrada. Al terminar, cada riel mide 5 V.',
        'antes': [
            ('warn', '<b>Orientación.</b> Todos los planos se dibujan con la <b>fila 1 a la izquierda</b> y '
                     'la <b>letra j arriba</b>. Pon una protoboard así y fíjate qué letra queda arriba. Si '
                     'queda la <b>a</b>, tu protoboard viene impresa al revés: <b>avísame antes de pegar nada</b> '
                     'y regenero todos los planos en espejo.'),
            ('warn', '<b>Rieles partidos.</b> Muchas protoboards de 830 tienen cada riel cortado a la mitad '
                     '(se nota un hueco más grande o la raya interrumpida cerca de la fila 32). Compruébalo con '
                     'el multímetro en continuidad entre el primer y el último agujero de cada riel. Si no pita, '
                     'pon un puente corto del mismo color (rojo en +, negro en −) cruzando el corte.'),
            ('note', '<b>La raya manda, no la posición.</b> En el plano el riel <b>+</b> (raya roja) es el '
                     'exterior y el <b>−</b> (raya azul) el interior. Si en tu protoboard la roja está adentro, '
                     'cablea siguiendo la raya de color, nunca la posición.'),
            ('warn', '<b>Solo 5 V regulados.</b> Los 74LS piden 4.75–5.25 V (máximo absoluto 7 V) y el pull-up '
                     'de CLEAR lleva el riel + a un pin del Mega, que no admite más de 5.5 V. Una fuente de '
                     '<b>6 V no va directa</b>: pásala por un regulador LM2940-5 (un 7805 no sirve, pide ≥7 V) '
                     'o, si es regulada, por un diodo 1N4001 en serie (ánodo a la fuente) y mide con carga. '
                     'Un adaptador de "6 V" no regulado da 7–9 V en vacío: no lo uses.'),
            ('note', '<b>Cómo se corta y pela cada cable.</b> El largo de cada tabla ya incluye las dos puntas: '
                     'corta a ese largo, pela <b>8 mm</b> en cada extremo, dobla las puntas a 90° y deja el cable '
                     '<b>plano, pegado a la protoboard</b>. Si en el dibujo un cable cruza sobre un chip, en '
                     'físico lo rodeas por el extremo más cercano del chip, nunca por encima.'),
        ],
        'manual': [
            'Inventario: revisa contra la lista de compras que tengas todo (sección Material del índice).',
            'Orientación: confirma que la fila 1 queda a la izquierda y la j arriba (ver aviso).',
            'Rieles partidos: prueba continuidad de los 16 rieles; puentea los que estén cortados.',
            'Base: une las 4 protoboards por sus encastres laterales en orden BB1 (arriba) → BB4 (abajo), '
            'todas con la fila 1 del mismo lado. Solo cuando estén alineadas, retira el adhesivo y pégalas.',
            'Mega: a la izquierda de BB2/BB3, con el USB hacia afuera (izquierda) y la cabecera doble '
            '22–53 mirando a las protoboards. Atorníllalo con separadores de 10 mm; deja ~2 cm de aire '
            'entre la cabecera y el borde de las protoboards.',
            'Rotula con cinta de enmascarar: BB1, BB2, BB3, BB4 en el borde izquierdo de cada protoboard.',
        ],
        'prueba': [
            ('Sin fuente, continuidad entre el + de BB1 (arriba) y el + de BB4 (abajo)', 'Pita'),
            ('Sin fuente, continuidad entre el − de BB1 y el − de BB4', 'Pita'),
            ('Sin fuente, continuidad entre + y − (cualquier protoboard)', '<b>NO pita.</b> Si pita, hay un corto: no conectes la fuente'),
            ('Conecta la fuente. Voltaje + a − en BB1, riel superior, fila 3 y fila 61', '4.75 – 5.25 V'),
            ('Igual en BB1 riel inferior', '4.75 – 5.25 V'),
            ('Igual en BB2 (superior e inferior)', '4.75 – 5.25 V'),
            ('Igual en BB3 (superior e inferior)', '4.75 – 5.25 V'),
            ('Igual en BB4 (superior e inferior)', '4.75 – 5.25 V'),
        ],
        'fallas': [
            ('0 V en medio riel', 'Riel partido sin puente', 'Puente del mismo color cruzando el corte'),
            ('Menos de 4.75 V', 'Fuente débil o conexión floja en la bornera', 'Aprieta la bornera; prueba otra fuente de ≥1 A'),
            ('Más de 5.25 V', 'Fuente de 6 V o no regulada', 'Desconecta ya; regulador LM2940-5 o diodo 1N4001 en serie (ver aviso)'),
            ('+ y − pitan entre sí', 'Un cable rojo en riel − o al revés', 'Revisa los puentes uno por uno con la tabla'),
        ],
        'cierre': ['Desconecta la fuente antes de pasar a la fase 1.',
                   'Anota en la bitácora las 8 mediciones y qué rieles tuviste que puentear.'],
    },
    1: {
        'objetivo': 'Montar el registro de salida, el 74LS240 y los 8 LEDs. Con el dip switch y el '
                    'pulsador (temporales, en BB2) se comprueba que un byte se engancha y se queda fijo. '
                    'Esta etapa se hace primero porque sus LEDs son la "pantalla" con la que se prueban '
                    'la ALU, los registros y el mux en las fases siguientes.',
        'antes': [
            ('warn', '<b>Siempre sin fuente</b> al insertar o quitar chips y cables. Descárgate tocando algo '
                     'metálico aterrizado antes de tomar un chip; tómalo por el cuerpo, no por las patas.'),
            ('note', '<b>Cómo se inserta un chip.</b> Endereza las patas apoyándolas de lado contra la mesa '
                     'hasta que queden a 90°. La <b>muesca apunta hacia la fila 1</b> y el <b>pin 1</b> (el del '
                     'punto) cae en el agujero que indica la tabla. Presiona parejo con el pulgar hasta que el '
                     'cuerpo quede a ras. Comprueba que el último pin cae donde dice la tabla.'),
            ('note', '<b>El 74LS240 invierte.</b> Con bit = 1 su salida baja a ~0.3 V y <b>hunde</b> la '
                     'corriente del LED, que se alimenta desde +5 V: +5 V → LED → 330 Ω → salida del 240. Así el LED '
                     'enciende con bit = 1. Por eso aquí los LEDs van al revés que en un diseño con 74LS244: '
                     'el <b>ánodo</b> (pata larga) va a la fila del <b>puente rojo a +5 V</b> y el <b>cátodo</b> '
                     '(pata corta, lado plano) a la fila de la resistencia. Sirve cualquier color.'),
            ('note', DIP),
        ],
        'manual': [],
        'prueba': [
            ('Conecta la fuente. Toca los chips con el dedo', 'Tibios como mucho. Si uno quema: desconecta y revisa su VCC/GND'),
            ('Los 8 interruptores en OFF → presiona y suelta el pulsador', 'Los 8 LEDs encendidos (11111111)'),
            ('Los 8 en ON → pulsa', 'Los 8 apagados (00000000)'),
            ('Solo el interruptor 1 en OFF → pulsa', 'Solo el LED de la <b>derecha</b> (bit 0)'),
            ('Solo el interruptor 8 en OFF → pulsa', 'Solo el LED de la <b>izquierda</b> (bit 7)'),
            ('Recorre los interruptores 2 a 7 uno por uno, pulsando cada vez', 'Se enciende un solo LED que avanza de derecha a izquierda'),
            ('Cambia interruptores <b>sin</b> pulsar', 'Los LEDs <b>no cambian</b>: el registro retiene'),
            ('Multímetro en la salida del 240 (pata Y) de un LED encendido, y luego de uno apagado',
             'Encendido ≈ 0.2 – 0.5 V (la salida hunde la corriente); apagado ≈ 3 V o más'),
        ],
        'fallas': [
            ('Ningún LED enciende', '1G̅/2G̅ del 240 sin GND, 240 sin VCC, o ánodos sin su puente a +5 V', 'Cables de habilitación y los 8 puentes rojos de los ánodos'),
            ('Los LEDs muestran el byte al revés (encienden los bits en 0)', 'LEDs cableados como para un 74LS244: ánodo a la salida y cátodo a GND', 'Con el 240 el ánodo va a +5 V (puente rojo) y el cátodo a la resistencia'),
            ('Solo encienden los bits 0-3 (o solo 4-7)', 'Una de las dos habilitaciones (pin 1 o pin 19) suelta', 'Pin 1 = bits 0-3, pin 19 = bits 4-7'),
            ('Un LED nunca enciende', 'LED al revés o LED dañado', 'Gíralo; si sigue igual, cámbialo'),
            ('Los LEDs siguen al dip sin pulsar', 'Un cable gris sale de una D en lugar de una Q del 273', 'Revisa los grises contra la tabla: las Q son los pines 2,5,6,9,12,15,16,19'),
            ('Pulsar no hace nada', 'CLEAR del 273 en bajo, o el pulsador mal orientado', 'CLEAR (pin 1) debe ir a +. Con el multímetro, el pulsador debe unir e↔f solo al presionar'),
            ('LEDs en orden cruzado', 'Cables grises cruzados', 'Recorre bit por bit con la tabla'),
        ],
        'cierre': ['Retira los cables de prueba marcados abajo. El dip switch, el pulsador y sus resistencias se quedan hasta la fase 4.',
                   'Anota en la bitácora el resultado de cada prueba.'],
    },
    2: {
        'objetivo': 'Montar las dos 74LS181 con su control en paralelo, la cadena de acarreo y el bus F '
                    '(azul, definitivo) hacia el registro de salida. Luego se caracteriza la ALU: A sale del '
                    'dip switch, B y el control de puentes temporales a los rieles, y el resultado se ve en '
                    'los LEDs pulsando el reloj de salida. <b>Esta fase resuelve el pendiente C.5</b> (acarreo en SUB).',
        'antes': [
            ('warn', '<b>Las 74LS181 son anchas (600 mil).</b> Sus patas van en las columnas <b>d</b> y <b>h</b>, '
                     'no en e/f: quedan 3 agujeros entre las filas de patas además del canal. En cada pata '
                     'quedan libres a, b, c (abajo) e i, j (arriba).'),
            ('warn', '<b>Pines 22 y 23.</b> El pin 23 es <b>A1</b> y el 22 es <b>B1</b> (datasheet de TI). Una '
                     'tabla antigua del registro de diseño los tenía cruzados; ya está corregida. Cablea con '
                     'esta guía.'),
            ('note', DIP + ' Los puentes temporales de <b>B</b> y del <b>control</b>: en el riel <b>+</b> valen 1, '
                     'en el riel <b>−</b> valen 0. Cambia cada uno de riel según el caso de prueba.'),
            ('note', 'Para ver el resultado: prepara el caso, presiona y suelta el pulsador (reloj del registro '
                     'de salida) y lee los LEDs. <b>C̄n+4</b> de la ALU ALTA (pin 16) se mide con el multímetro: '
                     'por debajo de 0.8 V = bajo, por encima de 2.4 V = alto.'),
        ],
        'manual': [],
        'prueba': [
            ('ADD 3+2 · A=00000011, B=00000010 · M=0 S3-S0=1001 C̄n=1', 'LEDs 00000101'),
            ('ADD 15+1 · A=00001111, B=00000001 · igual control', 'LEDs 00010000 (el acarreo cruzó de ALU BAJA a ALTA)'),
            ('ADD 255+1 · A=11111111, B=00000001', 'LEDs 00000000 · C̄n+4 ALTA en <b>bajo</b> (hubo acarreo)'),
            ('SUB 5−3 · A=00000101, B=00000011 · M=0 S=0110 C̄n=0', 'LEDs 00000010 · anota C̄n+4 ALTA (alto/bajo)'),
            ('SUB 3−5 · A=00000011, B=00000101', 'LEDs 11111110 · anota C̄n+4 ALTA'),
            ('SUB 5−5 · A=00000101, B=00000101', 'LEDs 00000000 · anota C̄n+4 ALTA'),
            ('AND · A=11001100, B=10101010 · M=1 S=1011', 'LEDs 10001000'),
            ('OR · mismas A y B · M=1 S=1110', 'LEDs 11101110'),
            ('XOR · mismas A y B · M=1 S=0110', 'LEDs 01100110'),
            ('Pasar A · M=1 S=1111', 'LEDs = A'),
            ('Pasar B · M=1 S=1010', 'LEDs = B'),
        ],
        'nota_prueba': '<b>C.5, acarreo en SUB:</b> el firmware supone que en 5−3 y en 5−5 (A ≥ B) C̄n+4 queda '
                       '<b>bajo</b> y en 3−5 queda <b>alto</b>. Si mides justo lo contrario en los tres casos, hay '
                       'que poner <code>#define CARRY_SUB_INVERTIDO 1</code> en <code>isa.h</code> antes de la fase 5. '
                       'Anota los tres niveles en la bitácora y avísame.',
        'fallas': [
            ('Todos los LEDs en 1 pase lo que pase', 'Control flotante o ALU sin VCC', 'Todos los puentes de control deben estar en un riel; revisa VCC (pin 24) y GND (pin 12)'),
            ('Nibble bajo bien, alto mal', 'Falta el acarreo C̄n+4 BAJA → C̄n ALTA, o el control no llega a la ALTA', 'Es el bug que ya pasó en Proteus: revisa el cable morado del pin 16 BAJA al pin 7 ALTA y los 5 de control'),
            ('SUB da el resultado de XOR', 'M no llega o está en 1', 'Cable de M (pin 8) y su puente temporal'),
            ('Bits 1 o 5 cruzados entre A y B', 'Pines 22/23 intercambiados', 'Pin 23 = A1, pin 22 = B1'),
            ('LEDs no cambian al pulsar', 'Algún cable azul F → D mal, o el pulsador ya no llega al reloj', 'Revisa la fase 1: pulsa con Pasar A'),
            ('Un chip quema', 'Chip al revés o VCC/GND cruzados', 'Desconecta ya. Muesca hacia la fila 1'),
        ],
        'cierre': ['Retira los cables de prueba del dip switch a A y los 8 de B. Los de control (S0-S3, M, C̄n) se quedan hasta la fase 4.',
                   'Anota la tabla completa y los tres niveles de C̄n+4 en SUB (C.5).'],
    },
    3: {
        'objetivo': 'Montar los registros A y B con sus salidas hacia la ALU (verde y blanco) y el CLEAR '
                    'común. Con el dip switch se cargan a mano y se leen a través de la ALU en modo "pasar".',
        'antes': [
            ('warn', '<b>Las Q del 74LS273 no son consecutivas.</b> Q0-Q7 están en los pines 2, 5, 6, 9, 12, '
                     '15, 16, 19 y las D en 3, 4, 7, 8, 13, 14, 17, 18. Es el error más fácil de cometer: '
                     'sigue la tabla, no la intuición.'),
            ('note', DIP),
            ('note', '<b>Un solo pulsador, tres relojes.</b> Hay un cable de prueba del pulsador a cada reloj '
                     '(REG A, REG B, registro de salida). Deja conectado <b>solo el del reloj que vas a pulsar</b> '
                     'y los otros dos sueltos al aire, sin tocar nada.'),
        ],
        'manual': [],
        'prueba': [
            ('Dip = 10100101 · pulsador solo en CLK A · pulsa', 'Se carga A (todavía no se ve)'),
            ('Control en Pasar A (M=1 S=1111) · pulsador solo en CLK de salida · pulsa', 'LEDs 10100101'),
            ('Dip = 01011010 · pulsador solo en CLK B · pulsa · luego Pasar B (S=1010) y pulsa CLK de salida', 'LEDs 01011010'),
            ('Cambia el dip sin pulsar CLK A ni CLK B · Pasar A y pulsa CLK de salida', 'LEDs siguen en 10100101: A retiene'),
            ('Carga A=00000101 y B=00000011 · ADD (M=0 S=1001 C̄n=1) · pulsa CLK de salida', 'LEDs 00001000'),
            ('Pasa un momento el puente de CLEAR del riel + al − y regrésalo · Pasar A · pulsa CLK de salida', 'LEDs 00000000 (A, B y salida en cero)'),
        ],
        'fallas': [
            ('Los LEDs muestran el dip sin haber pulsado CLK A', 'Un cable verde sale de una D en vez de una Q', 'Q = pines 2,5,6,9,12,15,16,19'),
            ('Bits desordenados', 'Q en orden equivocado', 'Recorre con el caso "un solo interruptor en OFF"'),
            ('El registro nunca carga', 'CLEAR en bajo o flotante', 'El puente temporal de CLEAR debe estar en +'),
            ('Cargan A y B a la vez', 'Los dos relojes conectados al pulsador', 'Deja solo uno'),
        ],
        'cierre': ['Retira los cables de prueba del dip switch a las D de REG A. Los de REG B se quedan para la fase 4.',
                   'Anota los resultados en la bitácora.'],
    },
    4: {
        'objetivo': 'Montar los dos 74LS157. Su salida Y alimenta las D de REG A (naranja); la entrada A viene '
                    'del bus D (amarillo, que ya llega a REG B) y la B del bus F (azul). Con esto se cierra el '
                    'lazo del acumulador: A ← A + B sin pasar por el Arduino. En la misma protoboard van los dos '
                    '<b>74LS161 del contador de programa (PC)</b>: sus entradas de carga P salen de las entradas A '
                    'del mux (bus D, amarillo), así que el dip switch también los carga durante la prueba.',
        'antes': [
            ('warn', '<b>G̅ (pin 15) a GND en los dos chips.</b> Si queda suelto, las salidas Y se quedan en 0 '
                     'sin importar nada: síntoma "REG A siempre carga cero".'),
            ('warn', '<b>Canales 3 y 4 van al revés.</b> En el 157 el canal 3 es 11 (A), 10 (B), 9 (Y) y el '
                     'canal 4 es 14 (A), 13 (B), 12 (Y): bajan en vez de subir. Sigue la tabla.'),
            ('note', DIP + ' El puente temporal de SEL: en <b>−</b> el mux deja pasar el bus D (dip switch); en '
                     '<b>+</b> deja pasar el resultado de la ALU.'),
            ('warn', '<b>El PC es físico, no una variable del Arduino.</b> Dos 74LS161 en cascada: el <b>RCO</b> '
                     '(pin 15) de PC BAJO va al <b>ENT</b> (pin 10) de PC ALTO. Si el ENT de PC ALTO va a +5 V, '
                     'el PC ALTO cuenta en cada pulso en vez de cada 16. ENP (pin 7) de los dos y ENT de PC BAJO '
                     'van a +5 V.'),
            ('note', '<b>Cómo se lee el PC en esta fase:</b> con el multímetro en voltaje, en las Q de cada 161 '
                     '(Q0 = pin 14, Q1 = 13, Q2 = 12, Q3 = 11). ~3.5 V es 1 y menos de 0.5 V es 0. En la fase 5 '
                     'lo lee el Mega por A8–A15. El puente temporal de <b>/LOAD</b>: en <b>+</b> el PC cuenta, en '
                     '<b>−</b> carga el dip switch en el siguiente pulso.'),
            ('note', '<b>El pulsador rebota.</b> Un solo toque puede contar 2 o 3 en el 161 (los 273 no lo notan '
                     'porque cargar dos veces lo mismo no cambia nada). Por eso las pruebas del PC cargan un valor '
                     'y miran si cambia de nibble, no la cuenta exacta.'),
        ],
        'manual': [],
        'prueba': [
            ('SEL en − · dip = 00000001 · pulsador solo en CLK A · pulsa', 'A = 1'),
            ('Pulsador en CLK B · pulsa', 'B = 1 (mismo dip)'),
            ('ADD (M=0 S=1001 C̄n=1) · pulsador en CLK de salida · pulsa', 'LEDs 00000010 (A+B)'),
            ('SEL en + · pulsador en CLK A · pulsa una vez', 'A = A + B = 2'),
            ('Pulsador en CLK de salida · pulsa', 'LEDs 00000011'),
            ('Repite: CLK A, luego CLK de salida, tres veces más', 'LEDs 00000100, 00000101, 00000110: el acumulador suma'),
            ('PC: pasa un momento el puente de CLEAR de REG A del riel + al − y regrésalo', 'Las 8 Q de los dos 161 en 0 V'),
            ('PC: dip = 10100101 · /LOAD en − · pulsador solo en CLK PC · pulsa · /LOAD en +', 'PC = 10100101 (carga paralela)'),
            ('PC: dip = 00001111 · /LOAD en − · pulsa · /LOAD en + · pulsa otra vez', 'Q0 de PC ALTO (pin 14) en 1: pasó a 0001xxxx, la cascada funciona'),
            ('PC: dip = 11111111 · /LOAD en − · pulsa · /LOAD en + · pulsa otra vez', 'Q de PC ALTO todo en 0: 0xFF + 1 dio la vuelta a 0x00'),
        ],
        'fallas': [
            ('REG A siempre carga 0', 'G̅ (pin 15) del 157 sin GND', 'Cable negro del pin 15 al riel −'),
            ('SEL no cambia nada', 'SEL no llega a los dos chips', 'Cable café entre los pines 1 de los dos 157'),
            ('Bits 2-3 o 6-7 cruzados', 'Canales 3/4 cableados en orden ascendente', 'Canal 3 = 11/10/9, canal 4 = 14/13/12'),
            ('Con SEL en + A no suma', 'Cable azul F → B del mux mal', 'Revisa los 8 azules nuevos de esta fase'),
            ('El PC no carga el dip', '/LOAD no llega a los dos 161, o las P no salen del bus D',
             'Cable café entre los pines 9; amarillos de las A del mux a los pines 3-6'),
            ('PC ALTO cuenta en cada pulso', 'ENT de PC ALTO a +5 V en vez de al RCO de PC BAJO', 'Pin 15 de PC BAJO → pin 10 de PC ALTO'),
            ('PC ALTO nunca cambia', 'RCO → ENT suelto, o ENP (pin 7) de PC ALTO sin +5 V', 'Revisa el café de la cascada y el rojo del pin 7'),
            ('El PC se queda en 0', 'CLEAR en bajo', 'El CLR (pin 1) de los 161 va al CLEAR de REG A, que en esta fase está en +'),
        ],
        'cierre': ['<b>Retira todo lo temporal:</b> dip switch, pulsador, sus 9 resistencias de 1 kΩ y todos los cables magenta que queden (lista abajo).',
                   'Desconecta la fuente. Desde aquí las entradas de control quedan al aire hasta conectar el Mega: no enciendas sin él.',
                   'Anota los resultados en la bitácora.'],
    },
    5: {
        'objetivo': 'Conectar el Arduino Mega: bus D, bus F, control de la ALU, relojes, CLEAR, selección del mux, '
                    'acarreo, reloj y /LOAD del PC, lectura del PC (A8–A15) y GND común. Cargar el firmware y correr el programa de referencia: 4 × 3 = 12 '
                    'tiene que aparecer en los LEDs.',
        'antes': [
            ('warn', '<b>Primero el firmware, con el Mega desconectado de la protoboard.</b> Si en la fase 2 '
                     'C.5 salió invertido, cambia <code>CARRY_SUB_INVERTIDO</code> a 1 en <code>isa.h</code>. '
                     'Sube <code>firmware/microprocesador/microprocesador.ino</code> desde el IDE, abre el monitor '
                     'serial a <b>115200</b> y escribe <code>HELP</code>: debe responder la lista de comandos.'),
            ('warn', '<b>El pin 5V del Mega no se conecta a nada.</b> El Mega se alimenta por USB y la protoboard '
                     'por su fuente; solo se unen las tierras. Conecta el <b>GND primero</b>.'),
            ('warn', '<b>Las 15 resistencias de esta fase van antes que los cables del Mega</b>, no después. '
                     'Las 7 de <b>1 kΩ</b> fijan el nivel de reposo de CLEAR, SEL, los tres relojes, el reloj del PC '
                     'y /LOAD del PC: esos pines '
                     'del Mega quedan en alta impedancia mientras resetea y durante <b>cada carga de firmware</b>, '
                     'y una entrada TTL al aire no vale 0 ni 1: flota alto y conmuta con el ruido. Sin ellas, un '
                     'CLEAR o un reloj espurio corrompe los registros a media ejecución.'),
            ('note', '<b>Las 8 de 330 Ω del bus F van en serie</b>, cada una entre un pin D del registro de salida '
                     'y la tira de la que sale su cable azul al Mega. Saltan 4 filas: dobla las patas en L y déjala '
                     'plana. Protegen contra contención si un pin del Mega quedara como <code>OUTPUT</code> por un '
                     '<code>pinMode</code> mal puesto: limitan a ~15 mA en vez de quemar el pin del Mega o la salida '
                     'de la ALU. No estorban la lectura, la entrada del Mega es de alta impedancia.'),
            ('warn', '<b>PORTC y PORTL van al revés.</b> F0 va al pin <b>37</b> (no al 30) y S0 al pin <b>49</b>. '
                     'Si lo inviertes, los resultados salen con los bits al revés sin ningún otro síntoma.'),
            ('note', '<b>El PC va a la cabecera analógica, en orden normal:</b> Q0 de PC BAJO → <b>A8</b> … Q3 de '
                     'PC ALTO → <b>A15</b> (PORTK asciende). El Arduino es la RAM: A8–A15 son sus patas de dirección.'),
            ('note', '<b>Orden de encendido:</b> fuente de la protoboard primero, luego el USB. Para apagar, al revés.'),
        ],
        'manual': [],
        'prueba': [
            ('Monitor serial: <code>STATE</code>', 'Responde el bloque de estado (PC=0x00)'),
            ('<code>LOADB 0x00 0x30 0x55 0xB0 0xC0</code> y luego <code>RUN</code> (MOV A,0x55 · OUT · HLT)', 'LEDs 01010101'),
            ('<code>BORRAR</code>, pega las 5 líneas de <code>programas/referencia.load</code>, <code>RUN</code>', 'LEDs <b>00001100</b> · traza 34 ciclos · A=0x0C · DETENIDO'),
            ('<code>LOAD 0xCC 0x09</code> · <code>LOAD 0x05 0x07</code> · <code>RESET</code> · <code>RUN</code> (9 × 7)', 'LEDs 00111111 (63)'),
            ('<code>RESET</code> y varios <code>STEP</code>', 'Avanza un microciclo por comando, igual que el simulador'),
            ('<code>STATE</code> tras cada instrucción, y el multímetro en las Q de los 161', 'El PC= del monitor es el mismo valor que marcan los 161'),
        ],
        'fallas': [
            ('Nada responde en la protoboard', 'Falta el GND común', 'Cable negro del GND del Mega al riel −'),
            ('Resultados con bits al revés', 'Bus F cableado 30→37 en vez de 37→30', 'F0 = pin 37 … F7 = pin 30'),
            ('Operaciones equivocadas', 'Control PORTL invertido', 'S0 = 49, S1 = 48, S2 = 47, S3 = 46, M = 45, C̄n = 44'),
            ('STATE bien pero LEDs no cambian con OUT', 'Reloj de salida', 'Mega pin 7 → pin 11 del registro de salida'),
            ('Monitor serial mudo', 'Velocidad o fin de línea', '115200 baudios; cualquier fin de línea sirve'),
            ('Bucle no termina / JNZ raro', 'Acarreo o C.5', 'Mega pin 2 ← pin 16 ALU ALTA; revisa CARRY_SUB_INVERTIDO'),
            ('Los registros se borran solos, o cargan basura al subir firmware',
             'Falta el pull-up de CLEAR (R_CLEAR) o un pull-down de reloj (R_CLK_A/B/S)',
             'Sin fuente, mide de CLEAR al riel + y de cada CLK al riel −: 1 kΩ en cada uno'),
            ('El programa se repite o salta a lo loco', 'Bits del PC cruzados hacia A8–A15, o CLK PC / /LOAD sin su resistencia',
             'Q0 de PC BAJO = A8 … Q3 de PC ALTO = A15; CLK PC (pin 42) y /LOAD (pin 43) llegan a los pines 2 y 9 de PC BAJO'),
            ('Un bit del bus F se lee siempre igual', 'Su resistencia de 330 Ω está en la tira equivocada',
             'Continuidad entre el pin D del registro de salida y el pin del Mega: debe dar ~330 Ω, no 0 ni infinito'),
        ],
        'cierre': ['Guarda la traza completa del programa de referencia en la bitácora.',
                   'Toma fotos: vista general y cada protoboard.'],
    },
    6: {
        'objetivo': 'Verificar cable por cable el montaje terminado, dejarlo rotulado y documentado, y '
                    'ensayar la demostración de la defensa.',
        'antes': [
            ('note', '<b>Revisión con la fuente desconectada.</b> Para cada cable, continuidad entre sus dos '
                     'puntas medida <b>en las patas de los chips</b>, no en el cable: así también se prueba el '
                     'contacto de la protoboard. Márcalo en la lista.'),
        ],
        'manual': [
            'Tirón suave a cada cable: ninguno debe salir.',
            'Resistencias, con la fuente desconectada y el multímetro en ohmios: las 8 del bus F miden ~330 Ω '
            'entre el pin D del registro de salida y su pin del Mega; CLEAR y /LOAD del PC miden 1 kΩ contra el '
            'riel +; SEL, los tres relojes y el reloj del PC miden 1 kΩ contra el riel −. Un 0 Ω significa que '
            'la resistencia está puenteada.',
            'Rotula cada chip con cinta de enmascarar (MUX BAJO, PC BAJO, REG A, ALU ALTA…).',
            'Revisa que no quede ningún cable de prueba (magenta) ni componente temporal.',
            'Fotos: vista general, cada protoboard de frente y un acercamiento por chip.',
        ],
        'prueba': [
            ('Programa de referencia', 'LEDs 00001100'),
            ('Demo de <code>instrucciones.md</code> con datos que elija otra persona', 'LEDs = lo que da el simulador'),
            ('<code>python -m asm programas/demo_alu.asm --run</code> y el mismo programa en la placa', 'Mismo resultado'),
        ],
        'fallas': [],
        'cierre': ['Bitácora completa, con fotos y la tabla de C.5.',
                   'Ensayo de la defensa con la secuencia de demostración.'],
    },
}
