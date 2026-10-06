
#ifndef ISA_H
#define ISA_H

#include <stdint.h>
// Opcodes
#define OP_NOP        0x0
#define OP_MOV_A_DIR  0x1
#define OP_MOV_B_DIR  0x2
#define OP_MOV_A_INM  0x3
#define OP_MOV_B_INM  0x4
#define OP_MOV_DIR_A  0x5
#define OP_ADD        0x6
#define OP_SUB        0x7
#define OP_AND        0x8
#define OP_OR         0x9
#define OP_XOR        0xA
#define OP_OUT        0xB
#define OP_HLT        0xC
#define OP_JMP        0xD
#define OP_JZ         0xE
#define OP_JNZ        0xF

// M
#define ALU_ARITMETICO  0
#define ALU_LOGICO      1

// Selectores S3 S2 S1 S0
#define ALU_ADD   0b1001
#define ALU_SUB   0b0110
#define ALU_AND   0b1011
#define ALU_OR    0b1110
#define ALU_XOR   0b0110   // mismo S que SUB; los distingue M

//Los valores van directo al 181 y no al Arduino
#define ALU_IDENTIDAD_A  0b0000   // F = A con M = 0 Cn = 1
#define ALU_IDENTIDAD_B  0b1010   // F = B con M = 1 Cn = 1

// Carry de entrada invertido
#define CN_ADD    1   // Sin acarreo de entrada
#define CN_SUB    0   // Acarreo forzado y el +1 del complemento a 2
#define CN_LOGICO 1
#define CN_IDENTIDAD 1   //sin acarreo, así M=0 S=0000 da F = A

#define CARRY_SUB_INVERTIDO 0

#define MODO_IMPLICITO 0
#define MODO_DIRECTO   1
#define MODO_INMEDIATO 2
#define MODO_NINGUNO   3

#define CAT_ALU                 0
#define CAT_CARGA_DIRECTA       1
#define CAT_GUARDA_DIRECTA      2
#define CAT_CARGA_INMEDIATA     3
#define CAT_SALTO_INCONDICIONAL 4
#define CAT_SALTO_CONDICIONAL   5
#define CAT_SALIDA              6
#define CAT_CONTROL             7

#define REG_NINGUNO 0
#define REG_A       1
#define REG_B       2

struct Instruccion {
  uint8_t opcode;
  const char* nemonico;
  uint8_t bytes;
  uint8_t modo;
  uint8_t categoria;
  uint8_t registro;
  uint8_t microciclos;  // 5 ALU / 3 control-salida / 4 dos bytes
};

extern const Instruccion TABLA_OPCODES[16];

#define PASOS_ALU     5   // FETCH DECODE EXECUTE WAIT WRITE
#define PASOS_CONTROL 3   // FETCH DECODE EXECUTE
#define PASOS_2BYTES  4   // FETCH DECODE FETCH2 EXECUTE

#define PASO_FETCH   0
#define PASO_DECODE  1
#define PASO_FETCH2  2
#define PASO_EXECUTE 3
#define PASO_WAIT    4
#define PASO_WRITE   5

const char* nombrePaso(uint8_t paso);
const char* nombreModo(uint8_t modo);

#define MEMORIA_TAM       256
#define ZONA_PROGRAMA_FIN 0xBF
#define ZONA_DATOS_INICIO 0xC0
#define DIRECCION_INICIO  0x00

#endif
