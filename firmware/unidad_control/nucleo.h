
#ifndef NUCLEO_H
#define NUCLEO_H

#include <stdint.h>

#include "hal.h"
#include "isa.h"

struct Traza {
  uint16_t ciclo;
  uint8_t pcAntes;
  uint8_t ir;
  uint8_t opcode;
  const char* nemonico;
  uint8_t bytes;
  uint8_t modo;
  uint8_t categoria;
  uint8_t registro;
  uint8_t operando;
  bool tieneOperando;
  uint8_t aAntes;
  uint8_t bAntes;
  uint8_t aDespues;
  uint8_t bDespues;
  uint8_t aluM;
  uint8_t aluS;
  uint8_t aluCn;
  bool usoALU;
  uint8_t z;
  uint8_t c;
  uint8_t pcDespues;
  uint8_t valorSalida;
  bool huboSalida;
};

// Resultado de un microciclo.
struct PasoResultado {
  uint8_t paso;                // PASO_FETCH, PASO_DECODE, ...
  bool instruccionCompleta;    // true cuando la traza ya es válida
  bool valido;                 // false si la CPU estaba detenida
};

#define FIN_HLT            0
#define FIN_LIMITE_CICLOS  1

class Nucleo {
 public:
  Nucleo();

  void reiniciar();

  // Borra la memoria entera a 0x00  y reinicia.
  void borrarTodo();

  // Avanza un microciclo.
  PasoResultado paso();

  // Ejecuta hasta HLT. Devuelve FIN_HLT o FIN_LIMITE_CICLOS.
  uint8_t correr(uint16_t limiteInstrucciones = 10000);

  void escribirMemoria(uint8_t direccion, uint8_t valor);
  uint8_t leerMemoria(uint8_t direccion) const;

  uint8_t pc() const { return hal::leerPC(); }
  uint8_t ir() const { return ir_; }
  uint8_t mar() const { return mar_; }
  uint8_t z() const { return z_; }
  uint8_t c() const { return c_; }
  bool detenido() const { return detenido_; }
  uint16_t instrucciones() const { return instrucciones_; }
  bool instruccionEnCurso() const { return pasosPendientes_ > 0; }

  uint8_t registroA();
  uint8_t registroB();

  const Traza& traza() const { return traza_; }

  // Último valor que ejecutó OUT.
  uint8_t ultimaSalida() const { return ultimaSalida_; }
  bool huboSalida() const { return huboSalida_; }
  void limpiarSalida() { huboSalida_ = false; }

 private:
  void empezarInstruccion();
  void ejecutarMicrociclo(uint8_t paso);
  void faseEjecutar();
  void faseEscribir();

  void engancharDesdeBus(uint8_t valor, uint8_t registro);
  uint8_t muestrearALU(uint8_t m, uint8_t s, uint8_t cn);
  void configurarOperacion(uint8_t opcode);

  uint8_t memoria_[MEMORIA_TAM];
  uint8_t ir_;
  uint8_t mar_;
  uint8_t z_;
  uint8_t c_;
  bool detenido_;
  uint16_t instrucciones_;

  const Instruccion* actual_;
  uint8_t operando_;
  uint8_t pasos_[PASOS_ALU];
  uint8_t pasosPendientes_;
  uint8_t indicePaso_;

  Traza traza_;
  uint8_t ultimaSalida_;
  bool huboSalida_;
};

#endif
