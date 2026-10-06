// Prueba de la fase 5: cada línea entre el Mega y la placa, una por una.
//
// Nace de una traza en la que el PC pasó de 0x00 a 0x11 en su primer conteo,
// A se cargó con 0x40 y se leyó 0x50, y B apareció con 0x40 sin que nadie la
// cargara. El firmware pasa sus pruebas contra el simulador, así que la
// sospecha es el cableado: temporales de la fase 4 peleando con el Mega, o un
// cable fuera de su sitio. Este sketch lo dice bit por bit.
//
// Los pines son los de firmware/unidad_control/pines.h (el IDE no deja
// incluirlo desde otra carpeta de sketch; si cambia allá, cambia aquí). Las
// secuencias copian hal_arduino.cpp, así que un OK aquí vale para el firmware.
//
// Comandos (mayúscula o minúscula) en el monitor serial a 115200:
//   T = prueba completa      R = CLEAR y estado     H = ayuda
//   C = cuenta el PC y lo muestra                    L = leer el PC
//   A = leer A por la ALU    B = leer B por la ALU
//   P = solo la prueba de pines de salida (contención)
//   M = solo el mapa de entradas de los 181 y del PC (prueba 10)
//
// Cada renglón dice OK o FALLA. En las fallas, "bits malos" es esperado XOR
// leído: un 1 marca el bit cuyo cable hay que revisar.

// ── Pines (pines.h) ─────────────────────────────────────────────────────────
const uint8_t PIN_CLOCK_A = 41;
const uint8_t PIN_CLOCK_B = 40;
const uint8_t PIN_MUX = 39;        // LOW = bus, HIGH = salida de ALU
const uint8_t PIN_CLEAR = 38;      // activo en BAJO
const uint8_t PIN_CARRY = 2;       // C̄n+4: BAJO = hubo acarreo
const uint8_t PIN_CLOCK_PC = 42;
const uint8_t PIN_CARGA_PC = 43;   // /LOAD, activo en BAJO
const uint8_t PIN_CLOCK_SALIDA = 7;

// PORTA = bus D (pin 22 + bit). PORTC = F (pin 37 - bit). PORTK = PC (A8 + bit).
// PORTL bits 0-5 = S0-S3, M, C̄n (pin 49 - bit); bits 6-7 son /LOAD y CLK PC.
const uint8_t BIT_M = 4;
const uint8_t BIT_CN = 5;
const uint8_t MASCARA_NO_ALU = 0xC0;

const uint8_t MICROS_PULSO = 5;
const uint8_t MICROS_PROPAGACION = 50;

// Funciones del 74LS181 (M, S, C̄n)
const uint8_t S_PASAR_A = 0b1111;   // M=1
const uint8_t S_PASAR_B = 0b1010;   // M=1
const uint8_t S_CERO = 0b0011;      // M=1: F = 0 sin importar A y B
const uint8_t S_UNOS = 0b1100;      // M=1: F = 1111 1111 sin importar A y B
const uint8_t S_ADD = 0b1001;       // M=0, C̄n=1
const uint8_t S_SUB = 0b0110;       // M=0, C̄n=0

// Valores de prueba: unos caminantes, ceros caminantes y dos alternados.
const uint8_t PATRONES[] = {0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80,
                            0xFE, 0xFD, 0xFB, 0xF7, 0xEF, 0xDF, 0xBF, 0x7F,
                            0x55, 0xAA};
const uint8_t N_PATRONES = sizeof(PATRONES);

uint16_t g_fallas = 0;

// ── Primitivas (copiadas de hal_arduino.cpp) ────────────────────────────────

void ponerBus(uint8_t v) { PORTA = v; }

void seleccionarMux(bool alu) { digitalWrite(PIN_MUX, alu ? HIGH : LOW); }

void configurarALU(uint8_t m, uint8_t s, uint8_t cn) {
  uint8_t control = s & 0x0F;
  if (m) control |= (1 << BIT_M);
  if (cn) control |= (1 << BIT_CN);
  PORTL = (PORTL & MASCARA_NO_ALU) | control;
}

uint8_t leerF() {
  delayMicroseconds(MICROS_PROPAGACION);
  return PINC;
}

