// ---------------------------------------------------------------------------
// hal_arduino.cpp — implementación real de hal.h sobre el Arduino Mega 2560.
//
// Solo se compila dentro del IDE de Arduino: el guard #ifdef ARDUINO lo deja
// fuera del build nativo de las pruebas, donde se enlaza hal_falso.cpp.
//
// Escritura y lectura del bus por puerto completo, no con digitalWrite bit a
// bit: los 8 bits cambian en una sola instrucción, así que el 74LS273 nunca
// puede enganchar un estado intermedio.
// ---------------------------------------------------------------------------

#ifdef ARDUINO

#include <Arduino.h>

#include "display.h"
#include "hal.h"
#include "isa.h"
#include "pines.h"

namespace hal {

void iniciar() {
  DDRA = 0xFF;   // PORTA salida: bus de datos hacia los registros
  PORTA = 0x00;

  DDRC = 0x00;   // PORTC entrada: lectura del bus F de la ALU
  PORTC = 0x00;  // sin pull-ups: las salidas del 181 son totem-pole

  DDRL |= 0x3F;  // PORTL bits 0-5 salida: S0-S3, M, C̄n

  DDRK = 0x00;   // PORTK entrada: Q0-Q7 del contador de programa
  PORTK = 0x00;  // sin pull-ups: las salidas del 161 son totem-pole

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
  digitalWrite(PIN_CLEAR, HIGH);   // CLEAR es activo en BAJO: reposo en alto
  digitalWrite(PIN_CLOCK_PC, LOW);
  digitalWrite(PIN_CARGA_PC, HIGH);   // /LOAD en reposo: el 161 cuenta

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

  // Una sola escritura: las seis líneas cambian simultáneamente.
  PORTL = static_cast<uint8_t>((PORTL & MASCARA_NO_ALU) | control);
}

void esperarPropagacion() {
  delayMicroseconds(MICROS_PROPAGACION);
}

uint8_t leerF() {
  return PINC;
}

bool huboAcarreo() {
  // El pin 16 (C̄n+4) está INVERTIDO: va a BAJO cuando hay acarreo. La
  // inversión vive aquí y en ningún otro sitio, así que el núcleo no tiene
  // que acordarse de ella.
  return digitalRead(PIN_CARRY) == LOW;
}

void pulsoClockA() {
  // El 74LS273 engancha en el flanco de SUBIDA.
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
  // CLEAR asíncrono, activo en BAJO. No necesita reloj. La misma línea llega
  // al /CLR de los 74LS161, así que el PC también queda en 0x00.
  digitalWrite(PIN_CLEAR, LOW);
  delayMicroseconds(MICROS_PULSO);
  digitalWrite(PIN_CLEAR, HIGH);
}

namespace {

void pulsoClockPC() {
  // El 74LS161 cuenta o carga en el flanco de SUBIDA.
  digitalWrite(PIN_CLOCK_PC, LOW);
  delayMicroseconds(MICROS_PULSO);
  digitalWrite(PIN_CLOCK_PC, HIGH);
  delayMicroseconds(MICROS_PULSO);
  digitalWrite(PIN_CLOCK_PC, LOW);
}

}  // namespace

void incrementarPC() {
  digitalWrite(PIN_CARGA_PC, HIGH);
  pulsoClockPC();
}

void cargarPC(uint8_t direccion) {
  // La carga es SÍNCRONA: bus y /LOAD tienen que estar estables antes del
  // flanco (setup ~20 ns; el pulso de 5 µs sobra).
  ponerBus(direccion);
  digitalWrite(PIN_CARGA_PC, LOW);
  pulsoClockPC();
  digitalWrite(PIN_CARGA_PC, HIGH);
}

uint8_t leerPC() {
  return PINK;
}

void mostrarByte(uint8_t valor) {
  // El valor NO se usa, y eso es el punto: en la placa real el dato viaja del
  // bus F al registro de salida por cable, sin pasar por el Arduino. Aquí
  // solo se pulsa el reloj que lo engancha. El parámetro existe porque el HAL
  // falso sí lo necesita (las pruebas verifican qué sacó OUT).
  (void)valor;
  display::enganchar();
}

}  // namespace hal

#endif  // ARDUINO
