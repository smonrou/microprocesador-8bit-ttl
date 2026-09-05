// ---------------------------------------------------------------------------
// display.cpp — multiplexado de los 8 dígitos binarios.
//
// Aquí no hay ninguna tabla de segmentos, y es a propósito: la decodificación
// vive en el 74LS151 (ver display.h). Este archivo solo cuenta 0..7 y pulsa
// un reloj.
// ---------------------------------------------------------------------------

#ifdef ARDUINO

#include "display.h"

#include <Arduino.h>

#include "pines.h"

namespace {

uint8_t g_digito = 0;

// Pone el número de dígito en las tres líneas de selección. Van a la vez al
// 74LS151 (qué bit) y al 74LS138 (qué dígito): un solo número, imposible que
// se desincronicen.
void seleccionarDigito(uint8_t digito) {
  digitalWrite(PIN_SEL_0, (digito & 0x01) ? HIGH : LOW);
  digitalWrite(PIN_SEL_1, (digito & 0x02) ? HIGH : LOW);
  digitalWrite(PIN_SEL_2, (digito & 0x04) ? HIGH : LOW);
}

}  // namespace

namespace display {

void iniciar() {
  pinMode(PIN_SEL_0, OUTPUT);
  pinMode(PIN_SEL_1, OUTPUT);
  pinMode(PIN_SEL_2, OUTPUT);
  pinMode(PIN_HABILITA_DISPLAY, OUTPUT);
  pinMode(PIN_CLOCK_SALIDA, OUTPUT);

  digitalWrite(PIN_CLOCK_SALIDA, LOW);
  apagar();
  seleccionarDigito(0);
  g_digito = 0;

  // El registro de salida comparte la línea CLEAR con los registros A y B, y
  // hal::iniciar() la pulsa justo después de llamar aquí: los ocho dígitos
  // arrancan en "00000000".
  digitalWrite(PIN_HABILITA_DISPLAY, HIGH);
}

void enganchar() {
  // El 74LS273 engancha en el flanco de SUBIDA, igual que los registros A y B.
  digitalWrite(PIN_CLOCK_SALIDA, LOW);
  delayMicroseconds(MICROS_PULSO);
  digitalWrite(PIN_CLOCK_SALIDA, HIGH);
  delayMicroseconds(MICROS_PULSO);
  digitalWrite(PIN_CLOCK_SALIDA, LOW);
}

void refrescar() {
  // Apagar antes de cambiar la selección evita el "fantasma": si no, el
  // dígito saliente alcanza a mostrar un instante el bit del entrante,
  // porque el 74LS138 conmuta antes de que el 74LS151 se estabilice.
  digitalWrite(PIN_HABILITA_DISPLAY, LOW);

  g_digito = static_cast<uint8_t>((g_digito + 1) % DIGITOS_SALIDA);
  seleccionarDigito(g_digito);

  digitalWrite(PIN_HABILITA_DISPLAY, HIGH);
}

void apagar() {
  digitalWrite(PIN_HABILITA_DISPLAY, LOW);
}

}  // namespace display

#endif  // ARDUINO
