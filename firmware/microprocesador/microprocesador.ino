// ---------------------------------------------------------------------------
// microprocesador.ino — unidad de control del microprocesador de 8 bits.
//
// Curso: Arquitectura de Computadoras y Ensambladores 1
//
// El Arduino es UNICAMENTE unidad de control, memoria y reloj. Las
// operaciones aritmeticas y logicas ocurren en dos SN74LS181 reales; el
// resultado vuelve al registro A por un mux 74LS157 sin pasar nunca por el
// Arduino. La unica operacion en software es Z = (F == 0), que es leer el
// bus de resultado, no calcularlo.
//
// La salida fisica tampoco pasa por el Arduino: el byte va del bus F a un
// tercer 74LS273 y de ahi al 74LS151 que dibuja cada bit como "0" o "1" en
// los ocho digitos. El Arduino solo pulsa el reloj y cuenta 0..7 para
// multiplexar (ver display.h).
//
// Este sketch es deliberadamente delgado: toda la logica vive en nucleo.cpp,
// que no toca ni un pin. Asi el mismo codigo se compila en la PC contra un
// emulador del circuito y se contrasta instruccion por instruccion con el
// simulador de referencia (tests/test_firmware_nucleo.py).
//
// Cableado: ver pines.h. OJO: en el Mega, PORTC y PORTL tienen los bits en
// orden DESCENDENTE respecto al numero de pin.
//
// Uso: abrir el Monitor Serie a 115200 baudios y escribir HELP.
// ---------------------------------------------------------------------------

// El IDE inyecta este include por su cuenta en los .ino, pero ponerlo
// explicito hace el archivo honesto y permite compilarlo fuera del IDE.
#include <Arduino.h>

#include "consola.h"
#include "display.h"
#include "hal.h"
#include "nucleo.h"

Nucleo nucleo;

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    ;  // en placas con USB nativo, esperar a que el puerto abra
  }

  hal::iniciar();       // pines, y CLEAR a los dos 74LS273
  nucleo.borrarTodo();  // memoria a 0x00, que decodifica como NOP
  consola::iniciar(&nucleo);
}

void loop() {
  consola::atender();

  // Los cuatro digitos de cada display comparten las lineas de segmento: sin
  // refresco continuo solo se veria uno de los ocho. Aqui no se decodifica
  // nada, solo se avanza el selector; el patron lo dibuja el hardware.
  // display::refrescar();
}