void pulso(uint8_t pin) {   // flanco de subida: el 273 carga y el 161 cuenta
  digitalWrite(pin, LOW);
  delayMicroseconds(MICROS_PULSO);
  digitalWrite(pin, HIGH);
  delayMicroseconds(MICROS_PULSO);
  digitalWrite(pin, LOW);
}

void limpiar() {
  digitalWrite(PIN_CLEAR, LOW);
  delayMicroseconds(MICROS_PULSO);
  digitalWrite(PIN_CLEAR, HIGH);
}

void contarPC() {
  digitalWrite(PIN_CARGA_PC, HIGH);
  pulso(PIN_CLOCK_PC);
}

void cargarPC(uint8_t v) {
  ponerBus(v);
  digitalWrite(PIN_CARGA_PC, LOW);
  pulso(PIN_CLOCK_PC);
  digitalWrite(PIN_CARGA_PC, HIGH);
}

uint8_t leerPC() { return PINK; }

uint8_t leerA() { configurarALU(1, S_PASAR_A, 1); return leerF(); }
uint8_t leerB() { configurarALU(1, S_PASAR_B, 1); return leerF(); }

void cargarA(uint8_t v) { ponerBus(v); seleccionarMux(false); pulso(PIN_CLOCK_A); }
void cargarB(uint8_t v) { ponerBus(v); seleccionarMux(false); pulso(PIN_CLOCK_B); }

bool huboAcarreo() { return digitalRead(PIN_CARRY) == LOW; }

void reposo() {
  digitalWrite(PIN_CLOCK_A, LOW);
  digitalWrite(PIN_CLOCK_B, LOW);
  digitalWrite(PIN_CLOCK_PC, LOW);
  digitalWrite(PIN_CLOCK_SALIDA, LOW);
  digitalWrite(PIN_MUX, LOW);
  digitalWrite(PIN_CLEAR, HIGH);
  digitalWrite(PIN_CARGA_PC, HIGH);
  ponerBus(0x00);
  configurarALU(1, S_PASAR_A, 1);
}

// ── Impresión ───────────────────────────────────────────────────────────────

void imprimirBin(uint8_t v) {
  for (int8_t b = 7; b >= 0; b--) {
    Serial.print((v >> b) & 1);
    if (b == 4) Serial.print(' ');
  }
  Serial.print(F(" (0x"));
  if (v < 0x10) Serial.print('0');
  Serial.print(v, HEX);
  Serial.print(')');
}

// Devuelve true si coincide. Si no, imprime la FALLA con los bits malos.
bool comparar(const __FlashStringHelper* que, uint8_t esperado, uint8_t leido) {
  if (esperado == leido) return true;
  g_fallas++;
  Serial.print(F("  FALLA "));
  Serial.print(que);
  Serial.print(F(": esperado "));
  imprimirBin(esperado);
  Serial.print(F("  leido "));
  imprimirBin(leido);
  Serial.print(F("  bits malos "));
  imprimirBin(esperado ^ leido);
  Serial.println();
  return false;
}

void titulo(const __FlashStringHelper* t) {
  Serial.println();
  Serial.println(t);
}

void cierre(uint16_t fallasAntes) {
  Serial.println(g_fallas == fallasAntes ? F("  OK") : F("  -> revisar"));
}

// Pin del Mega que corresponde a cada bit, para nombrar el cable sospechoso.
void listarPines(const __FlashStringHelper* puerto, uint8_t mascara, int base, int paso) {
  for (uint8_t b = 0; b < 8; b++) {
    if (mascara & (1 << b)) {
      Serial.print(F("    "));
      Serial.print(puerto);
      Serial.print(b);
      Serial.print(F(" = pin "));
      Serial.println(base + paso * b);
    }
  }
}

// ── Pruebas ─────────────────────────────────────────────────────────────────

