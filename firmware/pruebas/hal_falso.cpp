// ---------------------------------------------------------------------------
// hal_falso.cpp — emulación del camino de datos (solo para pruebas nativas).
//
// Fuente: datasheet TI SDLS136, página 4, TABLE 2 (ACTIVE-HIGH DATA).
// La tabla 1 (active-low) NO aplica a este diseño.
//
// Convención de C̄n (pin 7), que está INVERTIDO en modo active-high:
//   cn = 1 (HIGH) -> columna "sin acarreo de entrada"
//   cn = 0 (LOW)  -> columna "con acarreo de entrada" (+1)
// ---------------------------------------------------------------------------

#include "hal_falso.h"

#include <cstdio>
#include <cstdlib>

#include "../microprocesador/hal.h"
#include "../microprocesador/isa.h"

namespace {

hal_falso::Estado g_estado;

// ── SN74LS181, columna lógica (M = 1) ────────────────────────────────────
// Las 16 funciones de la tabla 2. Las que usa el diseño (AND=1011, OR=1110,
// XOR=0110, F=A 1111, F=B 1010, NOT A 0000) están verificadas contra la
// bitácora; el resto se incluyen porque son triviales y así una S equivocada
// produce el valor que de verdad daría el chip, no un error inventado.
uint8_t funcionLogica(uint8_t s, uint8_t a, uint8_t b) {
  switch (s & 0x0F) {
    case 0b0000: return static_cast<uint8_t>(~a);            // F = A'
    case 0b0001: return static_cast<uint8_t>(~(a | b));      // F = (A+B)'
    case 0b0010: return static_cast<uint8_t>(~a & b);        // F = A'B
    case 0b0011: return 0x00;                                 // F = 0
    case 0b0100: return static_cast<uint8_t>(~(a & b));      // F = (AB)'
    case 0b0101: return static_cast<uint8_t>(~b);            // F = B'
    case 0b0110: return static_cast<uint8_t>(a ^ b);         // F = A XOR B
    case 0b0111: return static_cast<uint8_t>(a & ~b);        // F = AB'
    case 0b1000: return static_cast<uint8_t>(~a | b);        // F = A'+B
    case 0b1001: return static_cast<uint8_t>(~(a ^ b));      // F = (A XOR B)'
    case 0b1010: return b;                                    // F = B
    case 0b1011: return static_cast<uint8_t>(a & b);         // F = AB
    case 0b1100: return 0xFF;                                 // F = 1
    case 0b1101: return static_cast<uint8_t>(a | ~b);        // F = A+B'
    case 0b1110: return static_cast<uint8_t>(a | b);         // F = A+B
    default:     return a;                                    // 1111: F = A
  }
}

// ── SN74LS181, columna aritmética (M = 0) ────────────────────────────────
// Devuelve el resultado en 9 bits: el bit 8 es el acarreo de salida.
//
// Solo se modelan las filas que el diseño usa, más sus vecinas de error más
// probable. Cualquier otra combinación aborta con un mensaje claro: un
// emulador que inventa un valor plausible es peor que uno que se detiene,
// porque escondería justo el bug que estas pruebas existen para cazar.
uint16_t funcionAritmetica(uint8_t s, uint8_t cn, uint8_t a, uint8_t b) {
  const uint16_t masUno = (cn == 0) ? 1 : 0;   // C̄n en BAJO = acarreo forzado

  switch (s & 0x0F) {
    case 0b0000:
      // C̄n=H: F = A          C̄n=L: F = A PLUS 1
      return static_cast<uint16_t>(a) + masUno;

    case 0b0110:
      // C̄n=H: F = A MINUS B MINUS 1     C̄n=L: F = A MINUS B
      // El chip genera el complemento a 1 de B; el acarreo forzado aporta
      // el +1 que completa el complemento a 2 (datasheet pág. 2).
      return static_cast<uint16_t>(a)
           + static_cast<uint16_t>(static_cast<uint8_t>(~b))
           + masUno;

    case 0b1001:
      // C̄n=H: F = A PLUS B   C̄n=L: F = A PLUS B PLUS 1
      return static_cast<uint16_t>(a) + static_cast<uint16_t>(b) + masUno;

    case 0b1111:
      // C̄n=H: F = A MINUS 1  C̄n=L: F = A
      return static_cast<uint16_t>(a) + 0x00FF + masUno;

    default:
      std::fprintf(stderr,
                   "hal_falso: combinacion aritmetica no modelada "
                   "(M=0 S=%d%d%d%d Cn=%u). El nucleo configuro la ALU de una "
                   "forma que este emulador no reproduce.\n",
                   (s >> 3) & 1, (s >> 2) & 1, (s >> 1) & 1, s & 1,
                   static_cast<unsigned>(cn));
      std::exit(2);
  }
}

// Salida F del 181: combinacional, siempre función de las entradas actuales.
uint8_t salidaALU() {
  if (g_estado.m == ALU_LOGICO) {
    return funcionLogica(g_estado.s, g_estado.registroA, g_estado.registroB);
  }
  uint16_t bruto = funcionAritmetica(g_estado.s, g_estado.cn,
                                     g_estado.registroA, g_estado.registroB);
  return static_cast<uint8_t>(bruto & 0xFF);
}

// Lo que el 74LS157 entrega a la entrada del registro A.
uint8_t salidaMux() {
  return (g_estado.muxFuente == MUX_ALU) ? salidaALU() : g_estado.bus;
}

}  // namespace

