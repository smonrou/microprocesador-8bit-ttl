
#ifndef CONSOLA_H
#define CONSOLA_H

#ifdef ARDUINO

#include "nucleo.h"

namespace consola {

void iniciar(Nucleo* nucleo);

// Lee lo que haya llegado por serial y ejecuta los comandos completos.
void atender();

}

#endif
#endif 
