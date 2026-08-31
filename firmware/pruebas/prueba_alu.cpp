// ---------------------------------------------------------------------------
// prueba_alu.cpp — barrido exhaustivo del 74LS181 emulado.
//
// Recorre las 5 operaciones del diseño sobre los 65536 pares (A, B) y vuelca
// el resultado. tests/test_firmware_alu.py compara cada línea contra
// sim/alu.py, así que el emulador queda anclado al simulador.
//
// Se compila solo para pruebas nativas; no forma parte del sketch.
// ---------------------------------------------------------------------------

#include <cstdio>

#include "../microprocesador/hal.h"
#include "../microprocesador/isa.h"
#include "hal_falso.h"

struct Operacion {
  const char* nombre;
  uint8_t m;
  uint8_t s;
  uint8_t cn;
};

int main() {
  const Operacion operaciones[] = {
    { "ADD", ALU_ARITMETICO, ALU_ADD, CN_ADD },
    { "SUB", ALU_ARITMETICO, ALU_SUB, CN_SUB },
    { "AND", ALU_LOGICO,     ALU_AND, CN_LOGICO },
    { "OR",  ALU_LOGICO,     ALU_OR,  CN_LOGICO },
    { "XOR", ALU_LOGICO,     ALU_XOR, CN_LOGICO },
  };

  hal::iniciar();

  for (const Operacion& op : operaciones) {
    for (int a = 0; a < 256; a++) {
      for (int b = 0; b < 256; b++) {
        hal_falso::forzarRegistros(static_cast<uint8_t>(a),
                                   static_cast<uint8_t>(b));
        hal::configurarALU(op.m, op.s, op.cn);
        hal::esperarPropagacion();

        uint8_t f = hal::leerF();
        int z = (f == 0) ? 1 : 0;
        int c = hal::huboAcarreo() ? 1 : 0;

        std::printf("%s %d %d %d %d %d\n", op.nombre, a, b,
                    static_cast<int>(f), z, c);
      }
    }
  }

  // Funciones extra del 181 que el núcleo usa para leer los registros.
  for (int a = 0; a < 256; a++) {
    hal_falso::forzarRegistros(static_cast<uint8_t>(a), 0x5A);
    hal::configurarALU(ALU_LOGICO, ALU_PASAR_A, CN_LOGICO);
    hal::esperarPropagacion();
    std::printf("PASAR_A %d %d %d 0 0\n", a, 0x5A,
                static_cast<int>(hal::leerF()));
  }
  for (int b = 0; b < 256; b++) {
    hal_falso::forzarRegistros(0xA5, static_cast<uint8_t>(b));
    hal::configurarALU(ALU_LOGICO, ALU_PASAR_B, CN_LOGICO);
    hal::esperarPropagacion();
    std::printf("PASAR_B %d %d %d 0 0\n", 0xA5, b,
                static_cast<int>(hal::leerF()));
  }

  return 0;
}
