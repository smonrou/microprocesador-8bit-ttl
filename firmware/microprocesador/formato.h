// ---------------------------------------------------------------------------
// formato.h — volcado de estado, en dos formatos a la vez.
//
// 1. El bloque legible de A.9, idéntico byte a byte a sim/trace.py.
// 2. Una línea `clave=valor` en ASCII puro, que es lo que parseará Processing.
//
// PURO: escribe a un buffer que le pasa quien llama, no usa Serial. Así
// compila también en la PC y las pruebas pueden comparar su salida contra la
// del simulador.
// ---------------------------------------------------------------------------

#ifndef FORMATO_H
#define FORMATO_H

#include <stddef.h>
#include <stdint.h>

#include "nucleo.h"

// Tamaño recomendado para el buffer del bloque A.9.
#define FORMATO_BUFFER 320

namespace formato {

// Bloque de A.9. Devuelve los caracteres escritos (sin contar el '\0').
size_t bloqueCiclo(const Traza& traza, char* destino, size_t tam);

// Línea `#clave=valor ...` para Processing. ASCII puro, sin acentos.
size_t lineaClaveValor(const Traza& traza, bool detenido,
                       char* destino, size_t tam);

// Estado actual sin traza de instrucción (para el comando STATE).
size_t lineaEstado(uint8_t pc, uint8_t ir, uint8_t a, uint8_t b,
                   uint8_t z, uint8_t c, bool detenido,
                   char* destino, size_t tam);

}  // namespace formato

#endif  // FORMATO_H
