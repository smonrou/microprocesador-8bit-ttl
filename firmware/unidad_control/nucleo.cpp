
#include "nucleo.h"

#include "hal.h"

// El PC arranca donde lo deja el CLEAR
static_assert(DIRECCION_INICIO == 0x00, "el CLEAR de los 74LS161 deja el PC en 0x00");

namespace {

// Secuencia de microciclos según la forma de la instrucción
void secuenciaDePasos(uint8_t microciclos, uint8_t* destino) {
  if (microciclos == PASOS_ALU) {
    destino[0] = PASO_FETCH;
    destino[1] = PASO_DECODE;
    destino[2] = PASO_EXECUTE;
    destino[3] = PASO_WAIT;
    destino[4] = PASO_WRITE;
  } else if (microciclos == PASOS_2BYTES) {
    destino[0] = PASO_FETCH;
    destino[1] = PASO_DECODE;
    destino[2] = PASO_FETCH2;
    destino[3] = PASO_EXECUTE;
  } else {  // PASOS_CONTROL
    destino[0] = PASO_FETCH;
    destino[1] = PASO_DECODE;
    destino[2] = PASO_EXECUTE;
  }
}

}

Nucleo::Nucleo() {
  borrarTodo();
}

void Nucleo::borrarTodo() {
  for (uint16_t i = 0; i < MEMORIA_TAM; i++) {
    memoria_[i] = 0x00;    //memoria vacía decodifica como NOP
  }
  reiniciar();
}

void Nucleo::reiniciar() {
  ir_ = 0;
  mar_ = 0;
  z_ = 0;
  c_ = 0;
  detenido_ = false;
  instrucciones_ = 0;
  actual_ = 0;
  operando_ = 0;
  pasosPendientes_ = 0;
  indicePaso_ = 0;
  ultimaSalida_ = 0;
  huboSalida_ = false;
  traza_ = Traza();

  //CLEAR asíncrono para que PC = DIRECCION_INICIO.
  hal::limpiarRegistros();
}

void Nucleo::escribirMemoria(uint8_t direccion, uint8_t valor) {
  memoria_[direccion] = valor;
}

uint8_t Nucleo::leerMemoria(uint8_t direccion) const {
  return memoria_[direccion];
}

void Nucleo::engancharDesdeBus(uint8_t valor, uint8_t registro) {
  hal::ponerBus(valor);
  hal::seleccionarMux(MUX_BUS);
  // Se elige el registro por cuál reloj se pulsa. Nunca los dos, nunca la misma línea.
  if (registro == REG_A) {
    hal::pulsoClockA();
  } else {
    hal::pulsoClockB();
  }
}

uint8_t Nucleo::muestrearALU(uint8_t m, uint8_t s, uint8_t cn) {
  // Configurar operación de identidad
  hal::configurarALU(m, s, cn);
  hal::esperarPropagacion();
  return hal::leerF();
}
//Ver que hay en A y en B
uint8_t Nucleo::registroA() {
  return muestrearALU(ALU_ARITMETICO, ALU_IDENTIDAD_A, CN_IDENTIDAD);
}

uint8_t Nucleo::registroB() {
  return muestrearALU(ALU_LOGICO, ALU_IDENTIDAD_B, CN_LOGICO);
}

void Nucleo::configurarOperacion(uint8_t opcode) {
  
  // SUB y XOR diferenciados por M
  uint8_t m, s, cn;
  switch (opcode) {
    case OP_ADD: m = ALU_ARITMETICO; s = ALU_ADD; cn = CN_ADD;    break;
    case OP_SUB: m = ALU_ARITMETICO; s = ALU_SUB; cn = CN_SUB;    break;
    case OP_AND: m = ALU_LOGICO;     s = ALU_AND; cn = CN_LOGICO; break;
    case OP_OR:  m = ALU_LOGICO;     s = ALU_OR;  cn = CN_LOGICO; break;
    default:     m = ALU_LOGICO;     s = ALU_XOR; cn = CN_LOGICO; break;  // XOR
  }

  traza_.aluM = m;
  traza_.aluS = s;
  traza_.aluCn = cn;
  traza_.usoALU = true;

  hal::configurarALU(m, s, cn);
}


void Nucleo::empezarInstruccion() {
  // FETCH: MAR <- PC; IR <- Mem[MAR]; PC++
  mar_ = hal::leerPC();
  uint8_t pcAntes = mar_;
  ir_ = memoria_[mar_];
  hal::incrementarPC();

  actual_ = &TABLA_OPCODES[ir_ >> 4];
  operando_ = 0;

  traza_ = Traza();
  traza_.ciclo = static_cast<uint16_t>(instrucciones_ + 1);
  traza_.pcAntes = pcAntes;
  traza_.ir = ir_;
  traza_.opcode = actual_->opcode;
  traza_.nemonico = actual_->nemonico;
  traza_.bytes = actual_->bytes;
  traza_.modo = actual_->modo;
  traza_.categoria = actual_->categoria;
  traza_.registro = actual_->registro;
  traza_.z = z_;
  traza_.c = c_;

  secuenciaDePasos(actual_->microciclos, pasos_);
  pasosPendientes_ = actual_->microciclos;
  indicePaso_ = 1;   // FETCH ya se ejecutó
}

