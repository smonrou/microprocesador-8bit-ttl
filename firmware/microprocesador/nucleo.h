// ---------------------------------------------------------------------------
// nucleo.h — unidad de control: ciclo fetch-decode-execute.
//
// Espeja sim/cpu.py: paso() avanza UN microciclo, correr() se construye sobre
// paso(), y "Ciclo N" numera instrucciones completadas (no microciclos).
//
// PURO: no toca pines ni Serial. Toda la E/S pasa por hal.h. Por eso el mismo
// código se ejecuta en el Arduino y en la PC contra el simulador.
//
// REGLA CENTRAL DEL PROYECTO: el Arduino no calcula. Aquí no hay ni un solo
// +, -, &, | o ^ entre valores de registro; toda operación se hace
// configurando el 74LS181 y leyendo F. La única excepción que permite el
// spec es Z = (F == 0), que es leer un resultado, no calcularlo.
//
// El PC tampoco se calcula aquí: es hardware (2× 74LS161). El núcleo solo
// pide contar (hal::incrementarPC) o cargar (hal::cargarPC) y lo lee de la
// placa; no hay copia en software. IR y MAR sí son variables de la unidad
// de control (A.2); los ++ de los índices de microciclo no son operaciones
// de ALU.
// ---------------------------------------------------------------------------

#ifndef NUCLEO_H
#define NUCLEO_H

#include <stdint.h>

#include "hal.h"
#include "isa.h"

// Estado de una instrucción, para el volcado en formato A.9.
struct Traza {
  uint16_t ciclo;         // instrucciones completadas, 1-based
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

// Motivos por los que correr() puede terminar.
#define FIN_HLT            0
#define FIN_LIMITE_CICLOS  1

class Nucleo {
 public:
  Nucleo();

  // PC, banderas y registros físicos a cero. CONSERVA la memoria, igual que
  // sim/cpu.py::reset(): RESET reinicia la ejecución, no borra el programa.
  void reiniciar();

  // Borra la memoria entera a 0x00 (que decodifica como NOP) y reinicia.
  void borrarTodo();

  // Avanza exactamente un microciclo.
  PasoResultado paso();

  // Ejecuta hasta HLT. Devuelve FIN_HLT o FIN_LIMITE_CICLOS.
  uint8_t correr(uint16_t limiteInstrucciones = 10000);

  // ── Memoria ────────────────────────────────────────────────────────────
  void escribirMemoria(uint8_t direccion, uint8_t valor);
  uint8_t leerMemoria(uint8_t direccion) const;

  // ── Estado ─────────────────────────────────────────────────────────────
  // El PC se lee del 74LS161, no de una copia (igual que A y B, abajo).
  uint8_t pc() const { return hal::leerPC(); }
  uint8_t ir() const { return ir_; }
  uint8_t mar() const { return mar_; }
  uint8_t z() const { return z_; }
  uint8_t c() const { return c_; }
  bool detenido() const { return detenido_; }
  uint16_t instrucciones() const { return instrucciones_; }
  bool instruccionEnCurso() const { return pasosPendientes_ > 0; }

  // Valores REALES de los registros físicos, leídos a través de la ALU
  // (F=A con M=1,S=1111; F=B con M=1,S=1010 — bitácora 6.2). No hay copia
  // en software que pueda divergir del hardware.
  uint8_t leerRegistroA();
  uint8_t leerRegistroB();

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

  // Primitivas del camino de datos.
  void cargarRegistroDesdeBus(uint8_t valor, uint8_t registro);
  uint8_t leerPorALU(uint8_t selector);
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

#endif  // NUCLEO_H
