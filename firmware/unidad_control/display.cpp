
#ifdef ARDUINO

#include "display.h"

#include <Arduino.h>

#include "pines.h"

namespace display {

void iniciar() {
  pinMode(PIN_CLOCK_SALIDA, OUTPUT);
  digitalWrite(PIN_CLOCK_SALIDA, LOW);
  //Clock salida compartido con A y B con CLEAR para iniciar con leds apagados
}

void enganchar() {
  // captura lo que hay en A y B para mostrarlo en el 244
  digitalWrite(PIN_CLOCK_SALIDA, LOW);
  delayMicroseconds(MICROS_PULSO);
  digitalWrite(PIN_CLOCK_SALIDA, HIGH);
  delayMicroseconds(MICROS_PULSO);
  digitalWrite(PIN_CLOCK_SALIDA, LOW);
}

}

#endif
