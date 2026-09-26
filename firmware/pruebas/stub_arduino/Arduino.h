// ---------------------------------------------------------------------------
// Arduino.h — stub mínimo para COMPROBAR QUE COMPILA, no para ejecutar.
//
// Los archivos hal_arduino.cpp, display.cpp y consola.cpp solo se compilan
// dentro del IDE de Arduino, así que sin esto quedarían completamente sin
// verificar hasta que llegue la placa. Con este stub se compilan en la PC y
// se cazan erratas, includes olvidados y firmas equivocadas.
//
// NO emula el comportamiento del hardware: los registros de puerto son
// variables normales y Serial no va a ninguna parte. Para verificar la
// LÓGICA está el HAL falso, que sí emula los tres integrados.
// ---------------------------------------------------------------------------

#ifndef ARDUINO_STUB_H
#define ARDUINO_STUB_H

#include <ctype.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define HIGH 1
#define LOW  0
#define INPUT  0
#define OUTPUT 1
#define INPUT_PULLUP 2

#define DEC 10
#define HEX 16
#define BIN 2

// Registros de puerto del ATmega2560. Aquí son variables sin efecto.
extern volatile uint8_t PORTA, PORTC, PORTK, PORTL;
extern volatile uint8_t DDRA, DDRC, DDRK, DDRL;
extern volatile uint8_t PINA, PINC, PINK, PINL;

void pinMode(uint8_t pin, uint8_t modo);
void digitalWrite(uint8_t pin, uint8_t valor);
int digitalRead(uint8_t pin);
void delay(unsigned long ms);
void delayMicroseconds(unsigned int us);
unsigned long millis();

// F() guarda literales en flash en el AVR real. Aquí es transparente.
#define F(cadena) (cadena)

class SerialStub {
 public:
  void begin(unsigned long baudios);
  operator bool() const;
  int available();
  int read();

  void print(const char* texto);
  void print(char caracter);
  void print(int valor);
  void print(int valor, int base);
  void print(unsigned int valor);
  void print(unsigned long valor);

  void println();
  void println(const char* texto);
  void println(char caracter);
  void println(int valor);
  void println(int valor, int base);
  void println(unsigned int valor);
  void println(unsigned long valor);
};

extern SerialStub Serial;

#endif  // ARDUINO_STUB_H