// ── Implementación de hal.h ──────────────────────────────────────────────

namespace hal {

void iniciar() {
  hal_falso::reiniciar();
}

void ponerBus(uint8_t valor) {
  g_estado.bus = valor;
}

void seleccionarMux(uint8_t fuente) {
  g_estado.muxFuente = fuente;
}

void configurarALU(uint8_t m, uint8_t s, uint8_t cn) {
  g_estado.m = m;
  g_estado.s = static_cast<uint8_t>(s & 0x0F);
  g_estado.cn = cn;
}

void esperarPropagacion() {
  g_estado.esperas++;   // en la emulación no hay nada que esperar
}

uint8_t leerF() {
  g_estado.lecturasF++;
  return salidaALU();
}

bool huboAcarreo() {
  // En modo lógico (M=1) el chip corta la cadena de acarreo: no es
  // significativo. A.5 lo define como 0.
  if (g_estado.m == ALU_LOGICO) {
    return false;
  }
  uint16_t bruto = funcionAritmetica(g_estado.s, g_estado.cn,
                                     g_estado.registroA, g_estado.registroB);
  return (bruto & 0x0100) != 0;
}

void pulsoClockA() {
  // El 74LS273 engancha en el flanco de subida lo que haya en su entrada,
  // que es lo que el mux esté seleccionando en ese instante.
  g_estado.registroA = salidaMux();
  g_estado.pulsosA++;
}

void pulsoClockB() {
  // El registro B se carga siempre desde el bus: el mux solo alimenta a A.
  g_estado.registroB = g_estado.bus;
  g_estado.pulsosB++;
}

void limpiarRegistros() {
  g_estado.registroA = 0;
  g_estado.registroB = 0;
}

void mostrarByte(uint8_t valor) {
  g_estado.ultimoByteMostrado = valor;
  g_estado.huboSalida = true;
}

}  // namespace hal

// ── Utilidades para las pruebas ──────────────────────────────────────────

namespace hal_falso {

void reiniciar() {
  g_estado = Estado();
  g_estado.muxFuente = MUX_BUS;
  g_estado.cn = 1;
}

const Estado& estado() {
  return g_estado;
}

void forzarRegistros(uint8_t a, uint8_t b) {
  g_estado.registroA = a;
  g_estado.registroB = b;
}

}  // namespace hal_falso
