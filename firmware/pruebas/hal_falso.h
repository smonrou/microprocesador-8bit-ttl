// ---------------------------------------------------------------------------
// hal_falso.h — emulación del camino de datos para las pruebas nativas.
//
// Implementa hal.h emulando los tres integrados físicos:
//   SN74LS181  ALU, tabla 2 (active-high) decodificada desde M / S3-S0 / C̄n
//   74LS273    registros A y B, enganchan en el flanco de subida
//   74LS157    mux de entrada a A
//   74LS161    ×2 en cascada: contador de programa de 8 bits
//
// Clave del diseño: la ALU falsa decide qué operación hacer leyendo las
// LÍNEAS DE CONTROL que el núcleo puso, no el nemónico de la instrucción. Si
// el núcleo configura S=0110 con M=1 creyendo que resta, aquí sale un XOR y
// la prueba falla — que es exactamente el error que de otro modo solo
// aparecería con el circuito ya soldado.
//
// Este archivo vive fuera de la carpeta del sketch a propósito: el IDE de
// Arduino compila todo lo que encuentra en ella, y esto no debe subir al chip.
// ---------------------------------------------------------------------------

#ifndef HAL_FALSO_H
#define HAL_FALSO_H

#include <stdint.h>

namespace hal_falso {

// Estado interno visible para las pruebas.
struct Estado {
  uint8_t registroA;
  uint8_t registroB;
  uint8_t pc;          // Q0-Q7 de los dos 74LS161
  uint8_t bus;
  uint8_t muxFuente;
  uint8_t m;
  uint8_t s;
  uint8_t cn;
  uint8_t ultimoByteMostrado;
  bool huboSalida;

  // Contadores, para verificar que el núcleo hace lo que dice.
  uint32_t pulsosA;
  uint32_t pulsosB;
  uint32_t pulsosPC;   // flancos del reloj del PC (cuentas + cargas)
  uint32_t cargasPC;   // de esos, cuántos fueron con /LOAD en bajo
  uint32_t esperas;
  uint32_t lecturasF;
};

// Reinicia el circuito emulado a su estado de encendido.
void reiniciar();

// Acceso de solo lectura al estado, para las aserciones de las pruebas.
const Estado& estado();

// Fuerza los registros — atajo para montar escenarios sin ejecutar programas.
void forzarRegistros(uint8_t a, uint8_t b);

// Fuerza el PC, para probar la vuelta 0xFF -> 0x00 sin 255 pulsos.
void forzarPC(uint8_t pc);

}  // namespace hal_falso

#endif  // HAL_FALSO_H
