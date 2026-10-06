
#include <Arduino.h>

#include "consola.h"
#include "hal.h"
#include "nucleo.h"

Nucleo nucleo;

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    ;  // en placas con USB nativo, esperar a que el puerto abra
  }

  hal::iniciar();       // pines, y CLEAR a los dos 74LS273
  nucleo.borrarTodo();  // memoria a 0x00
  consola::iniciar(&nucleo);
}

void loop() {
  consola::atender();
}
