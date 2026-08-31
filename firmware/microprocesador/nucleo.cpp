// ---------------------------------------------------------------------------
// nucleo.cpp — implementación de la unidad de control.
// ---------------------------------------------------------------------------

#include "nucleo.h"

#include "hal.h"

namespace {

// Secuencia de microciclos según la forma de la instrucción (decisión B.1).
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

}  // namespace

Nucleo::Nucleo() {
  borrarTodo();
}

void Nucleo::borrarTodo() {
  for (uint16_t i = 0; i < MEMORIA_TAM; i++) {
    memoria_[i] = 0x00;   // A.6: memoria vacía decodifica como NOP
  }
  reiniciar();
}

void Nucleo::reiniciar() {
  pc_ = DIRECCION_INICIO;
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

  hal::limpiarRegistros();   // CLEAR asíncrono de ambos 74LS273
}

void Nucleo::escribirMemoria(uint8_t direccion, uint8_t valor) {
  memoria_[direccion] = valor;
}

uint8_t Nucleo::leerMemoria(uint8_t direccion) const {
  return memoria_[direccion];
}

// ── Primitivas del camino de datos ───────────────────────────────────────

void Nucleo::cargarRegistroDesdeBus(uint8_t valor, uint8_t registro) {
  hal::ponerBus(valor);
  hal::seleccionarMux(MUX_BUS);
  // El 74LS273 no tiene habilitación: se elige el registro por cuál reloj se
  // pulsa. Nunca los dos, nunca la misma línea.
  if (registro == REG_A) {
    hal::pulsoClockA();
  } else {
    hal::pulsoClockB();
  }
}

uint8_t Nucleo::leerPorALU(uint8_t selector) {
  // Las salidas del 74LS273 van al 181, no al Arduino. Para conocer el valor
  // real de un registro se hace pasar por la ALU sin alterarlo y se lee F.
  hal::configurarALU(ALU_LOGICO, selector, CN_LOGICO);
  hal::esperarPropagacion();
  return hal::leerF();
}

uint8_t Nucleo::leerRegistroA() { return leerPorALU(ALU_PASAR_A); }
uint8_t Nucleo::leerRegistroB() { return leerPorALU(ALU_PASAR_B); }

void Nucleo::configurarOperacion(uint8_t opcode) {
  // Tabla A.3, verificada contra el datasheet TI SDLS136 pág. 4, TABLE 2.
  // SUB y XOR comparten S=0110: los distingue M. Error frecuente.
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

// ── Máquina de microciclos ───────────────────────────────────────────────

void Nucleo::empezarInstruccion() {
  uint8_t pcAntes = pc_;

  // FETCH: MAR <- PC; IR <- Mem[MAR]; PC++
  mar_ = pc_;
  ir_ = memoria_[mar_];
  pc_++;

  actual_ = &TABLA_OPCODES[ir_ >> 4];   // A.4: el opcode son siempre 4 bits
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
    // Una instrucción de un solo microciclo no existe en este set, pero si
    // existiera quedaría completa aquí.
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
    traza_.pcDespues = pc_;
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
      // Informativo: el opcode ya se separó en el FETCH. Existe como
      // microciclo propio porque A.8 lo describe así.
      break;

    case PASO_FETCH2:
      operando_ = memoria_[pc_];
      pc_++;
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
      // Se leen A y B para la traza ANTES de configurar la operación: el
      // volcado de estado debe mostrar los operandos, y estos valores salen
      // del registro físico, no de una copia.
      traza_.aAntes = leerRegistroA();
      traza_.bAntes = leerRegistroB();
      configurarOperacion(actual_->opcode);
      break;

    case CAT_CARGA_DIRECTA: {
      uint8_t valor = memoria_[operando_];
      cargarRegistroDesdeBus(valor, actual_->registro);
      if (actual_->registro == REG_A) {
        traza_.aDespues = valor;
      } else {
        traza_.bDespues = valor;
      }
      break;
    }

    case CAT_CARGA_INMEDIATA:
      cargarRegistroDesdeBus(operando_, actual_->registro);
      if (actual_->registro == REG_A) {
        traza_.aDespues = operando_;
      } else {
        traza_.bDespues = operando_;
      }
      break;

    case CAT_GUARDA_DIRECTA: {
      uint8_t valorA = leerRegistroA();
      memoria_[operando_] = valorA;
      traza_.aAntes = valorA;
      traza_.aDespues = valorA;
      break;
    }

    case CAT_SALTO_INCONDICIONAL:
      pc_ = operando_;
      break;

    case CAT_SALTO_CONDICIONAL: {
      // A.5: JZ salta con Z=1, JNZ con Z=0. Las banderas NO se tocan aquí.
      bool condicion = (actual_->opcode == OP_JZ) ? (z_ == 1) : (z_ == 0);
      if (condicion) {
        pc_ = operando_;
      }
      break;
    }

    case CAT_SALIDA: {
      uint8_t valorA = leerRegistroA();
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
  //
  // ORDEN CRÍTICO: F se lee ANTES de pulsar el reloj. El 181 es
  // combinacional, así que F siempre vale (A actual) OP B. En cuanto el
  // pulso engancha F en el registro A, F pasa a valer (A nuevo) OP B, que es
  // un valor distinto. Leerlo después daría basura.
  uint8_t f = hal::leerF();

  // Única operación en software que permite el spec: leer si el resultado
  // es cero. No es un cálculo, es una comparación del bus F.
  z_ = (f == 0) ? 1 : 0;

  bool acarreo = hal::huboAcarreo();
#if CARRY_SUB_INVERTIDO
  // Pendiente Parte C punto 5: si la prueba en protoboard demuestra que la
  // polaridad del acarreo en resta es la contraria, esto la corrige.
  if (actual_->opcode == OP_SUB) {
    acarreo = !acarreo;
  }
#endif
  c_ = acarreo ? 1 : 0;

  // Ahora sí: el resultado vuelve al registro A por el camino del mux, sin
  // pasar por el Arduino.
  hal::seleccionarMux(MUX_ALU);
  hal::pulsoClockA();

  traza_.aDespues = f;
  traza_.bDespues = traza_.bAntes;
  traza_.z = z_;
  traza_.c = c_;
}

uint8_t Nucleo::correr(uint16_t limiteInstrucciones) {
  // RUN se construye sobre paso(): una sola implementación de la lógica, sin
  // riesgo de que los dos modos discrepen.
  while (!detenido_) {
    paso();
    if (instrucciones_ > limiteInstrucciones) {
      return FIN_LIMITE_CICLOS;
    }
  }
  return FIN_HLT;
}