PasoResultado Nucleo::paso() {
  PasoResultado resultado;
  resultado.paso = PASO_FETCH;
  resultado.instruccionCompleta = false;
  resultado.valido = true;

  if (detenido_) {
    resultado.valido = false;
    return resultado;
  }

  if (pasosPendientes_ == 0) {
    empezarInstruccion();
    resultado.paso = PASO_FETCH;
    resultado.instruccionCompleta = (indicePaso_ >= pasosPendientes_);
    if (resultado.instruccionCompleta) {
      instrucciones_++;
      pasosPendientes_ = 0;
    }
    return resultado;
  }

  uint8_t paso = pasos_[indicePaso_];
  ejecutarMicrociclo(paso);
  indicePaso_++;
  resultado.paso = paso;

  if (indicePaso_ >= pasosPendientes_) {
    traza_.pcDespues = hal::leerPC();
    traza_.z = z_;
    traza_.c = c_;
    instrucciones_++;
    pasosPendientes_ = 0;
    indicePaso_ = 0;
    resultado.instruccionCompleta = true;
  }

  return resultado;
}

void Nucleo::ejecutarMicrociclo(uint8_t paso) {
  switch (paso) {
    case PASO_DECODE:
      // Ya separado en actual_ >> 4
      break;

    case PASO_FETCH2:
      operando_ = memoria_[hal::leerPC()];
      hal::incrementarPC();
      traza_.operando = operando_;
      traza_.tieneOperando = true;
      break;

    case PASO_WAIT:
      // Propagación por los dos 181 en cascada.
      hal::esperarPropagacion();
      break;

    case PASO_EXECUTE:
      faseEjecutar();
      break;

    case PASO_WRITE:
      faseEscribir();
      break;

    default:
      break;
  }
}

void Nucleo::faseEjecutar() {
  switch (actual_->categoria) {
    case CAT_ALU:
      // Se leen A y B para la traza ANTES de configurar la operación y salen del registro físico
      traza_.aAntes = registroA();
      traza_.bAntes = registroB();
      configurarOperacion(actual_->opcode);
      break;

    case CAT_CARGA_DIRECTA: {
      uint8_t valor = memoria_[operando_];
      engancharDesdeBus(valor, actual_->registro);
      if (actual_->registro == REG_A) {
        traza_.aDespues = valor;
      } else {
        traza_.bDespues = valor;
      }
      break;
    }

    case CAT_CARGA_INMEDIATA:
      engancharDesdeBus(operando_, actual_->registro);
      if (actual_->registro == REG_A) {
        traza_.aDespues = operando_;
      } else {
        traza_.bDespues = operando_;
      }
      break;

    case CAT_GUARDA_DIRECTA: {
      uint8_t valorA = registroA();
      memoria_[operando_] = valorA;
      traza_.aAntes = valorA;
      traza_.aDespues = valorA;
      break;
    }

    case CAT_SALTO_INCONDICIONAL:
      hal::cargarPC(operando_);
      break;

    case CAT_SALTO_CONDICIONAL: {
      bool condicion = (actual_->opcode == OP_JZ) ? (z_ == 1) : (z_ == 0);
      if (condicion) {
        hal::cargarPC(operando_);
      }
      break;
    }

    case CAT_SALIDA: {
      uint8_t valorA = registroA();
      ultimaSalida_ = valorA;
      huboSalida_ = true;
      traza_.aAntes = valorA;
      traza_.aDespues = valorA;
      traza_.valorSalida = valorA;
      traza_.huboSalida = true;
      hal::mostrarByte(valorA);
      break;
    }

    case CAT_CONTROL:
      if (actual_->opcode == OP_HLT) {
        detenido_ = true;
      }
      // NOP: nada.
      break;

    default:
      break;
  }
}

void Nucleo::faseEscribir() {
  // Solo llegan aquí las operaciones de ALU.
  // Leer antes de escribir porque cambia la configuración de la ALU la lectura
  uint8_t f = hal::leerF();

  // Comparación del bus F
  z_ = (f == 0) ? 1 : 0;

  bool acarreo = hal::huboAcarreo();
#if CARRY_SUB_INVERTIDO
  if (actual_->opcode == OP_SUB) {
    acarreo = !acarreo;
  }
#endif
  c_ = acarreo ? 1 : 0;
  // Resultado regresa por el mux sin tocar al arduino
  hal::seleccionarMux(MUX_ALU);
  hal::pulsoClockA();

  traza_.aDespues = f;
  traza_.bDespues = traza_.bAntes;
  traza_.z = z_;
  traza_.c = c_;
}

uint8_t Nucleo::correr(uint16_t limiteInstrucciones) {
  // RUN
  while (!detenido_) {
    paso();
    if (instrucciones_ > limiteInstrucciones) {
      return FIN_LIMITE_CICLOS;
    }
  }
  return FIN_HLT;
}
