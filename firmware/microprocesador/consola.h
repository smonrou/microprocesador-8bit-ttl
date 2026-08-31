// ---------------------------------------------------------------------------
// consola.h — protocolo serial.
//
// Comandos:
//   LOAD <dir> <byte>        escribe un byte      -> OK dir=0xCC val=0x04
//   LOADB <dir> <hex...>     carga un bloque      -> OK dir=0xC0 n=16
//   RUN                      ejecuta hasta HLT
//   STEP                     avanza UN microciclo
//   RESET                    PC=0, banderas a 0, CLEAR a los registros
//   DUMP <ini> <fin>         vuelca memoria
//   STATE                    estado actual
//   VEL <ms>                 retardo entre instrucciones en RUN
//   HELP                     lista los comandos
//
// Cada LOAD confirma. El buffer de recepción del Arduino son 64 bytes y el
// archivo .load que genera el ensamblador tiene ~29 líneas: sin confirmación
// por línea, pegarlo de golpe podría perder comandos EN SILENCIO. LOADB
// existe para reducir esas 29 líneas a dos o tres.
//
// Toda salida sale por duplicado: el bloque legible de A.9 y una línea
// `#clave=valor` en ASCII puro que es la que parseará Processing.
// ---------------------------------------------------------------------------

#ifndef CONSOLA_H
#define CONSOLA_H

#ifdef ARDUINO

#include "nucleo.h"

namespace consola {

void iniciar(Nucleo* nucleo);

// Lee lo que haya llegado por serial y ejecuta los comandos completos.
void atender();

}  // namespace consola

#endif  // ARDUINO
#endif  // CONSOLA_H
