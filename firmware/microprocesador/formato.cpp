// ---------------------------------------------------------------------------
// formato.cpp — implementación del volcado de estado.
//
// El bloque de A.9 debe salir IDÉNTICO al de sim/trace.py: el simulador es la
// referencia con la que se depurará el hardware, y comparar dos volcados que
// difieren en el formato es perder el tiempo.
// tests/test_firmware_formato.py compara ambas salidas byte a byte.
// ---------------------------------------------------------------------------

#include "formato.h"

#include <stdarg.h>
#include <stdio.h>
#include <string.h>

namespace {

// Acumula en el buffer respetando el espacio restante.
struct Escritor {
  char* destino;
  size_t tam;
  size_t usado;

  Escritor(char* d, size_t t) : destino(d), tam(t), usado(0) {
    if (tam > 0) destino[0] = '\0';
  }

  void agregar(const char* formato, ...) __attribute__((format(printf, 2, 3)));
};

void Escritor::agregar(const char* formato, ...) {
  if (usado + 1 >= tam) return;
  va_list argumentos;
  va_start(argumentos, formato);
  int escritos = vsnprintf(destino + usado, tam - usado, formato, argumentos);
  va_end(argumentos);
  if (escritos > 0) {
    usado += static_cast<size_t>(escritos);
    if (usado >= tam) usado = tam - 1;
  }
}

const char* simboloALU(uint8_t opcode) {
  switch (opcode) {
    case OP_ADD: return "+";
    case OP_SUB: return "-";
    case OP_AND: return "&";
    case OP_OR:  return "|";
    case OP_XOR: return "^";
    default:     return "?";
  }
}

// Cuatro bits en binario, con ceros a la izquierda.
void binario4(uint8_t valor, char* destino) {
  for (int i = 0; i < 4; i++) {
    destino[i] = ((valor >> (3 - i)) & 1) ? '1' : '0';
  }
  destino[4] = '\0';
}

const char* nombreRegistro(uint8_t registro) {
  return (registro == REG_A) ? "A" : "B";
}

}  // namespace

