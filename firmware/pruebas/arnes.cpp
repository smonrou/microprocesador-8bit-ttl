// ---------------------------------------------------------------------------
// arnes.cpp — ejecuta el núcleo del firmware en la PC y vuelca su estado.
//
//   arnes <imagen.bin> [--microciclos] [--limite N]
//
// Carga una imagen de 256 bytes, la ejecuta contra el HAL falso y escribe una
// línea ASCII por instrucción completada. tests/test_firmware_nucleo.py
// recorre sim/cpu.py en paralelo y compara instrucción por instrucción, así
// que cualquier divergencia se localiza exactamente donde empieza.
//
// Solo pruebas nativas: no forma parte del sketch.
// ---------------------------------------------------------------------------

#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "../unidad_control/formato.h"
#include "../unidad_control/hal.h"
#include "../unidad_control/nucleo.h"
#include "hal_falso.h"

namespace {

bool cargarImagen(const char* ruta, Nucleo& nucleo) {
  std::FILE* archivo = std::fopen(ruta, "rb");
  if (archivo == 0) {
    std::fprintf(stderr, "arnes: no se pudo abrir '%s'\n", ruta);
    return false;
  }

  unsigned char bytes[MEMORIA_TAM];
  size_t leidos = std::fread(bytes, 1, MEMORIA_TAM, archivo);
  std::fclose(archivo);

  if (leidos != MEMORIA_TAM) {
    std::fprintf(stderr, "arnes: '%s' tiene %u bytes, se esperaban %d\n",
                 ruta, static_cast<unsigned>(leidos), MEMORIA_TAM);
    return false;
  }

  for (uint16_t i = 0; i < MEMORIA_TAM; i++) {
    nucleo.escribirMemoria(static_cast<uint8_t>(i), bytes[i]);
  }
  return true;
}

void volcarInstruccion(Nucleo& nucleo) {
  const Traza& t = nucleo.traza();
  std::printf("INSTR n=%u pc_antes=0x%02X ir=0x%02X op=%s "
              "a=0x%02X b=0x%02X z=%u c=%u pc=0x%02X\n",
              static_cast<unsigned>(t.ciclo),
              static_cast<unsigned>(t.pcAntes),
              static_cast<unsigned>(t.ir),
              t.nemonico,
              static_cast<unsigned>(nucleo.registroA()),
              static_cast<unsigned>(nucleo.registroB()),
              static_cast<unsigned>(nucleo.z()),
              static_cast<unsigned>(nucleo.c()),
              static_cast<unsigned>(nucleo.pc()));

  if (nucleo.huboSalida()) {
    std::printf("OUT valor=%u\n", static_cast<unsigned>(nucleo.ultimaSalida()));
    nucleo.limpiarSalida();
  }
}

}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) {
    std::fprintf(stderr, "uso: arnes <imagen.bin> [--microciclos] [--limite N]\n");
    return 1;
  }

  bool volcarMicrociclos = false;
  bool volcarBloques = false;
  uint16_t limite = 10000;

  for (int i = 2; i < argc; i++) {
    if (std::strcmp(argv[i], "--microciclos") == 0) {
      volcarMicrociclos = true;
    } else if (std::strcmp(argv[i], "--bloques") == 0) {
      volcarBloques = true;
    } else if (std::strcmp(argv[i], "--limite") == 0 && i + 1 < argc) {
      limite = static_cast<uint16_t>(std::atoi(argv[++i]));
    }
  }

  hal::iniciar();

  Nucleo nucleo;
  if (!cargarImagen(argv[1], nucleo)) {
    return 1;
  }

  uint32_t microciclos = 0;
  bool limiteAlcanzado = false;

  while (!nucleo.detenido()) {
    PasoResultado resultado = nucleo.paso();
    if (!resultado.valido) {
      break;
    }
    microciclos++;

    if (volcarMicrociclos) {
      std::printf("PASO %s\n", nombrePaso(resultado.paso));
    }

    if (resultado.instruccionCompleta) {
      if (volcarBloques) {
        // Delimitadores para que la prueba recorte cada bloque sin ambigüedad.
        char buffer[FORMATO_BUFFER];
        formato::bloqueCiclo(nucleo.traza(), buffer, sizeof(buffer));
        std::printf("<<<BLOQUE\n%s\n>>>BLOQUE\n", buffer);

        char linea[160];
        formato::lineaClaveValor(nucleo.traza(), nucleo.detenido(),
                                 linea, sizeof(linea));
        std::printf("%s\n", linea);
      }
      volcarInstruccion(nucleo);
      if (nucleo.instrucciones() > limite) {
        limiteAlcanzado = true;
        break;
      }
    }
  }

  // Volcado final de memoria, para comparar la imagen completa.
  std::printf("MEM");
  for (uint16_t i = 0; i < MEMORIA_TAM; i++) {
    std::printf(" %02X", nucleo.leerMemoria(static_cast<uint8_t>(i)));
  }
  std::printf("\n");

  // Flancos que recibió el contador de programa emulado (2× 74LS161):
  // cuántas cuentas y cuántas cargas pidió el núcleo.
  const hal_falso::Estado& placa = hal_falso::estado();
  std::printf("FIN detenido=%u instrucciones=%u microciclos=%u limite=%u "
              "pulsos_pc=%u cargas_pc=%u\n",
              static_cast<unsigned>(nucleo.detenido() ? 1 : 0),
              static_cast<unsigned>(nucleo.instrucciones()),
              static_cast<unsigned>(microciclos),
              static_cast<unsigned>(limiteAlcanzado ? 1 : 0),
              static_cast<unsigned>(placa.pulsosPC),
              static_cast<unsigned>(placa.cargasPC));
  return 0;
}
