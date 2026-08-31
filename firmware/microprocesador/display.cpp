// ---------------------------------------------------------------------------
// display.cpp — multiplexado de los dos dígitos de 7 segmentos.
// ---------------------------------------------------------------------------

#ifdef ARDUINO

#include "display.h"

#include <Arduino.h>

#include "pines.h"

namespace {

// Patrones de segmentos, bit 0 = a ... bit 6 = g.
// Hexadecimal completo: las letras van en minúscula donde se distinguen
// mejor (b y d), que es la convención habitual en displays de 7 segmentos.
//
//       a
//     ─────
//   f│     │b
//    │  g  │
//     ─────
//   e│     │c
//    │  d  │
//     ─────
const uint8_t PATRONES[16] = {
  0b0111111,  // 0  a b c d e f
  0b0000110,  // 1  b c
  0b1011011,  // 2  a b d e g
  0b1001111,  // 3  a b c d g
  0b1100110,  // 4  b c f g
  0b1101101,  // 5  a c d f g
  0b1111101,  // 6  a c d e f g
  0b0000111,  // 7  a b c
  0b1111111,  // 8  todos
  0b1101111,  // 9  a b c d f g
  0b1110111,  // A  a b c e f g
  0b1111100,  // b  c d e f g
  0b0111001,  // C  a d e f
  0b1011110,  // d  b c d e g
  0b1111001,  // E  a d e f g
  0b1110001,  // F  a e f g
};

const uint8_t PINES_SEGMENTO[7] = {
  PIN_SEGMENTO_A, PIN_SEGMENTO_B, PIN_SEGMENTO_C, PIN_SEGMENTO_D,
  PIN_SEGMENTO_E, PIN_SEGMENTO_F, PIN_SEGMENTO_G,
};

uint8_t g_valor = 0;
bool g_digitoAlto = false;

// Con ánodo común el segmento se enciende poniendo su línea en BAJO, y el
// dígito se activaría poniendo su común en ALTO. Con cátodo común, al revés.
#if DISPLAY_ANODO_COMUN
  #define NIVEL_SEGMENTO_ENCENDIDO LOW
  #define NIVEL_SEGMENTO_APAGADO   HIGH
  #define DIGITO_ACTIVO_DIRECTO    HIGH
  #define DIGITO_INACTIVO_DIRECTO  LOW
#else
  #define NIVEL_SEGMENTO_ENCENDIDO HIGH
  #define NIVEL_SEGMENTO_APAGADO   LOW
  #define DIGITO_ACTIVO_DIRECTO    LOW
  #define DIGITO_INACTIVO_DIRECTO  HIGH
#endif

// El transistor que maneja el común invierte la señal (ver display.h): el
// pin del Arduino ataca la base, no el común. Sin esta inversión el display
// quedaría siempre apagado o siempre encendido.
#if DISPLAY_DIGITO_INVERTIDO
  #define NIVEL_DIGITO_ACTIVO   DIGITO_INACTIVO_DIRECTO
  #define NIVEL_DIGITO_INACTIVO DIGITO_ACTIVO_DIRECTO
#else
  #define NIVEL_DIGITO_ACTIVO   DIGITO_ACTIVO_DIRECTO
  #define NIVEL_DIGITO_INACTIVO DIGITO_INACTIVO_DIRECTO
#endif

void escribirSegmentos(uint8_t patron) {
  for (uint8_t i = 0; i < 7; i++) {
    bool encendido = (patron >> i) & 1;
    digitalWrite(PINES_SEGMENTO[i],
                 encendido ? NIVEL_SEGMENTO_ENCENDIDO : NIVEL_SEGMENTO_APAGADO);
  }
}

}  // namespace

namespace display {

void iniciar() {
  for (uint8_t i = 0; i < 7; i++) {
    pinMode(PINES_SEGMENTO[i], OUTPUT);
  }
  pinMode(PIN_DIGITO_ALTO, OUTPUT);
  pinMode(PIN_DIGITO_BAJO, OUTPUT);
  apagar();
}

void mostrar(uint8_t valor) {
  g_valor = valor;
}

void refrescar() {
  // Apagar ambos comunes antes de cambiar los segmentos evita el "fantasma":
  // si no, el dígito saliente alcanza a mostrar un instante el patrón del
  // entrante y se ve un parpadeo sucio.
  digitalWrite(PIN_DIGITO_ALTO, NIVEL_DIGITO_INACTIVO);
  digitalWrite(PIN_DIGITO_BAJO, NIVEL_DIGITO_INACTIVO);

  g_digitoAlto = !g_digitoAlto;
  uint8_t nibble = g_digitoAlto ? (g_valor >> 4) : (g_valor & 0x0F);
  escribirSegmentos(PATRONES[nibble]);

  digitalWrite(g_digitoAlto ? PIN_DIGITO_ALTO : PIN_DIGITO_BAJO,
               NIVEL_DIGITO_ACTIVO);
}

void apagar() {
  digitalWrite(PIN_DIGITO_ALTO, NIVEL_DIGITO_INACTIVO);
  digitalWrite(PIN_DIGITO_BAJO, NIVEL_DIGITO_INACTIVO);
  escribirSegmentos(0);
}

}  // namespace display

#endif  // ARDUINO
