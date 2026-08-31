// ---------------------------------------------------------------------------
// consola.cpp — implementación del protocolo serial.
// ---------------------------------------------------------------------------

#ifdef ARDUINO

#include "consola.h"

#include <Arduino.h>
#include <ctype.h>    // toupper: no depender de que Arduino.h lo arrastre
#include <stdlib.h>
#include <string.h>

#include "display.h"
#include "formato.h"

namespace {

const uint8_t LINEA_MAX = 96;

Nucleo* g_nucleo = 0;
char g_linea[LINEA_MAX];
uint8_t g_largo = 0;
uint16_t g_retardo = 200;   // ms entre instrucciones en modo RUN

// Espera manteniendo vivo el multiplexado del display: si se parara durante
// el retardo, el dígito activo quedaría fijo y el otro apagado.
void esperarRefrescando(uint16_t milisegundos) {
  uint32_t fin = millis() + milisegundos;
  while (millis() < fin) {
    display::refrescar();
    delay(2);
  }
}

bool leerNumero(const char* texto, long* destino) {
  if (texto == 0 || *texto == '\0') return false;
  char* sobrante = 0;
  long valor = strtol(texto, &sobrante, 0);   // base 0: acepta 0x.. y decimal
  if (sobrante == texto || *sobrante != '\0') return false;
  *destino = valor;
  return true;
}

bool enRango(long valor) {
  return valor >= 0 && valor <= 255;
}

void imprimirBloqueYClaves() {
  char bloque[FORMATO_BUFFER];
  formato::bloqueCiclo(g_nucleo->traza(), bloque, sizeof(bloque));
  Serial.println(bloque);

  char linea[160];
  formato::lineaClaveValor(g_nucleo->traza(), g_nucleo->detenido(),
                           linea, sizeof(linea));
  Serial.println(linea);
}

void imprimirEstado() {
  // Los valores de A y B se leen del registro FÍSICO a través de la ALU
  // (F=A con M=1,S=1111). No hay copia en software que pueda mentir.
  uint8_t a = g_nucleo->leerRegistroA();
  uint8_t b = g_nucleo->leerRegistroB();

  Serial.print(F("PC=0x"));   if (g_nucleo->pc() < 16) Serial.print('0');
  Serial.print(g_nucleo->pc(), HEX);
  Serial.print(F("  IR=0x"));  if (g_nucleo->ir() < 16) Serial.print('0');
  Serial.print(g_nucleo->ir(), HEX);
  Serial.print(F("  A=0x"));   if (a < 16) Serial.print('0');
  Serial.print(a, HEX);
  Serial.print(F("  B=0x"));   if (b < 16) Serial.print('0');
  Serial.print(b, HEX);
  Serial.print(F("  Z="));     Serial.print(g_nucleo->z());
  Serial.print(F("  C="));     Serial.print(g_nucleo->c());
  Serial.print(F("  "));
  Serial.println(g_nucleo->detenido() ? F("DETENIDO") : F("listo"));

  char linea[160];
  formato::lineaEstado(g_nucleo->pc(), g_nucleo->ir(), a, b,
                       g_nucleo->z(), g_nucleo->c(), g_nucleo->detenido(),
                       linea, sizeof(linea));
  Serial.println(linea);
}

void comandoLoad(char* argumentos) {
  char* textoDir = strtok(argumentos, " \t");
  char* textoVal = strtok(0, " \t");
  long direccion, valor;

  if (!leerNumero(textoDir, &direccion) || !leerNumero(textoVal, &valor)) {
    Serial.println(F("ERR LOAD requiere <dir> <byte>"));
    return;
  }
  if (!enRango(direccion) || !enRango(valor)) {
    Serial.println(F("ERR valor fuera de rango (0-255)"));
    return;
  }

  g_nucleo->escribirMemoria((uint8_t)direccion, (uint8_t)valor);

  // La confirmación es lo que impide perder comandos en silencio al pegar
  // muchas líneas seguidas en el monitor serie.
  Serial.print(F("OK dir=0x"));
  if (direccion < 16) Serial.print('0');
  Serial.print((int)direccion, HEX);
  Serial.print(F(" val=0x"));
  if (valor < 16) Serial.print('0');
  Serial.println((int)valor, HEX);
}

void comandoLoadB(char* argumentos) {
  char* textoDir = strtok(argumentos, " \t");
  long direccion;
  if (!leerNumero(textoDir, &direccion) || !enRango(direccion)) {
    Serial.println(F("ERR LOADB requiere <dir> <hex> [hex...]"));
    return;
  }

  uint16_t escritos = 0;
  for (char* token = strtok(0, " \t"); token != 0; token = strtok(0, " \t")) {
    long valor;
    if (!leerNumero(token, &valor) || !enRango(valor)) {
      Serial.print(F("ERR byte invalido: "));
      Serial.println(token);
      return;
    }
    if (direccion + escritos > 255) {
      Serial.println(F("ERR el bloque excede la memoria"));
      return;
    }
    g_nucleo->escribirMemoria((uint8_t)(direccion + escritos), (uint8_t)valor);
    escritos++;
  }

  if (escritos == 0) {
    Serial.println(F("ERR LOADB sin bytes"));
    return;
  }

  Serial.print(F("OK dir=0x"));
  if (direccion < 16) Serial.print('0');
  Serial.print((int)direccion, HEX);
  Serial.print(F(" n="));
  Serial.println(escritos);
}

void comandoRun() {
  if (g_nucleo->detenido()) {
    Serial.println(F("ERR la CPU esta detenida; usa RESET"));
    return;
  }

  Serial.println(F("--- RUN ---"));
  uint16_t tope = 10000;

  while (!g_nucleo->detenido()) {
    PasoResultado paso = g_nucleo->paso();
    if (!paso.valido) break;

    if (paso.instruccionCompleta) {
      imprimirBloqueYClaves();
      if (g_nucleo->instrucciones() > tope) {
        Serial.println(F("ERR limite de instrucciones; posible bucle infinito"));
        return;
      }
      if (g_retardo > 0) esperarRefrescando(g_retardo);
    }
    display::refrescar();
  }

  Serial.println(F("--- HLT ---"));
  imprimirEstado();
}

void comandoStep() {
  if (g_nucleo->detenido()) {
    Serial.println(F("ERR la CPU esta detenida; usa RESET"));
    return;
  }

  PasoResultado paso = g_nucleo->paso();
  if (!paso.valido) {
    Serial.println(F("ERR no se pudo avanzar"));
    return;
  }

  Serial.print(F("paso: "));
  Serial.println(nombrePaso(paso.paso));

  // El bloque de A.9 se imprime cuando la instruccion termina: "Ciclo N"
  // numera instrucciones completadas, no microciclos.
  if (paso.instruccionCompleta) {
    imprimirBloqueYClaves();
  } else {
    Serial.print(F("#paso="));
    Serial.println(nombrePaso(paso.paso));
  }
}

void comandoDump(char* argumentos) {
  char* textoIni = strtok(argumentos, " \t");
  char* textoFin = strtok(0, " \t");
  long inicio = 0, fin = 255;

  if (textoIni != 0 && (!leerNumero(textoIni, &inicio) || !enRango(inicio))) {
    Serial.println(F("ERR DUMP requiere <ini> [fin]"));
    return;
  }
  if (textoFin != 0 && (!leerNumero(textoFin, &fin) || !enRango(fin))) {
    Serial.println(F("ERR DUMP requiere <ini> [fin]"));
    return;
  }
  if (fin < inicio) {
    Serial.println(F("ERR el final va antes del inicio"));
    return;
  }

  for (long direccion = inicio; direccion <= fin; direccion += 16) {
    Serial.print(F("0x"));
    if (direccion < 16) Serial.print('0');
    Serial.print((int)direccion, HEX);
    Serial.print(F(": "));

    for (long i = direccion; i < direccion + 16 && i <= fin; i++) {
      uint8_t valor = g_nucleo->leerMemoria((uint8_t)i);
      if (valor < 16) Serial.print('0');
      Serial.print(valor, HEX);
      Serial.print(' ');
    }
    Serial.println();
  }
}

void comandoVel(char* argumentos) {
  char* texto = strtok(argumentos, " \t");
  long milisegundos;
  if (!leerNumero(texto, &milisegundos) || milisegundos < 0 || milisegundos > 5000) {
    Serial.println(F("ERR VEL requiere <ms> entre 0 y 5000"));
    return;
  }
  g_retardo = (uint16_t)milisegundos;
  Serial.print(F("OK vel="));
  Serial.println(g_retardo);
}

void comandoHelp() {
  Serial.println(F("LOAD <dir> <byte>     escribe un byte"));
  Serial.println(F("LOADB <dir> <hex...>  carga un bloque"));
  Serial.println(F("RUN                   ejecuta hasta HLT"));
  Serial.println(F("STEP                  avanza un microciclo"));
  Serial.println(F("RESET                 PC=0, banderas a 0 (conserva memoria)"));
  Serial.println(F("BORRAR                borra toda la memoria"));
  Serial.println(F("DUMP <ini> [fin]      vuelca memoria"));
  Serial.println(F("STATE                 estado actual"));
  Serial.println(F("VEL <ms>              retardo entre instrucciones en RUN"));
}

void ejecutarLinea(char* linea) {
  char* orden = strtok(linea, " \t");
  if (orden == 0) return;

  for (char* p = orden; *p; p++) {
    *p = toupper(*p);
  }
  char* argumentos = strtok(0, "");

  if      (strcmp(orden, "LOAD")   == 0) comandoLoad(argumentos);
  else if (strcmp(orden, "LOADB")  == 0) comandoLoadB(argumentos);
  else if (strcmp(orden, "RUN")    == 0) comandoRun();
  else if (strcmp(orden, "STEP")   == 0) comandoStep();
  else if (strcmp(orden, "DUMP")   == 0) comandoDump(argumentos);
  else if (strcmp(orden, "VEL")    == 0) comandoVel(argumentos);
  else if (strcmp(orden, "STATE")  == 0) imprimirEstado();
  else if (strcmp(orden, "HELP")   == 0) comandoHelp();
  else if (strcmp(orden, "RESET")  == 0) {
    g_nucleo->reiniciar();
    Serial.println(F("OK reset"));
    imprimirEstado();
  } else if (strcmp(orden, "BORRAR") == 0) {
    g_nucleo->borrarTodo();
    Serial.println(F("OK memoria borrada"));
  } else {
    Serial.print(F("ERR comando desconocido: "));
    Serial.println(orden);
  }
}

}  // namespace

