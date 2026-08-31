// ---------------------------------------------------------------------------
// main_stub.cpp — main() para el enlazado de comprobación del sketch.
//
// El IDE de Arduino genera su propio main() que llama a setup() y loop(). Al
// compilar el sketch en la PC solo para verificar que enlaza, hace falta uno.
// No ejecuta nada: llamar a loop() sin hardware no tendría sentido.
// ---------------------------------------------------------------------------

void setup();
void loop();

int main() {
  // Referenciadas para que el enlazador exija que existan y tengan la firma
  // correcta, sin llegar a ejecutarlas.
  void (*inicio)() = setup;
  void (*bucle)() = loop;
  (void)inicio;
  (void)bucle;
  return 0;
}
