// ---------------------------------------------------------------------------
// pines.h — asignación de pines del Arduino Mega 2560.
//
// ⚠️ AVISO DE CABLEADO CRÍTICO
//
// En el Mega, PORTA ASCIENDE con el número de pin, pero PORTC y PORTL
// DESCIENDEN. Cablear F0 al pin 30 daría el bit 7, no el bit 0, y el
// procesador entregaría resultados con los bits invertidos sin ningún
// síntoma evidente. Seguir las tablas al pie de la letra.
//
// ── PORTA — bus de datos (Arduino → registros A y B). ASCENDENTE ──────────
//   PA0 = pin 22 = D0        PA4 = pin 26 = D4
//   PA1 = pin 23 = D1        PA5 = pin 27 = D5
//   PA2 = pin 24 = D2        PA6 = pin 28 = D6
//   PA3 = pin 25 = D3        PA7 = pin 29 = D7
//
// ── PORTC — lectura de F (ALU → Arduino). DESCENDENTE ────────────────────
//   PC0 = pin 37 = F0  ← el bit 0 va al pin 37, NO al 30
//   PC1 = pin 36 = F1        PC5 = pin 32 = F5
//   PC2 = pin 35 = F2        PC6 = pin 31 = F6
//   PC3 = pin 34 = F3        PC7 = pin 30 = F7
//   PC4 = pin 33 = F4
//
// ── PORTL bits 0-5 — control de la ALU. DESCENDENTE ──────────────────────
//   PL0 = pin 49 = S0        PL4 = pin 45 = M
//   PL1 = pin 48 = S1        PL5 = pin 44 = C̄n  (pin 7 del 181 bajo)
//   PL2 = pin 47 = S2        PL6 = pin 43 = libre
//   PL3 = pin 46 = S3        PL7 = pin 42 = libre
//
// Los seis bits de control caben en un puerto, así que configurar la ALU
// entera es UNA escritura: todas las líneas cambian a la vez, sin estados
// intermedios que el 181 pudiera llegar a ver.
//
// ── Pines sueltos ────────────────────────────────────────────────────────
//   41  CLK A   reloj del 74LS273 del registro A
//   40  CLK B   reloj del 74LS273 del registro B  (línea INDEPENDIENTE)
//   39  MUX     selección del 74LS157: LOW = bus, HIGH = salida de ALU
//   38  CLEAR   clear asíncrono de ambos 74LS273 (activo en BAJO)
//    2  CARRY   C̄n+4, pin 16 del 181 alto. ENTRADA, invertida
//
// ── Display de 7 segmentos, multiplexado ─────────────────────────────────
//    3..9   segmentos a, b, c, d, e, f, g
//   10      común del dígito alto
//   11      común del dígito bajo
//
// Total: 36 pines de los 54 del Mega.
// ---------------------------------------------------------------------------

#ifndef PINES_H
#define PINES_H

// Posiciones dentro de PORTL de las líneas de control de la ALU.
#define BIT_S0  0
#define BIT_S1  1
#define BIT_S2  2
#define BIT_S3  3
#define BIT_M   4
#define BIT_CN  5

// Máscara de los bits de PORTL que NO son de la ALU (se preservan).
#define MASCARA_NO_ALU 0xC0

// Pines sueltos
#define PIN_CLOCK_A 41
#define PIN_CLOCK_B 40
#define PIN_MUX     39
#define PIN_CLEAR   38
#define PIN_CARRY    2

// Display
#define PIN_SEGMENTO_A  3
#define PIN_SEGMENTO_B  4
#define PIN_SEGMENTO_C  5
#define PIN_SEGMENTO_D  6
#define PIN_SEGMENTO_E  7
#define PIN_SEGMENTO_F  8
#define PIN_SEGMENTO_G  9
#define PIN_DIGITO_ALTO 10
#define PIN_DIGITO_BAJO 11

// Margen de propagación. El peor caso del datasheet ronda 80 ns entre los dos
// 181 en cascada; 50 µs son tres órdenes de magnitud de sobra.
#define MICROS_PROPAGACION 50

// Ancho del pulso de reloj del 74LS273.
#define MICROS_PULSO 5

#endif  // PINES_H
