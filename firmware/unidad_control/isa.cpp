// ---------------------------------------------------------------------------
// isa.cpp — la tabla de opcodes.
//
// Transcripción literal de A.5. Cualquier cambio aquí debe hacerse también en
// sim/isa.py, y tests/test_firmware_isa.py lo comprueba.
// ---------------------------------------------------------------------------

#include "isa.h"

const Instruccion TABLA_OPCODES[16] = {
  // opcode  nemónico       bytes  modo             categoría                registro     pasos
  { OP_NOP,   "NOP",         1,     MODO_NINGUNO,    CAT_CONTROL,             REG_NINGUNO, PASOS_CONTROL },
  { OP_LDA,   "MOV A,[dir]", 2,     MODO_DIRECTO,    CAT_CARGA_DIRECTA,       REG_A,       PASOS_2BYTES  },
  { OP_LDB,   "MOV B,[dir]", 2,     MODO_DIRECTO,    CAT_CARGA_DIRECTA,       REG_B,       PASOS_2BYTES  },
  { OP_LDI_A, "MOV A,inm",   2,     MODO_INMEDIATO,  CAT_CARGA_INMEDIATA,     REG_A,       PASOS_2BYTES  },
  { OP_LDI_B, "MOV B,inm",   2,     MODO_INMEDIATO,  CAT_CARGA_INMEDIATA,     REG_B,       PASOS_2BYTES  },
  { OP_STA,   "MOV [dir],A", 2,     MODO_DIRECTO,    CAT_GUARDA_DIRECTA,      REG_A,       PASOS_2BYTES  },
  { OP_ADD,   "ADD",         1,     MODO_IMPLICITO,  CAT_ALU,                 REG_NINGUNO, PASOS_ALU     },
  { OP_SUB,   "SUB",         1,     MODO_IMPLICITO,  CAT_ALU,                 REG_NINGUNO, PASOS_ALU     },
  { OP_AND,   "AND",         1,     MODO_IMPLICITO,  CAT_ALU,                 REG_NINGUNO, PASOS_ALU     },
  { OP_OR,    "OR",          1,     MODO_IMPLICITO,  CAT_ALU,                 REG_NINGUNO, PASOS_ALU     },
  { OP_XOR,   "XOR",         1,     MODO_IMPLICITO,  CAT_ALU,                 REG_NINGUNO, PASOS_ALU     },
  { OP_OUT,   "OUT",         1,     MODO_IMPLICITO,  CAT_SALIDA,              REG_NINGUNO, PASOS_CONTROL },
  { OP_HLT,   "HLT",         1,     MODO_NINGUNO,    CAT_CONTROL,             REG_NINGUNO, PASOS_CONTROL },
  { OP_JMP,   "JMP",         2,     MODO_DIRECTO,    CAT_SALTO_INCONDICIONAL, REG_NINGUNO, PASOS_2BYTES  },
  { OP_JZ,    "JZ",          2,     MODO_DIRECTO,    CAT_SALTO_CONDICIONAL,   REG_NINGUNO, PASOS_2BYTES  },
  { OP_JNZ,   "JNZ",         2,     MODO_DIRECTO,    CAT_SALTO_CONDICIONAL,   REG_NINGUNO, PASOS_2BYTES  },
};

const char* nombrePaso(uint8_t paso) {
  switch (paso) {
    case PASO_FETCH:   return "FETCH";
    case PASO_DECODE:  return "DECODE";
    case PASO_FETCH2:  return "FETCH2";
    case PASO_EXECUTE: return "EXECUTE";
    case PASO_WAIT:    return "WAIT";
    case PASO_WRITE:   return "WRITE";
    default:           return "?";
  }
}

// Los textos llevan tilde porque deben coincidir byte a byte con
// sim/trace.py; tests/test_firmware_formato.py compara las dos salidas.
// Son literales UTF-8, que es lo que espera el Monitor Serie del IDE.
const char* nombreModo(uint8_t modo) {
  switch (modo) {
    case MODO_IMPLICITO: return "modo implícito";
    case MODO_DIRECTO:   return "modo directo";
    case MODO_INMEDIATO: return "modo inmediato";
    case MODO_NINGUNO:   return "sin operando";
    default:             return "?";
  }
}