// 1. En el AVR, PINx refleja el voltaje REAL del pin aunque sea salida. Si el
// Mega pone ALTO y lee BAJO (o al revés), algo de fuera lo está forzando: un
// temporal de la fase 4 al riel, el dip en ON, un puente a otra señal. El
// choque dura unos microsegundos por pin.
void pruebaPinesSalida() {
  titulo(F("1. Pines de salida del Mega (contencion con la placa)"));
  uint16_t antes = g_fallas;

  PORTA = 0xFF; delayMicroseconds(2); uint8_t altoA = PINA;
  PORTA = 0x00; delayMicroseconds(2); uint8_t bajoA = PINA;
  if (!comparar(F("bus D en ALTO"), 0xFF, altoA)) listarPines(F("PA"), ~altoA, 22, 1);
  if (!comparar(F("bus D en BAJO"), 0x00, bajoA)) listarPines(F("PA"), bajoA, 22, 1);

  uint8_t l = PORTL & MASCARA_NO_ALU;
  PORTL = l | 0x3F; delayMicroseconds(2); uint8_t altoL = PINL & 0x3F;
  PORTL = l;        delayMicroseconds(2); uint8_t bajoL = PINL & 0x3F;
  if (!comparar(F("S0-S3/M/Cn en ALTO"), 0x3F, altoL)) listarPines(F("PL"), ~altoL & 0x3F, 49, -1);
  if (!comparar(F("S0-S3/M/Cn en BAJO"), 0x00, bajoL)) listarPines(F("PL"), bajoL, 49, -1);

  const uint8_t sueltos[] = {PIN_CLEAR, PIN_MUX, PIN_CLOCK_B, PIN_CLOCK_A,
                             PIN_CLOCK_PC, PIN_CARGA_PC, PIN_CLOCK_SALIDA};
  for (uint8_t i = 0; i < sizeof(sueltos); i++) {
    uint8_t p = sueltos[i];
    digitalWrite(p, HIGH); delayMicroseconds(2); int alto = digitalRead(p);
    digitalWrite(p, LOW);  delayMicroseconds(2); int bajo = digitalRead(p);
    if (alto != HIGH || bajo != LOW) {
      g_fallas++;
      Serial.print(F("  FALLA pin "));
      Serial.print(p);
      Serial.println(alto != HIGH ? F(": algo lo jala a GND (pone ALTO, lee BAJO)")
                                  : F(": algo lo jala a +5 V (pone BAJO, lee ALTO)"));
    }
  }

  reposo();
  limpiar();   // los relojes sí pulsaron: deja todo en cero otra vez
  cierre(antes);
}

// 2. Una línea que nadie maneja lee distinto con y sin pull-up; una manejada
// por un 181 o un 161 lee igual (totem-pole contra ~35 kΩ).
void pruebaEntradasFlotantes() {
  titulo(F("2. Entradas flotantes (F en PORTC, PC en PORTK)"));
  uint16_t antes = g_fallas;

  configurarALU(1, S_CERO, 1);
  delayMicroseconds(MICROS_PROPAGACION);
  uint8_t fSin = PINC, pcSin = PINK;
  PORTC = 0xFF; PORTK = 0xFF;            // pull-ups encendidos
  delayMicroseconds(MICROS_PROPAGACION);
  uint8_t fCon = PINC, pcCon = PINK;
  PORTC = 0x00; PORTK = 0x00;            // como los deja el firmware

  if (!comparar(F("F sin/con pull-up"), fSin, fCon)) listarPines(F("PC"), fSin ^ fCon, 37, -1);
  if (!comparar(F("PC sin/con pull-up"), pcSin, pcCon)) {
    Serial.println(F("    (PK0..PK7 = A8..A15)"));
  }
  cierre(antes);
}

// 3. Funciones constantes del 181: F no depende de A ni de B, así que esto
// prueba solo el control de la ALU y los 8 cables de F, sin registros.
void pruebaLecturaF() {
  titulo(F("3. Lectura de F (M=1 S=0011 -> 0x00, M=1 S=1100 -> 0xFF)"));
  uint16_t antes = g_fallas;
  configurarALU(1, S_CERO, 1);
  uint8_t cero = leerF();
  configurarALU(1, S_UNOS, 1);
  uint8_t unos = leerF();
  if (!comparar(F("F=0"), 0x00, cero)) listarPines(F("PC"), cero, 37, -1);
  if (!comparar(F("F=FF"), 0xFF, unos)) listarPines(F("PC"), ~unos, 37, -1);
  cierre(antes);
}

// 4. CLEAR llega a los dos 273 y a los dos 161.
void pruebaClear() {
  titulo(F("4. CLEAR (pin 38): PC, A y B en cero"));
  uint16_t antes = g_fallas;
  cargarA(0xFF);
  cargarB(0xFF);
  cargarPC(0xFF);
  limpiar();
  comparar(F("PC"), 0x00, leerPC());
  comparar(F("A"), 0x00, leerA());
  comparar(F("B"), 0x00, leerB());
  cierre(antes);
}

