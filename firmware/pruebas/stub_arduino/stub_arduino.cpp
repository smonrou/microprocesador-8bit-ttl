// ---------------------------------------------------------------------------
// stub_arduino.cpp — cuerpos vacíos para el stub de compilación.
//
// Existe solo para que el enlazador tenga algo. Nada de esto se ejecuta.
// ---------------------------------------------------------------------------

#include "Arduino.h"

volatile uint8_t PORTA = 0, PORTC = 0, PORTK = 0, PORTL = 0;
volatile uint8_t DDRA = 0, DDRC = 0, DDRK = 0, DDRL = 0;
volatile uint8_t PINA = 0, PINC = 0, PINK = 0, PINL = 0;

void pinMode(uint8_t, uint8_t) {}
void digitalWrite(uint8_t, uint8_t) {}
int digitalRead(uint8_t) { return LOW; }
void delay(unsigned long) {}
void delayMicroseconds(unsigned int) {}
unsigned long millis() { return 0; }

void SerialStub::begin(unsigned long) {}
SerialStub::operator bool() const { return true; }
int SerialStub::available() { return 0; }
int SerialStub::read() { return -1; }

void SerialStub::print(const char*) {}
void SerialStub::print(char) {}
void SerialStub::print(int) {}
void SerialStub::print(int, int) {}
void SerialStub::print(unsigned int) {}
void SerialStub::print(unsigned long) {}

void SerialStub::println() {}
void SerialStub::println(const char*) {}
void SerialStub::println(char) {}
void SerialStub::println(int) {}
void SerialStub::println(int, int) {}
void SerialStub::println(unsigned int) {}
void SerialStub::println(unsigned long) {}

SerialStub Serial;
