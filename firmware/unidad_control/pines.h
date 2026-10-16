
#ifndef PINES_H
#define PINES_H

// Posiciones dentro de PORTL de las líneas de control de la ALU.
#define BIT_S0  0
#define BIT_S1  1
#define BIT_S2  2
#define BIT_S3  3
#define BIT_M   4
#define BIT_CN  5

// Máscara de los bits de PORTL que NO son de la ALU
#define MASCARA_NO_ALU 0xC0

// Pines sueltos
#define PIN_CLOCK_A 41
#define PIN_CLOCK_B 40
#define PIN_MUX     39
#define PIN_CLEAR   38
#define PIN_CARRY    2

// PC
#define PIN_CLOCK_PC 42
#define PIN_CARGA_PC 43   // /LOAD, activo en BAJO

// Salida física
#define PIN_CLOCK_SALIDA 7

#define MICROS_PROPAGACION 50

//25 ns;
#define MICROS_PULSO 3

#endif