// 5 y 6. Bus D hacia un registro, comprobando que el OTRO no se mueva: si se
// mueve, su reloj está unido al que se pulsó.
void pruebaBusARegistro(bool aEsDestino) {
  titulo(aEsDestino ? F("5. Bus D -> A (solo CLK A, pin 41); B debe quedar en 0")
                    : F("6. Bus D -> B (solo CLK B, pin 40); A debe quedar en 0"));
  uint16_t antes = g_fallas;
  uint8_t malosDestino = 0;
  bool otroSeMovio = false;

  limpiar();
  for (uint8_t i = 0; i < N_PATRONES; i++) {
    uint8_t v = PATRONES[i];
    if (aEsDestino) cargarA(v); else cargarB(v);
    // Se lee con el bus en el complemento: una entrada del 181 que tome el
    // bus en vez del registro sale como bit malo, en vez de esconderse.
    ponerBus(~v);
    uint8_t destino = aEsDestino ? leerA() : leerB();
    uint8_t otro = aEsDestino ? leerB() : leerA();
    malosDestino |= v ^ destino;
    if (otro != 0x00) otroSeMovio = true;
  }
  ponerBus(0x00);

  if (malosDestino) {
    g_fallas++;
    Serial.print(F("  FALLA bits que no llegan bien: "));
    imprimirBin(malosDestino);
    Serial.println(F("  (la prueba 10 dice si es el bus o el cable al 181)"));
  }
  if (otroSeMovio) {
    g_fallas++;
    Serial.println(aEsDestino ? F("  FALLA B no se lee 0 tras pulsar solo CLK A")
                              : F("  FALLA A no se lee 0 tras pulsar solo CLK B"));
    Serial.println(F("    (relojes unidos, o una entrada del 181 cableada a otra cosa: ver la prueba 10)"));
  }
  limpiar();
  cierre(antes);
}

// 7. El PC cuenta de uno en uno, incluido el paso 0x0F -> 0x10 (cascada RCO).
void pruebaPCCuenta() {
  titulo(F("7. PC cuenta (pin 42, /LOAD alto): 0x00 -> 0x14"));
  uint16_t antes = g_fallas;
  limpiar();
  comparar(F("PC tras CLEAR"), 0x00, leerPC());
  for (uint8_t esperado = 1; esperado <= 0x14; esperado++) {
    contarPC();
    if (!comparar(F("PC"), esperado, leerPC())) break;
  }
  cierre(antes);
}

// 8. El PC carga el bus D con /LOAD bajo (los saltos) y sigue contando desde ahí.
void pruebaPCCarga() {
  titulo(F("8. PC carga desde el bus D (/LOAD pin 43)"));
  uint16_t antes = g_fallas;
  uint8_t malos = 0, malosSiguiente = 0;
  for (uint8_t i = 0; i < N_PATRONES; i++) {
    uint8_t v = PATRONES[i];
    cargarPC(v);
    malos |= v ^ leerPC();
    contarPC();
    malosSiguiente |= (uint8_t)(v + 1) ^ leerPC();
  }
  ponerBus(0x00);
  if (malos) {
    g_fallas++;
    Serial.print(F("  FALLA bits que no cargan bien: "));
    imprimirBin(malos);
    Serial.println();
  }
  if (malosSiguiente && !malos) {
    g_fallas++;
    Serial.print(F("  FALLA carga bien pero luego no cuenta bien: "));
    imprimirBin(malosSiguiente);
    Serial.println();
  }
  limpiar();
  cierre(antes);
}

