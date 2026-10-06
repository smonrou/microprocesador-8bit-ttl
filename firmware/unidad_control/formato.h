
#ifndef FORMATO_H
#define FORMATO_H

#include <stddef.h>
#include <stdint.h>

#include "nucleo.h"
#define FORMATO_BUFFER 320

namespace formato {

// Devuelve los caracteres escritos (sin contar el '\0').
size_t bloqueCiclo(const Traza& traza, char* destino, size_t tam);

// Línea `#clave=valor ...`
size_t lineaClaveValor(const Traza& traza, bool detenido,
                       char* destino, size_t tam);

// Estado actual sin traza de instrucción (para el comando STATE).
size_t lineaEstado(uint8_t pc, uint8_t ir, uint8_t a, uint8_t b,
                   uint8_t z, uint8_t c, bool detenido,
                   char* destino, size_t tam);

}

#endif
