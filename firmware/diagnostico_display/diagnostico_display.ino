// ---------------------------------------------------------------------------
// diagnostico_display.ino — prueba aislada de la salida binaria de 8 digitos.
//
// No depende de nucleo.cpp/hal.h/consola.h: solo usa display.cpp/h y pines.h
// (copias exactas de firmware/microprocesador/, mismo esquematico de Proteus).
// Sirve para separar un problema de cableado de uno de la ruta
// nucleo -> hal -> display.
//
// IMPORTANTE: el dato ya NO lo pone el Arduino. El registro de salida
// (74LS273) toma sus 8 bits del bus F. Para probar el bloque aislado hay que
// poner el valor a mano en las entradas D del registro: en Proteus, con un
// LOGICSTATE por bit o un DIPSWITCH; en protoboard, con ocho cables a 5V/GND.
//
// Que hace este sketch:
//   - Pulsa el reloj del registro de salida cada 2 s: engancha lo que haya en
//     ese momento en las entradas D. Cambiar los interruptores y esperar al
//     siguiente pulso debe cambiar lo que se ve.
//   - Recorre los digitos DESPACIO (uno cada 300 ms) en vez de multiplexar a
//     velocidad normal, para poder ver cual se enciende y en que orden.
//
// Que mirar:
//   - Si un digito nunca enciende: su transistor, su resistencia de base o su
//     salida del 74LS138.
//   - Si todos encienden pero muestran el mismo simbolo: el 74LS151 no esta
//     conmutando, revisar que A,B,C esten en los pines 3,4,5 y compartidos
//     con el 74LS138.
//   - Si el simbolo esta invertido ("1" donde deberia haber "0"): estan
//     cambiadas las lineas Y y W del 74LS151.
//   - Si a los digitos les falta un segmento: revisar esa linea concreta,
//     b y c van a nivel fijo, a/d/e/f a W, g a Y.
// ---------------------------------------------------------------------------

// #include <Arduino.h>

// #include "display.h"
// #include "pines.h"

// const unsigned long MS_ENTRE_DIGITOS = 300;
// const unsigned long MS_ENTRE_ENGANCHES = 2000;

// unsigned long g_ultimoDigito = 0;
// unsigned long g_ultimoEnganche = 0;

// void setup() {
//   Serial.begin(115200);
//   display::iniciar();
//   display::enganchar();   // captura lo que haya en las entradas D al arrancar
//   Serial.println(F("diagnostico: recorriendo los 8 digitos, uno cada 300 ms"));
// }

// void loop() {
//   unsigned long ahora = millis();

//   if (ahora - g_ultimoEnganche >= MS_ENTRE_ENGANCHES) {
//     display::enganchar();
//     g_ultimoEnganche = ahora;
//     Serial.println(F("enganche: valor capturado del bus F"));
//   }

  // Multiplexado deliberadamente LENTO: en el sketch real esto corre miles de
  // veces por segundo y los ocho digitos se ven a la vez.
//   if (ahora - g_ultimoDigito >= MS_ENTRE_DIGITOS) {
//     display::refrescar();
//     g_ultimoDigito = ahora;
//   }
// }