namespace consola {

void iniciar(Nucleo* nucleo) {
  g_nucleo = nucleo;
  g_largo = 0;

  Serial.println();
  Serial.println(F("Microprocesador de 8 bits - unidad de control lista"));
  Serial.println(F("ALU: 2x SN74LS181  Registros: 2x 74LS273  Mux: 2x 74LS157"));
  Serial.println(F("Escribe HELP para ver los comandos."));
  imprimirEstado();
}

void atender() {
  while (Serial.available() > 0) {
    char caracter = (char)Serial.read();

    // Algunos terminales (p.ej. la Virtual Terminal de Proteus) mandan solo
    // \r al presionar Enter, sin \n. Tratar \r igual que \n evita que el
    // comando se quede esperando un terminador que nunca llega. Si el
    // terminal manda \r\n completo, el \n que sigue cae con g_largo=0 y no
    // se re-ejecuta nada.
    if (caracter == '\r' || caracter == '\n') {
      g_linea[g_largo] = '\0';
      if (g_largo > 0) ejecutarLinea(g_linea);
      g_largo = 0;
      continue;
    }

    if (g_largo < LINEA_MAX - 1) {
      g_linea[g_largo++] = caracter;
    } else {
      // Línea demasiado larga: se descarta entera para no ejecutar un
      // comando truncado a medias.
      g_largo = 0;
      Serial.println(F("ERR linea demasiado larga"));
    }
  }
}

}  // namespace consola

#endif  // ARDUINO
