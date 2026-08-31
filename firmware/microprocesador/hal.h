// ---------------------------------------------------------------------------
// hal.h — la frontera entre la lógica de control y el hardware.
//
// Todo lo que el núcleo puede hacerle al circuito pasa por aquí. Hay dos
// implementaciones y solo una se enlaza en cada build:
//
//   hal_arduino.cpp   pines reales del Mega          -> sketch
//   pruebas/hal_falso.cpp   emula 181 + 273 + 157    -> pruebas nativas
//
// Se enlazan en tiempo de compilación, sin clases virtuales: nunca hacen
// falta las dos a la vez y así no se paga una tabla de funciones en un AVR.
//
// LO QUE EL NÚCLEO NO PUEDE HACER: tocar un pin directamente, llamar a
// Serial, ni calcular una operación aritmética o lógica entre registros.
// Esa última es el requisito central del proyecto: el Arduino no calcula.
// ---------------------------------------------------------------------------

#ifndef HAL_H
#define HAL_H

#include <stdint.h>

// Fuente que el 74LS157 entrega a la entrada del registro A.
#define MUX_BUS 0   // bus del Arduino
#define MUX_ALU 1   // salida F de la ALU

namespace hal {

// Configura pines y deja el circuito en un estado conocido.
void iniciar();

// Pone un byte en el bus del Arduino (PORTA). No engancha nada por sí solo:
// hay que pulsar el reloj del registro que corresponda.
void ponerBus(uint8_t valor);

// Elige qué ve la entrada del registro A: el bus o la salida de la ALU.
void seleccionarMux(uint8_t fuente);

// Configura las seis líneas de control del 181 de una sola vez.
//   m  : ALU_ARITMETICO | ALU_LOGICO
//   s  : selectores S3..S0 (4 bits)
//   cn : C̄n del pin 7, YA en la polaridad del pin (invertida — ver A.3)
void configurarALU(uint8_t m, uint8_t s, uint8_t cn);

// Espera a que el resultado se propague por los dos 181 en cascada.
// El peor caso del datasheet ronda 80 ns; el margen es de 50 µs.
void esperarPropagacion();

// Lee el bus F (PINC). Es combinacional: siempre refleja las entradas
// actuales, así que hay que leerlo ANTES de pulsar el reloj del registro A.
uint8_t leerF();

// Acarreo de salida. El pin 16 (C̄n+4) está INVERTIDO: va a BAJO cuando hay
// acarreo. Esta función devuelve el valor ya corregido, así que la inversión
// vive en un único sitio y el núcleo no tiene que recordarla.
bool huboAcarreo();

// Pulsos de reloj. El 74LS273 engancha en CADA flanco de subida y no tiene
// habilitación, así que A y B llevan líneas independientes: se controla cuál
// se carga por cuál se pulsa. NUNCA compartirlas.
void pulsoClockA();
void pulsoClockB();

// CLEAR asíncrono de ambos 74LS273: los dos registros a 0x00.
void limpiarRegistros();

// Envía un byte al display de 7 segmentos. En el HAL falso no hace nada.
void mostrarByte(uint8_t valor);

}  // namespace hal

#endif  // HAL_H
