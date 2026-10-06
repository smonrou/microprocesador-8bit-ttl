// Todo lo que el núcleo puede hacerle al circuito pasa por aquí. Hay dos
// implementaciones y solo una se enlaza en cada build:

#ifndef HAL_H
#define HAL_H

#include <stdint.h>

#define MUX_BUS 0   // bus del Arduino
#define MUX_ALU 1   // salida F de la ALU

namespace hal {

void iniciar();

// Pone un byte en el bus del Arduino y hay que pulsar el reloj del registro que corresponda.
void ponerBus(uint8_t valor);

// Elige qué ve la entrada del registro A: el bus o la salida de la ALU.
void seleccionarMux(uint8_t fuente);

// Lineas de control
void configurarALU(uint8_t m, uint8_t s, uint8_t cn);


void esperarPropagacion();

// Lee el bus F.
// Antes de pulsar el reloj del registro A.
uint8_t leerF();

bool huboAcarreo();

void pulsoClockA();
void pulsoClockB();

// CLEAR asíncrono compartido a 0x00. Por eso el programa siempre arranca en 0x00.
void limpiarRegistros();

// Un flanco con /LOAD en alto: PC <- PC + 1 y  0xFF pasa a 0x00 solo, por la cascada RCO -> ENT.
void incrementarPC();

// Carga paralela SÍNCRONA desde el bus D: pone `direccion` en el bus, baja
// /LOAD y pulsa el reloj. Deja el bus con `direccion`, que no engancha nada
// más porque ningún otro reloj se pulsa.
void cargarPC(uint8_t direccion);

// Valor actual del PC (Q0-Q7 de los 161, por PORTK). La RAM vive en el
// Arduino, así que estas son sus líneas de dirección.
uint8_t leerPC();


// El parámetro se mantiene porque el HAL falso lo registra
void mostrarByte(uint8_t valor);

}

#endif
