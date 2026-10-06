#ifndef DISPLAY_H
#define DISPLAY_H

#include <stdint.h>

namespace display {

void iniciar();

// Pulsa el reloj del registro de salida, se llama desde hal::mostrarByte(), justo después de que el
// núcleo dejó la ALU en F=A para leer el registro A, así que lo que se engancha es A.
void enganchar();

}

#endif