namespace formato {

size_t bloqueCiclo(const Traza& t, char* destino, size_t tam) {
  Escritor salida(destino, tam);

  salida.agregar("─── Ciclo %u ───\n", static_cast<unsigned>(t.ciclo));
  salida.agregar("FETCH   PC=0x%02X  →  IR=0x%02X (%s)\n",
                 static_cast<unsigned>(t.pcAntes),
                 static_cast<unsigned>(t.ir), t.nemonico);

  char opcodeBin[5];
  binario4(t.opcode, opcodeBin);
  salida.agregar("DECODE  Opcode %s | %s | %s\n", opcodeBin,
                 (t.bytes == 1) ? "1 byte" : "2 bytes", nombreModo(t.modo));

  switch (t.categoria) {
    case CAT_ALU: {
      char selectorBin[5];
      binario4(t.aluS, selectorBin);
      salida.agregar("EXECUTE A=0x%02X %s B=0x%02X\n",
                     static_cast<unsigned>(t.aAntes), simboloALU(t.opcode),
                     static_cast<unsigned>(t.bAntes));
      salida.agregar("        ALU: M=%u S=%s Cn=%u\n",
                     static_cast<unsigned>(t.aluM), selectorBin,
                     static_cast<unsigned>(t.aluCn));
      salida.agregar("RESULT  A=0x%02X   Z=%u  C=%u\n",
                     static_cast<unsigned>(t.aDespues),
                     static_cast<unsigned>(t.z), static_cast<unsigned>(t.c));
      break;
    }

    case CAT_CARGA_DIRECTA: {
      uint8_t valor = (t.registro == REG_A) ? t.aDespues : t.bDespues;
      salida.agregar("EXECUTE Mem[0x%02X] → %s\n",
                     static_cast<unsigned>(t.operando),
                     nombreRegistro(t.registro));
      salida.agregar("RESULT  %s=0x%02X\n", nombreRegistro(t.registro),
                     static_cast<unsigned>(valor));
      break;
    }

    case CAT_GUARDA_DIRECTA:
      salida.agregar("EXECUTE A → Mem[0x%02X]\n",
                     static_cast<unsigned>(t.operando));
      salida.agregar("RESULT  Mem[0x%02X]=0x%02X\n",
                     static_cast<unsigned>(t.operando),
                     static_cast<unsigned>(t.aAntes));
      break;

    case CAT_CARGA_INMEDIATA: {
      uint8_t valor = (t.registro == REG_A) ? t.aDespues : t.bDespues;
      salida.agregar("EXECUTE #0x%02X → %s\n",
                     static_cast<unsigned>(t.operando),
                     nombreRegistro(t.registro));
      salida.agregar("RESULT  %s=0x%02X\n", nombreRegistro(t.registro),
                     static_cast<unsigned>(valor));
      break;
    }

    case CAT_SALTO_INCONDICIONAL:
      salida.agregar("EXECUTE PC ← 0x%02X\n",
                     static_cast<unsigned>(t.operando));
      salida.agregar("RESULT  salto incondicional\n");
      break;

    case CAT_SALTO_CONDICIONAL:
      salida.agregar("EXECUTE %s 0x%02X (Z=%u)\n", t.nemonico,
                     static_cast<unsigned>(t.operando),
                     static_cast<unsigned>(t.z));
      salida.agregar("RESULT  %s\n",
                     (t.pcDespues == t.operando) ? "salta" : "no salta");
      break;

    case CAT_SALIDA:
      salida.agregar("EXECUTE Muestra A\n");
      salida.agregar("RESULT  A=0x%02X\n", static_cast<unsigned>(t.aAntes));
      break;

    default:  // CAT_CONTROL: NOP, HLT
      salida.agregar("EXECUTE %s\n", t.nemonico);
      salida.agregar("RESULT  —\n");
      break;
  }

  salida.agregar("PC → 0x%02X", static_cast<unsigned>(t.pcDespues));
  return salida.usado;
}

size_t lineaClaveValor(const Traza& t, bool detenido, char* destino, size_t tam) {
  Escritor salida(destino, tam);
  // ASCII puro y prefijo '#': Processing filtra estas líneas sin confundirlas
  // con el texto bonito, y ningún acento puede romper el parseo.
  salida.agregar("#ciclo=%u pc=0x%02X ir=0x%02X op=%s a=0x%02X b=0x%02X "
                 "z=%u c=%u halted=%u",
                 static_cast<unsigned>(t.ciclo),
                 static_cast<unsigned>(t.pcDespues),
                 static_cast<unsigned>(t.ir), t.nemonico,
                 static_cast<unsigned>(t.aDespues),
                 static_cast<unsigned>(t.bDespues),
                 static_cast<unsigned>(t.z), static_cast<unsigned>(t.c),
                 static_cast<unsigned>(detenido ? 1 : 0));
  if (t.huboSalida) {
    salida.agregar(" salida=%u", static_cast<unsigned>(t.valorSalida));
  }
  return salida.usado;
}

size_t lineaEstado(uint8_t pc, uint8_t ir, uint8_t a, uint8_t b,
                   uint8_t z, uint8_t c, bool detenido,
                   char* destino, size_t tam) {
  Escritor salida(destino, tam);
  salida.agregar("#pc=0x%02X ir=0x%02X a=0x%02X b=0x%02X z=%u c=%u halted=%u",
                 static_cast<unsigned>(pc), static_cast<unsigned>(ir),
                 static_cast<unsigned>(a), static_cast<unsigned>(b),
                 static_cast<unsigned>(z), static_cast<unsigned>(c),
                 static_cast<unsigned>(detenido ? 1 : 0));
  return salida.usado;
}

}  // namespace formato