// 9. Lo que el programa de referencia necesita: SUB que da cero (si no, Z
// nunca es 1 y el JNZ gira para siempre) y el resultado de vuelta en A.
void pruebaALU() {
  titulo(F("9. ALU: control de las dos mitades, 0x40-0x40 = 0, y 5+3 de vuelta en A"));
  uint16_t antes = g_fallas;

  limpiar();

  // Control de las dos mitades SIN depender de A ni de B (que pueden estar
  // mal). M=0 S=0011 es "menos 1": cada 181 propaga sin generar, así que
  //   C̄n=1 (sin acarreo) -> F = 1111 1111
  //   C̄n=0 (con acarreo) -> F = 0000 0000, y el acarreo cruza de la BAJA a la ALTA
  // Una mitad que vea M=1 da 0000 en el primer caso (S=0011 lógico = 0). Si
  // el acarreo no cruza, la ALTA da 1111 en el segundo. Se repite 200 veces
  // para atrapar un falso contacto.
  uint8_t fallasM = 0, fallasC = 0, malosM = 0, malosC = 0;
  for (uint8_t i = 0; i < 200; i++) {
    configurarALU(0, S_CERO, 1);
    uint8_t sinAcarreo = leerF();
    configurarALU(0, S_CERO, 0);
    uint8_t conAcarreo = leerF();
    if (sinAcarreo != 0xFF) { fallasM++; malosM |= (uint8_t)~sinAcarreo; }
    if (conAcarreo != 0x00) { fallasC++; malosC |= conAcarreo; }
  }
  if (fallasM) {
    g_fallas++;
    Serial.print(F("  FALLA M (M=0 S=0011 Cn=1 debe dar 0xFF): "));
    Serial.print(fallasM);
    Serial.print(F(" de 200 mal; nibbles en 0 "));
    imprimirBin(malosM);
    Serial.println();
    if (malosM & 0xF0) Serial.println(F("    ALU ALTA no recibe M=0: puente morado #100 (BB3-a13 -> BB3-a29, pata 8)"));
    if (malosM & 0x0F) Serial.println(F("    ALU BAJA no recibe M=0: Mega pin 45 -> BB3-b13 (pata 8)"));
  }
  if (fallasC && !(malosM & 0xF0)) {
    g_fallas++;
    Serial.print(F("  FALLA acarreo (M=0 S=0011 Cn=0 debe dar 0x00): "));
    Serial.print(fallasC);
    Serial.print(F(" de 200 mal; bits en 1 "));
    imprimirBin(malosC);
    Serial.println();
    if (malosC & 0x0F) Serial.println(F("    ALU BAJA no recibe Cn: Mega pin 44 (pata 7 de la ALU BAJA)"));
    if (malosC & 0xF0) Serial.println(F("    el acarreo no cruza: puente morado #101 (BB3-j14 -> BB3-a28)"));
  }

  cargarA(0x40);
  cargarB(0x40);
  configurarALU(0, S_SUB, 0);
  comparar(F("SUB 0x40-0x40"), 0x00, leerF());
  if (!huboAcarreo()) {
    g_fallas++;
    Serial.println(F("  FALLA C~n+4 (pin 2) deberia estar en BAJO con A >= B"));
  }

  cargarA(0x05);
  cargarB(0x03);
  configurarALU(0, S_ADD, 1);
  comparar(F("F de 5+3"), 0x08, leerF());
  seleccionarMux(true);
  pulso(PIN_CLOCK_A);
  seleccionarMux(false);
  comparar(F("A tras escribir 5+3"), 0x08, leerA());

  // Para verlo en los LEDs: pasar A y enganchar el registro de salida.
  configurarALU(1, S_PASAR_A, 1);
  delayMicroseconds(MICROS_PROPAGACION);
  pulso(PIN_CLOCK_SALIDA);
  Serial.println(F("  (los LEDs deben mostrar 0000 1000)"));
  cierre(antes);
}

// 10. Mapa: de dónde toma realmente su valor cada entrada A0-A7 y B0-B7 de
// los 181 y cada P0-P7 de los 161. Se cargan A, B y el bus con valores
// independientes (pseudoaleatorios, siempre los mismos) muchas veces, y para
// cada entrada se busca la única señal que coincide en TODAS las lecturas.
// Con 40 lecturas, una coincidencia por casualidad es imposible en la práctica.

const uint8_t N_ESTADOS = 40;
uint8_t g_cargaA[N_ESTADOS], g_cargaB[N_ESTADOS], g_bus[N_ESTADOS];
uint8_t g_leidoA[N_ESTADOS], g_leidoB[N_ESTADOS], g_leidoPC[N_ESTADOS];

// Candidatas: 0-7 bit de REG A, 8-15 bit de REG B, 16-23 bit del bus D,
// 24 fijo en 0, 25 fijo en 1.
const uint8_t C_BUS = 16;
const uint8_t C_FIJO_0 = 24;
const uint8_t C_FIJO_1 = 25;
const uint8_t N_CANDIDATAS = 26;

