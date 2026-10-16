
#ifdef ARDUINO

#include <Arduino.h>

#include "display.h"
#include "hal.h"
#include "isa.h"
#include "pines.h"

namespace hal {

void iniciar() {
  //1111 1111
  DDRA = 0xFF;   // Salida de bus de datos hacia los registros
  PORTA = 0x00;

  DDRC = 0x00;   // PORTC entrada de lectura del bus F de la ALU
  PORTC = 0x00;
  //0011 1111
  DDRL |= 0x3F;  // Pines ALU

  DDRK = 0x00;   // Entrada de Q0-Q7 del contador de programa
  PORTK = 0x00;

  pinMode(PIN_CLOCK_A, OUTPUT);
  pinMode(PIN_CLOCK_B, OUTPUT);
  pinMode(PIN_MUX, OUTPUT);
  pinMode(PIN_CLEAR, OUTPUT);
  pinMode(PIN_CARRY, INPUT);
  pinMode(PIN_CLOCK_PC, OUTPUT);
  pinMode(PIN_CARGA_PC, OUTPUT);

  digitalWrite(PIN_CLOCK_A, LOW);
  digitalWrite(PIN_CLOCK_B, LOW);
  digitalWrite(PIN_MUX, LOW);
  digitalWrite(PIN_CLEAR, HIGH);   // CLEAR es activo en 0: reposo en 1
  digitalWrite(PIN_CLOCK_PC, LOW);
  digitalWrite(PIN_CARGA_PC, HIGH);   // /LOAD en reposo porque el 161 cuenta

  display::iniciar();
  limpiarRegistros();
}

void ponerBus(uint8_t valor) {
  PORTA = valor;
}

void seleccionarMux(uint8_t fuente) {
  digitalWrite(PIN_MUX, (fuente == MUX_ALU) ? HIGH : LOW);
}

void configurarALU(uint8_t m, uint8_t s, uint8_t cn) {
  uint8_t control = static_cast<uint8_t>(s & 0x0F);
  if (m)  control |= (1 << BIT_M);
  if (cn) control |= (1 << BIT_CN);

  // Una sola escritura y las seis líneas cambian simultáneamente.
  PORTL = static_cast<uint8_t>((PORTL & MASCARA_NO_ALU) | control);
}

void esperarPropagacion() {
  delayMicroseconds(MICROS_PROPAGACION);
}

uint8_t leerF() {
  return PINC;
}

bool huboAcarreo() {
  // El pin Cn + 4 invertido
  return digitalRead(PIN_CARRY) == LOW;// Por eso low
}

void pulsoClockA() {
  digitalWrite(PIN_CLOCK_A, LOW);
  delayMicroseconds(MICROS_PULSO);
  digitalWrite(PIN_CLOCK_A, HIGH);
  delayMicroseconds(MICROS_PULSO);
  digitalWrite(PIN_CLOCK_A, LOW);
}

void pulsoClockB() {
  digitalWrite(PIN_CLOCK_B, LOW);
  delayMicroseconds(MICROS_PULSO);
  digitalWrite(PIN_CLOCK_B, HIGH);
  delayMicroseconds(MICROS_PULSO);
  digitalWrite(PIN_CLOCK_B, LOW);
}

void limpiarRegistros() {
  // CLEAR asíncroco con PC
  digitalWrite(PIN_CLEAR, LOW);
  delayMicroseconds(MICROS_PULSO);
  digitalWrite(PIN_CLEAR, HIGH);
}

namespace {

void pulsoClockPC() {
  // El 74LS161 cuenta o carga en 1.
  digitalWrite(PIN_CLOCK_PC, LOW);
  delayMicroseconds(MICROS_PULSO);
  digitalWrite(PIN_CLOCK_PC, HIGH);
  delayMicroseconds(MICROS_PULSO);
  digitalWrite(PIN_CLOCK_PC, LOW);
}

}

void incrementarPC() {
  digitalWrite(PIN_CARGA_PC, HIGH);
  pulsoClockPC();
}

void cargarPC(uint8_t direccion) {
  ponerBus(direccion);
  digitalWrite(PIN_CARGA_PC, LOW);
  pulsoClockPC();
  digitalWrite(PIN_CARGA_PC, HIGH);
}

uint8_t leerPC() {
  return PINK;
}

void mostrarByte(uint8_t valor) {
  // El valor para el simulador, físico no lo ocupa
  (void)valor;
  display::enganchar();
}

} 

#endif
