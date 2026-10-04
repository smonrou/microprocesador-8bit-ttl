// ---------------------------------------------------------------------------
// isa.h — set de instrucciones y constantes de la ALU.
//
// Espeja sim/isa.py fila por fila. tests/test_firmware_isa.py verifica que
// ambos coincidan: si alguien cambia uno sin el otro, la suite falla.
// "Parte A es inmutable" (regla D.1).
// ---------------------------------------------------------------------------

#ifndef ISA_H
#define ISA_H

#include <stdint.h>

// ── Opcodes (nibble alto del primer byte) ─────────────────────────────────
// Los nombres OP_LDA/OP_LDB/OP_LDI_A/OP_LDI_B/OP_STA son identificadores
// internos históricos; el nemónico que ve el usuario es el de TABLA_OPCODES
// (sintaxis x86 desde 2026-09-28): MOV A,[dir] / MOV B,[dir] / MOV A,inm /
// MOV B,inm / MOV [dir],A.
#define OP_NOP    0x0
#define OP_LDA    0x1
#define OP_LDB    0x2
#define OP_LDI_A  0x3
#define OP_LDI_B  0x4
#define OP_STA    0x5
#define OP_ADD    0x6
#define OP_SUB    0x7
#define OP_AND    0x8
#define OP_OR     0x9
#define OP_XOR    0xA
#define OP_OUT    0xB
#define OP_HLT    0xC
#define OP_JMP    0xD
#define OP_JZ     0xE
#define OP_JNZ    0xF

// ── Control de la ALU — SN74LS181, datasheet TI SDLS136 pág. 4, TABLE 2 ───
// (ACTIVE-HIGH DATA). La tabla 1 (active-low) NO aplica a este diseño.

// Modo (pin M)
#define ALU_ARITMETICO  0
#define ALU_LOGICO      1

// Selectores S3 S2 S1 S0
#define ALU_ADD   0b1001
#define ALU_SUB   0b0110
#define ALU_AND   0b1011
#define ALU_OR    0b1110
#define ALU_XOR   0b0110   // mismo S que SUB; los distingue M

// Funciones identidad del 181 (bitácora 6.2). Se usan para leer los
// registros físicos a través de la ALU, ya que las salidas del 74LS273 van
// al 181 y no al Arduino. A se lee en modo ARITMÉTICO: A PLUS 0 sin acarreo
// de entrada, que no genera acarreo hacia la ALU alta. B solo tiene
// identidad en modo lógico.
#define ALU_IDENTIDAD_A  0b0000   // F = A   (con M = ALU_ARITMETICO, C̄n = CN_IDENTIDAD)
#define ALU_IDENTIDAD_B  0b1010   // F = B   (con M = ALU_LOGICO)

// Carry de entrada (pin 7, INVERTIDO en modo active-high)
#define CN_ADD    1   // HIGH: sin acarreo de entrada
#define CN_SUB    0   // LOW:  acarreo forzado -> el +1 del complemento a 2
#define CN_LOGICO 1   // irrelevante en modo lógico; se fija para no dejarlo flotando
#define CN_IDENTIDAD 1   // HIGH: sin acarreo, así M=0 S=0000 da F = A y no A PLUS 1

// ---------------------------------------------------------------------------
// Parte C punto 5 — semántica del carry en SUB. RESUELTO (2026-09-29).
//
// C̄n+4 en bajo durante una resta significa que NO hubo préstamo (A >= B).
// Medido en protoboard, fase 2 del montaje (C̄n+4 de la ALU ALTA, C̄n = 0):
// 5-3 -> bajo, 3-5 -> alto, 5-5 -> bajo. Coincide con el supuesto, así que
// queda en 0. Con 1 el núcleo negaría C únicamente en las restas.
// ---------------------------------------------------------------------------
#define CARRY_SUB_INVERTIDO 0

// ── Modos de direccionamiento ─────────────────────────────────────────────
#define MODO_IMPLICITO 0
#define MODO_DIRECTO   1
#define MODO_INMEDIATO 2
#define MODO_NINGUNO   3

// ── Categorías (agrupan opcodes por forma de ejecución) ───────────────────
#define CAT_ALU                 0
#define CAT_CARGA_DIRECTA       1
#define CAT_GUARDA_DIRECTA      2
#define CAT_CARGA_INMEDIATA     3
#define CAT_SALTO_INCONDICIONAL 4
#define CAT_SALTO_CONDICIONAL   5
#define CAT_SALIDA              6
#define CAT_CONTROL             7

// ── Registro destino/origen, cuando aplica ────────────────────────────────
#define REG_NINGUNO 0
#define REG_A       1
#define REG_B       2

// ── Descriptor de instrucción ─────────────────────────────────────────────
struct Instruccion {
  uint8_t opcode;
  const char* nemonico;
  uint8_t bytes;        // 1 o 2
  uint8_t modo;
  uint8_t categoria;
  uint8_t registro;
  uint8_t microciclos;  // 5 ALU / 3 control-salida / 4 dos bytes
};

// Tabla indexada por opcode. Orden idéntico a A.5 y a sim/isa.py.
extern const Instruccion TABLA_OPCODES[16];

// Número de microciclos por forma de instrucción (decisión de B.1).
#define PASOS_ALU     5   // FETCH DECODE EXECUTE WAIT WRITE
#define PASOS_CONTROL 3   // FETCH DECODE EXECUTE
#define PASOS_2BYTES  4   // FETCH DECODE FETCH2 EXECUTE

// Etiquetas de microciclo
#define PASO_FETCH   0
#define PASO_DECODE  1
#define PASO_FETCH2  2
#define PASO_EXECUTE 3
#define PASO_WAIT    4
#define PASO_WRITE   5

const char* nombrePaso(uint8_t paso);
const char* nombreModo(uint8_t modo);

// ── Memoria ───────────────────────────────────────────────────────────────
#define MEMORIA_TAM       256
#define ZONA_PROGRAMA_FIN 0xBF
#define ZONA_DATOS_INICIO 0xC0
#define DIRECCION_INICIO  0x00

#endif  // ISA_H
