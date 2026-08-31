// ---------------------------------------------------------------------------
// display.h — dos dígitos de 7 segmentos, multiplexados.
//
// Muestra un byte en HEXADECIMAL COMPLETO (00–FF). La decodificación es por
// software a propósito: el 74LS47/48 decodifica BCD y solo acierta de 0 a 9;
// con 10–15 muestra patrones sin sentido. Hacerlo aquí ahorra dos integrados
// y es coherente con que el Arduino ya lee el bus F.
// ---------------------------------------------------------------------------

#ifndef DISPLAY_H
#define DISPLAY_H

#include <stdint.h>

// ---------------------------------------------------------------------------
// PENDIENTE Parte C punto 4 — los displays aún no se han comprado, así que no
// se sabe si serán de ánodo o de cátodo común.
//
// Ánodo común: el común va a 5V y el segmento se enciende poniéndolo en BAJO.
// Cátodo común: el común va a GND y el segmento se enciende en ALTO.
//
// Cambiar este 1 por un 0 al saberlo. Es el único cambio necesario.
// ---------------------------------------------------------------------------
#define DISPLAY_ANODO_COMUN 1

// ---------------------------------------------------------------------------
// El común de cada dígito NO se conecta directo a un pin del Arduino.
//
// Al multiplexar, ese pin conduce la corriente de los 7 segmentos a la vez.
// Con resistencias de 220 Ω son unos 95 mA (con 330 Ω, unos 63 mA), y el
// máximo ABSOLUTO de un pin del Arduino son 40 mA. Conectarlo directo lo
// quema, o peor: lo degrada de forma intermitente, y el síntoma parece un
// fallo de lógica.
//
// Por eso va un transistor por dígito (2N3906 PNP para ánodo común, 2N2222
// NPN para cátodo común) con una resistencia de base de 1 kΩ. El pin del
// Arduino solo maneja la base, unos 5 mA.
//
// El transistor INVIERTE la señal de selección: para activar un dígito hay
// que poner su pin al nivel contrario del que pediría el display solo. Sin
// esto el display queda siempre apagado o siempre encendido, y es un fallo
// caro de encontrar porque el código "se ve bien".
//
// Poner a 0 solo si se conectara sin transistor (no recomendado).
// ---------------------------------------------------------------------------
#define DISPLAY_DIGITO_INVERTIDO 1

namespace display {

void iniciar();

// Guarda el byte a mostrar. No dibuja: el dibujado lo hace refrescar().
void mostrar(uint8_t valor);

// Alterna el dígito activo. Hay que llamarla a menudo desde loop(): los dos
// dígitos comparten las líneas de segmento, así que la persistencia de la
// visión es lo que hace que se vean ambos encendidos.
void refrescar();

// Apaga los dos dígitos.
void apagar();

}  // namespace display

#endif  // DISPLAY_H