// Patas del 74LS273 (Q y D), del 74LS181 (A y B) y del 74LS161 (P) por bit.
const uint8_t PATA_273_Q[] = {2, 5, 6, 9, 12, 15, 16, 19};
const uint8_t PATA_273_D[] = {3, 4, 7, 8, 13, 14, 17, 18};
const uint8_t PATA_181_A[] = {2, 23, 21, 19};
const uint8_t PATA_181_B[] = {1, 22, 20, 18};
const uint8_t PATA_161_P[] = {3, 4, 5, 6};

uint16_t g_azar;

uint8_t azar() {   // LFSR de 16 bits: la misma secuencia en cada corrida
  for (uint8_t i = 0; i < 8; i++) {
    uint16_t bit = (g_azar ^ (g_azar >> 2) ^ (g_azar >> 3) ^ (g_azar >> 5)) & 1;
    g_azar = (g_azar >> 1) | (bit << 15);
  }
  return g_azar & 0xFF;
}

uint8_t valorCandidata(uint8_t c, uint8_t s) {
  if (c < 8) return (g_cargaA[s] >> c) & 1;
  if (c < 16) return (g_cargaB[s] >> (c - 8)) & 1;
  if (c < 24) return (g_bus[s] >> (c - 16)) & 1;
  return c == C_FIJO_1 ? 1 : 0;
}

bool coincide(uint8_t c, const uint8_t* leido, uint8_t bit) {
  for (uint8_t s = 0; s < N_ESTADOS; s++) {
    if (((leido[s] >> bit) & 1) != valorCandidata(c, s)) return false;
  }
  return true;
}

void imprimirCandidata(uint8_t c) {
  if (c < 16) {
    uint8_t k = c % 8;
    Serial.print(c < 8 ? F("REG A Q") : F("REG B Q"));
    Serial.print(k);
    Serial.print(F(" (pata "));
    Serial.print(PATA_273_Q[k]);
    Serial.print(F(" del 273)"));
  } else if (c < C_FIJO_0) {
    uint8_t k = c - C_BUS;
    Serial.print(F("bus D"));
    Serial.print(k);
    Serial.print(F(" (Mega pin "));
    Serial.print(22 + k);
    Serial.print(F("; en REG B es la pata "));
    Serial.print(PATA_273_D[k]);
    Serial.print(F(" del 273)"));
  } else if (c == C_FIJO_0) {
    Serial.print(F("fijo en 0 (cable a GND o a algo que no cambia)"));
  } else {
    Serial.print(F("fijo en 1 (entrada al aire o unida a +5 V)"));
  }
}

// lado: 0 = entradas A del 181, 1 = entradas B del 181, 2 = P del PC.
uint8_t reportarEntradas(uint8_t lado, const uint8_t* leido) {
  uint8_t malas = 0;
  for (uint8_t bit = 0; bit < 8; bit++) {
    uint8_t esperada = (lado == 0) ? bit : (lado == 1) ? 8 + bit : C_BUS + bit;
    if (coincide(esperada, leido, bit)) continue;
    malas++;
    g_fallas++;

    Serial.print(F("  FALLA "));
    if (lado == 2) {
      Serial.print(bit < 4 ? F("PC BAJO") : F("PC ALTO"));
      Serial.print(F(" P"));
      Serial.print(bit % 4);
      Serial.print(F(" (pata "));
      Serial.print(PATA_161_P[bit % 4]);
    } else {
      Serial.print(bit < 4 ? F("ALU BAJA ") : F("ALU ALTA "));
      Serial.print(lado == 0 ? 'A' : 'B');
      Serial.print(bit % 4);
      Serial.print(F(" (pata "));
      Serial.print(lado == 0 ? PATA_181_A[bit % 4] : PATA_181_B[bit % 4]);
    }
    Serial.print(F(", bit "));
    Serial.print(bit);
    Serial.println(F(")"));

    Serial.print(F("      deberia seguir a: "));
    imprimirCandidata(esperada);
    Serial.println();
    Serial.print(F("      se comporta como: "));
    bool hallada = false;
    for (uint8_t c = (lado == 2 ? C_BUS : 0); c < N_CANDIDATAS; c++) {
      if (coincide(c, leido, bit)) {
        imprimirCandidata(c);
        hallada = true;
        break;
      }
    }
    if (!hallada) {
      Serial.print(F("ninguna senal fija: contacto flojo o dos salidas unidas"));
    }
    Serial.println();
  }
  return malas;
}

