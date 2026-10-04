// Prueba de la fase 4 (mux y PC) con relojes limpios del Mega.
//
// El reloj manual con un cable rebota: en el lazo del acumulador (SEL en +)
// un segundo flanco carga F a medio calcular, y en el PC cuenta de más. Este
// sketch da un solo flanco de subida por comando y lee el PC por PORTK.
//
// Conexiones (GND del Mega al riel − PRIMERO; el pin 5V no se conecta):
//   pin 41 → REG A CLK        (BB2-h29)
//   pin 7  → REG SALIDA CLK   (BB4-h19)
//   pin 42 → PC BAJO CLK      (BB1-c33)
//   A8..A15 ← PC0..PC7        (BB1-j34..j37, BB1-j46..j49)
//
// Comandos (mayúscula o minúscula) en el monitor serial a 115200:
//   A = pulso CLK A      S = pulso CLK S      P = CLK A y luego CLK S
//   C = pulso CLK PC y muestra el PC          L = leer el PC

const int CLK_A = 41;
const int CLK_S = 7;
const int CLK_PC = 42;

void pulso(int pin) {
  digitalWrite(pin, HIGH);   // flanco de subida: el 273 carga y el 161 cuenta aquí
  delayMicroseconds(10);
  digitalWrite(pin, LOW);
}

void mostrarPC() {
  byte pc = PINK;            // A8..A15 = PK0..PK7 = PC0..PC7
  Serial.print("PC = ");
  for (int b = 7; b >= 0; b--) {
    Serial.print((pc >> b) & 1);
    if (b == 4) Serial.print(' ');
  }
  Serial.print("  (0x");
  if (pc < 0x10) Serial.print('0');
  Serial.print(pc, HEX);
  Serial.print(", ");
  Serial.print(pc);
  Serial.println(")");
}

void setup() {
  pinMode(CLK_A, OUTPUT);  digitalWrite(CLK_A, LOW);
  pinMode(CLK_S, OUTPUT);  digitalWrite(CLK_S, LOW);
  pinMode(CLK_PC, OUTPUT); digitalWrite(CLK_PC, LOW);
  DDRK = 0x00;               // PORTK como entrada
  PORTK = 0x00;              // sin pull-ups: el 161 maneja las líneas
  Serial.begin(115200);
  Serial.println("A = CLK A, S = CLK S, P = CLK A y luego CLK S, C = CLK PC, L = leer PC");
}

void loop() {
  if (!Serial.available()) return;
  char c = toupper(Serial.read());
  switch (c) {
    case 'A': pulso(CLK_A); Serial.println("A"); break;
    case 'S': pulso(CLK_S); Serial.println("S"); break;
    case 'P': pulso(CLK_A); delayMicroseconds(10); pulso(CLK_S); Serial.println("P"); break;
    case 'C': pulso(CLK_PC); Serial.print("C  "); mostrarPC(); break;
    case 'L': mostrarPC(); break;
  }
}
