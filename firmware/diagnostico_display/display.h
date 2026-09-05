// ---------------------------------------------------------------------------
// display.h — salida física del procesador: el byte en BINARIO, 8 dígitos.
//
// CAMBIO DE CRITERIO (ver §20 del registro de diseño): antes este módulo
// llevaba una tabla de 16 patrones y decodificaba hexadecimal EN SOFTWARE.
// El ingeniero lo rechazó: el Arduino es la unidad de control, no puede ser
// también quien convierte el dato para mostrarlo. Si se muestra hexadecimal,
// tiene que existir hardware que haga esa conversión; si se muestra binario,
// no hay nada que convertir, porque el bit ya es la magnitud.
//
// Se eligió binario. Cada uno de los 8 dígitos dibuja "0" o "1" según su bit:
//
//     "0" = segmentos a b c d e f        "1" = segmentos b c
//
// Comparando los dos patrones sale la lógica entera, sin tabla:
//     b, c        encendidos SIEMPRE            -> nivel fijo
//     a, d, e, f  encendidos si el bit es 0     -> complemento del bit
//     g           encendido si el bit es 1      -> el bit tal cual
//
// El 74LS151 (mux 8:1) ya entrega las dos señales que hacen falta: Y es el
// bit seleccionado y W su complemento. La "conversión" es literalmente un
// cable a Y y otro a W — combinacional, física, y a la vista en la placa.
//
// CAMINO DEL DATO (el Arduino no está en él):
//   bus F -> 74LS273 (registro de salida) -> 74LS151 -> buffer -> segmentos
//
// LO QUE HACE EL ARDUINO, y nada más:
//   1. enganchar()  pulsa el reloj del registro de salida al ejecutar OUT.
//                   El dato entra desde el bus F, no desde el Arduino.
//   2. refrescar()  cuenta 0..7 en las tres líneas de selección, que van a la
//                   vez al 74LS151 (elige el bit) y al 74LS138 (elige el
//                   dígito). Ambos usan el MISMO número, así que el dígito
//                   encendido y el bit mostrado no pueden desincronizarse.
//
// Los displays cuádruples comparten las 7 líneas de segmento entre sus cuatro
// dígitos, así que el multiplexado es obligatorio: no se puede mostrar un
// patrón distinto en dos dígitos a la vez sin alternarlos.
// ---------------------------------------------------------------------------

#ifndef DISPLAY_H
#define DISPLAY_H

#include <stdint.h>

// ---------------------------------------------------------------------------
// PENDIENTE Parte C punto 4 — ánodo o cátodo común. Sigue abierto porque los
// displays no se han comprado, pero YA NO ES UN PENDIENTE DE FIRMWARE: con la
// decodificación en hardware, el tipo de display solo cambia dos piezas.
//
//   Ánodo común:  segmento enciende en BAJO -> buffer INVERSOR (74LS240),
//                 común a 5V, transistor PNP (2N3906) por dígito.
//   Cátodo común: segmento enciende en ALTO -> buffer directo  (74LS244),
//                 común a GND, transistor NPN (2N2222) por dígito.
//
// En los dos casos el firmware es idéntico: cuenta 0..7 y pulsa un reloj.
// Por eso aquí ya no hay ningún #define que ajustar al comprar el display.
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Los comunes NO se conectan a pines del Arduino: los maneja el 74LS138 a
// través de un transistor por dígito (resistencia de base de 1 kΩ). El común
// conduce la corriente de hasta 6 segmentos a la vez (el patrón "0"), muy por
// encima de los 40 mA máximos de un pin, y además el Mega no tiene pines de
// sobra para ocho comunes. El 74LS138 tampoco los maneja directo: sus salidas
// atacan las bases, no los comunes.
//
// Brillo: con 8 dígitos multiplexados cada uno está encendido 1/8 del tiempo
// (antes 1/2). Si se ve apagado, bajar las resistencias de segmento a 220 Ω
// antes que acelerar el refresco.
// ---------------------------------------------------------------------------

namespace display {

void iniciar();

// Pulsa el reloj del registro de salida: engancha lo que haya EN ESE INSTANTE
// en el bus F. Se llama desde hal::mostrarByte(), justo después de que el
// núcleo dejó la ALU en F=A para leer el registro A, así que lo que se
// engancha es A. No recibe el valor a propósito: el dato no pasa por aquí.
void enganchar();

// Avanza al siguiente dígito. Hay que llamarla a menudo desde loop(): los
// cuatro dígitos de cada display comparten las líneas de segmento y es la
// persistencia de la visión lo que hace que se vean los ocho encendidos.
// Con 8 dígitos hacen falta ~480 llamadas por segundo para no ver parpadeo.
void refrescar();

// Apaga los ocho dígitos (deshabilita el 74LS138). No borra el registro de
// salida: al volver a habilitar se ve el mismo valor.
void apagar();

}  // namespace display

#endif  // DISPLAY_H