void pruebaMapa() {
  titulo(F("10. Mapa: de donde toma su valor cada entrada de los 181 y del PC"));
  uint16_t antes = g_fallas;

  g_azar = 0xACE1;
  for (uint8_t s = 0; s < N_ESTADOS; s++) {
    g_cargaA[s] = azar();
    g_cargaB[s] = azar();
    g_bus[s] = azar();
    cargarA(g_cargaA[s]);
    cargarB(g_cargaB[s]);
    ponerBus(g_bus[s]);
    g_leidoA[s] = leerA();
    g_leidoB[s] = leerB();
    cargarPC(g_bus[s]);
    g_leidoPC[s] = leerPC();
  }
  ponerBus(0x00);
  limpiar();

  reportarEntradas(0, g_leidoA);
  reportarEntradas(1, g_leidoB);
  reportarEntradas(2, g_leidoPC);
  cierre(antes);
}

void pruebaCompleta() {
  g_fallas = 0;
  Serial.println(F("=== Prueba de la fase 5 ==="));
  pruebaPinesSalida();
  pruebaEntradasFlotantes();
  pruebaLecturaF();
  pruebaClear();
  pruebaBusARegistro(true);
  pruebaBusARegistro(false);
  pruebaPCCuenta();
  pruebaPCCarga();
  pruebaALU();
  pruebaMapa();
  Serial.println();
  if (g_fallas == 0) {
    Serial.println(F("=== TODO OK: el cableado responde como espera el firmware ==="));
  } else {
    Serial.print(F("=== "));
    Serial.print(g_fallas);
    Serial.println(F(" falla(s). La prueba 10 dice que cable va a que pata: arregla esas ==="));
    Serial.println(F("=== primero; las fallas de 4 a 9 suelen ser consecuencia de ellas ==="));
  }
  reposo();
}

// ── Comandos manuales ───────────────────────────────────────────────────────

void mostrar(const __FlashStringHelper* nombre, uint8_t v) {
  Serial.print(nombre);
  Serial.print(F(" = "));
  imprimirBin(v);
  Serial.println();
}

void ayuda() {
  Serial.println(F("T = prueba completa   R = CLEAR y estado   C = contar PC   L = leer PC"));
  Serial.println(F("A = leer A   B = leer B   P = pines de salida   M = mapa de entradas   H = ayuda"));
}

void setup() {
  DDRA = 0xFF;                  // bus D
  DDRC = 0x00; PORTC = 0x00;    // F, sin pull-ups (330 ohm en serie)
  DDRK = 0x00; PORTK = 0x00;    // PC, sin pull-ups
  DDRL |= 0x3F;                 // control de la ALU
  pinMode(PIN_CLOCK_A, OUTPUT);
  pinMode(PIN_CLOCK_B, OUTPUT);
  pinMode(PIN_MUX, OUTPUT);
  pinMode(PIN_CLEAR, OUTPUT);
  pinMode(PIN_CLOCK_PC, OUTPUT);
  pinMode(PIN_CARGA_PC, OUTPUT);
  pinMode(PIN_CLOCK_SALIDA, OUTPUT);
  pinMode(PIN_CARRY, INPUT);
  reposo();
  limpiar();

  Serial.begin(115200);
  Serial.println(F("Prueba de la fase 5 (Mega <-> placa)"));
  ayuda();
}

void loop() {
  if (!Serial.available()) return;
  char c = toupper(Serial.read());
  switch (c) {
    case 'T': pruebaCompleta(); break;
    case 'R':
      limpiar();
      mostrar(F("PC"), leerPC());
      mostrar(F("A "), leerA());
      mostrar(F("B "), leerB());
      break;
    case 'C': contarPC(); mostrar(F("PC"), leerPC()); break;
    case 'L': mostrar(F("PC"), leerPC()); break;
    case 'A': mostrar(F("A"), leerA()); break;
    case 'B': mostrar(F("B"), leerB()); break;
    case 'P': g_fallas = 0; pruebaPinesSalida(); break;
    case 'M': g_fallas = 0; pruebaMapa(); break;
    case 'H': ayuda(); break;
  }
}
