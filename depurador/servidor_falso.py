"""Arduino de mentira: servidor TCP que habla el protocolo serial del firmware.

El Arduino Mega todavía no se ha comprado. Este servidor monta el mismo
protocolo de ``firmware/unidad_control/consola.cpp`` sobre ``sim.cpu.CPU``,
así el depurador se puede probar de punta a punta HOY. El día que llegue la
placa solo cambia el transporte (TCP -> puerto serie), no la interfaz.

Reglas que se respetan al pie de la letra:

- Cada texto ``OK ...``/``ERR ...`` es una transcripción literal de consola.cpp.
- El bloque humano de A.9 lo genera ``sim.trace.format_cycle``, que
  ``tests/test_firmware_formato.py`` ya demuestra byte-idéntico al del
  firmware. No se reimplementa aquí.
- ``Serial.println`` de Arduino termina en ``\\r\\n``, y el bloque de A.9 viaja
  en UN solo println con ``\\n`` internos: quien lee esto por líneas tiene que
  reensamblarlo (``protocolo.EnsambladorDeBloques``).
- ``CPU.step()`` LANZA si la CPU está detenida, así que se comprueba
  ``cpu.halted`` antes, igual que ``comandoRun``/``comandoStep`` comprueban
  ``detenido()``.
- ``CPU.reset()`` NO borra la memoria (RESET conserva el programa);
  ``BORRAR`` sí (``memoria.reset()`` + ``cpu.reset()``).
- El rango 0-255 se valida a mano: ``Memory.write`` enmascara en silencio con
  ``& 0xFF`` y eso taparía el ``ERR valor fuera de rango`` del firmware.

Solo biblioteca estándar: ``socket`` + ``threading``. Sin pyserial, sin Tkinter.
"""

import socket
import threading
import time
from typing import List, Optional

from sim.cpu import CPU
from sim.exceptions import CpuHaltedError
from sim.memory import Memory
from sim.trace import format_cycle

from . import protocolo

# Arduino termina cada println con CR+LF (Print::println).
FIN_DE_LINEA = "\r\n"

# consola.cpp: const uint8_t LINEA_MAX = 96;
LINEA_MAX = 96

# consola.cpp: uint16_t g_retardo = 200;
RETARDO_POR_DEFECTO = 200

# comandoRun: uint16_t tope = 10000;
TOPE_INSTRUCCIONES = 10000

TEXTO_AYUDA = (
    "LOAD <dir> <byte>     escribe un byte",
    "LOADB <dir> <hex...>  carga un bloque",
    "RUN                   ejecuta hasta HLT",
    "STEP                  avanza un microciclo",
    "RESET                 PC=0, banderas a 0 (conserva memoria)",
    "BORRAR                borra toda la memoria",
    "DUMP <ini> [fin]      vuelca memoria",
    "STATE                 estado actual",
    "VEL <ms>              retardo entre instrucciones en RUN",
)

BANNER = (
    "",
    "Microprocesador de 8 bits - unidad de control lista",
    "ALU: 2x SN74LS181  Registros: 2x 74LS273  Mux: 2x 74LS157",
    "Escribe HELP para ver los comandos.",
)


class ConsolaFalsa:
    """El intérprete de comandos, sin sockets: entra texto, sale texto.

    Separarlo del servidor permite probar cada comando sin abrir un puerto, y
    es la parte que de verdad tiene que coincidir con consola.cpp.
    """

    def __init__(self, retardo: int = RETARDO_POR_DEFECTO,
                 dormir=time.sleep, emisor=None) -> None:
        self.cpu = CPU(Memory())
        self.retardo = retardo
        self._dormir = dormir            # inyectable: los tests no esperan de verdad
        # Con `emisor` la salida se manda EN CUANTO se produce, como el
        # Serial.println del firmware: durante un RUN con VEL>0 el depurador ve
        # aparecer las instrucciones una a una en vez de todas al final.
        # Sin él se acumula y la devuelve `recibir()`, que es lo cómodo para
        # probar comando por comando.
        self._emisor = emisor
        self._salida: List[str] = []
        self._buffer = ""                # espeja g_linea/g_largo de consola.cpp

    # ── Salida (espeja Serial.print / Serial.println) ──────────────────────

    def _println(self, texto: str = "") -> None:
        if self._emisor is not None:
            self._emisor(texto + FIN_DE_LINEA)
        else:
            self._salida.append(texto + FIN_DE_LINEA)

    def _recoger(self) -> str:
        texto = "".join(self._salida)
        self._salida = []
        return texto

    # ── Entrada (espeja consola::atender) ──────────────────────────────────

    def banner(self) -> str:
        """Lo que imprime ``consola::iniciar`` al arrancar."""
        for linea in BANNER:
            self._println(linea)
        self._imprimir_estado()
        return self._recoger()

    def recibir(self, texto: str) -> str:
        """Consume caracteres crudos y devuelve todo lo que el firmware
        imprimiría. Se emula el buffer de 96 bytes carácter a carácter porque
        su desbordamiento tiene salida propia (``ERR linea demasiado larga``).
        """
        for caracter in texto:
            if caracter == "\r":
                continue
            if caracter == "\n":
                if self._buffer:
                    self._ejecutar_linea(self._buffer)
                self._buffer = ""
                continue
            if len(self._buffer) < LINEA_MAX - 1:
                self._buffer += caracter
            else:
                # Línea demasiado larga: se descarta para no ejecutar un
                # comando truncado a medias.
                self._buffer = ""
                self._println("ERR linea demasiado larga")
        return self._recoger()

    # ── Estado ─────────────────────────────────────────────────────────────

    def _imprimir_estado(self) -> None:
        """Espeja ``imprimirEstado``: la línea legible y la ``#pc=...``."""
        cpu = self.cpu
        self._println(protocolo.linea_estado_humana(
            cpu.pc, cpu.ir, cpu.a, cpu.b, cpu.z, cpu.c, cpu.halted))
        self._println(protocolo.linea_estado(
            cpu.pc, cpu.ir, cpu.a, cpu.b, cpu.z, cpu.c, cpu.halted))

    def _imprimir_bloque_y_claves(self, traza) -> None:
        """Espeja ``imprimirBloqueYClaves``: el bloque de A.9 en UN println
        (con saltos internos) y detrás la línea ``#clave=valor``."""
        self._println(format_cycle(traza))
        self._println(protocolo.linea_clave_valor(traza, self.cpu.halted))

    # ── Despacho (espeja ejecutarLinea) ────────────────────────────────────

    def _ejecutar_linea(self, linea: str) -> None:
        partes = linea.split()          # strtok(linea, " \t")
        if not partes:
            return                       # orden == 0: el firmware no dice nada
        orden = partes[0].upper()
        argumentos = partes[1:]

        if orden == "LOAD":
            self._comando_load(argumentos)
        elif orden == "LOADB":
            self._comando_loadb(argumentos)
        elif orden == "RUN":
            self._comando_run()
        elif orden == "STEP":
            self._comando_step()
        elif orden == "DUMP":
            self._comando_dump(argumentos)
        elif orden == "VEL":
            self._comando_vel(argumentos)
        elif orden == "STATE":
            self._imprimir_estado()
        elif orden == "HELP":
            self._comando_help()
        elif orden == "RESET":
            self.cpu.reset()             # conserva la memoria, como reiniciar()
            self._println("OK reset")
            self._imprimir_estado()
        elif orden == "BORRAR":
            self.cpu.memory.reset()      # borrarTodo(): memoria a 0x00 + reinicio
            self.cpu.reset()
            self._println("OK memoria borrada")
        else:
            self._println(f"ERR comando desconocido: {orden}")

    # ── Comandos ───────────────────────────────────────────────────────────

    def _comando_load(self, argumentos: List[str]) -> None:
        texto_dir = argumentos[0] if len(argumentos) > 0 else None
        texto_val = argumentos[1] if len(argumentos) > 1 else None
        direccion = protocolo.parsear_numero(texto_dir)
        valor = protocolo.parsear_numero(texto_val)

        if direccion is None or valor is None:
            self._println("ERR LOAD requiere <dir> <byte>")
            return
        if not protocolo.en_rango(direccion) or not protocolo.en_rango(valor):
            self._println("ERR valor fuera de rango (0-255)")
            return

        self.cpu.memory.write(direccion, valor)
        # La confirmación es lo que impide perder comandos en silencio al pegar
        # muchas líneas seguidas.
        self._println(f"OK dir=0x{direccion:02X} val=0x{valor:02X}")

    def _comando_loadb(self, argumentos: List[str]) -> None:
        texto_dir = argumentos[0] if argumentos else None
        direccion = protocolo.parsear_numero(texto_dir)
        if direccion is None or not protocolo.en_rango(direccion):
            self._println("ERR LOADB requiere <dir> <hex> [hex...]")
            return

        escritos = 0
        for token in argumentos[1:]:
            valor = protocolo.parsear_numero(token)
            if valor is None or not protocolo.en_rango(valor):
                self._println(f"ERR byte invalido: {token}")
                return
            if direccion + escritos > 255:
                self._println("ERR el bloque excede la memoria")
                return
            self.cpu.memory.write(direccion + escritos, valor)
            escritos += 1

        if escritos == 0:
            self._println("ERR LOADB sin bytes")
            return

        self._println(f"OK dir=0x{direccion:02X} n={escritos}")

    def _comando_run(self) -> None:
        if self.cpu.halted:
            self._println("ERR la CPU esta detenida; usa RESET")
            return

        self._println("--- RUN ---")

        while not self.cpu.halted:
            try:
                resultado = self.cpu.step()
            except CpuHaltedError:
                break                     # espeja `if (!paso.valido) break;`
            if resultado.completed:
                self._imprimir_bloque_y_claves(resultado.trace)
                if self.cpu.instruction_count > TOPE_INSTRUCCIONES:
                    self._println(
                        "ERR limite de instrucciones; posible bucle infinito")
                    return
                if self.retardo > 0:
                    self._dormir(self.retardo / 1000.0)

        self._println("--- HLT ---")
        self._imprimir_estado()

    def _comando_step(self) -> None:
        if self.cpu.halted:
            self._println("ERR la CPU esta detenida; usa RESET")
            return

        try:
            resultado = self.cpu.step()
        except CpuHaltedError:
            # Espeja `if (!paso.valido)`. En el firmware es inalcanzable (arriba
            # ya se comprobó detenido()) y aquí también, pero se transcribe:
            # si algún día CPU.step() cambia, el protocolo no se inventa nada.
            self._println("ERR no se pudo avanzar")
            return

        self._println(f"paso: {resultado.label}")

        # El bloque de A.9 se imprime cuando la instrucción termina: "Ciclo N"
        # numera instrucciones completadas, no microciclos.
        if resultado.completed:
            self._imprimir_bloque_y_claves(resultado.trace)
        else:
            self._println(f"#paso={resultado.label}")

    def _comando_dump(self, argumentos: List[str]) -> None:
        texto_ini = argumentos[0] if len(argumentos) > 0 else None
        texto_fin = argumentos[1] if len(argumentos) > 1 else None
        inicio, fin = 0, 255

        if texto_ini is not None:
            valor = protocolo.parsear_numero(texto_ini)
            if valor is None or not protocolo.en_rango(valor):
                self._println("ERR DUMP requiere <ini> [fin]")
                return
            inicio = valor
        if texto_fin is not None:
            valor = protocolo.parsear_numero(texto_fin)
            if valor is None or not protocolo.en_rango(valor):
                self._println("ERR DUMP requiere <ini> [fin]")
                return
            fin = valor
        if fin < inicio:
            self._println("ERR el final va antes del inicio")
            return

        for direccion in range(inicio, fin + 1, 16):
            fila = f"0x{direccion:02X}: "
            for i in range(direccion, min(direccion + 16, fin + 1)):
                # Arduino imprime un espacio DETRÁS de cada byte: la fila queda
                # con un espacio final. Se respeta.
                fila += f"{self.cpu.memory.read(i):02X} "
            self._println(fila)

    def _comando_vel(self, argumentos: List[str]) -> None:
        texto = argumentos[0] if argumentos else None
        milisegundos = protocolo.parsear_numero(texto)
        if milisegundos is None or milisegundos < 0 or milisegundos > 5000:
            self._println("ERR VEL requiere <ms> entre 0 y 5000")
            return
        self.retardo = milisegundos
        self._println(f"OK vel={self.retardo}")

    def _comando_help(self) -> None:
        for linea in TEXTO_AYUDA:
            self._println(linea)


class ServidorFalso:
    """Servidor TCP mono-cliente que expone una ``ConsolaFalsa``.

    Mono-cliente a propósito: un Arduino tiene UN puerto serie. Mientras haya
    un cliente conectado, otro que llegue espera en la cola de ``listen``.

    ``RUN`` bloquea el hilo del cliente mientras duerme entre instrucciones,
    exactamente como el firmware bloquea en ``esperarRefrescando``.
    """

    def __init__(self, puerto: int = 0, direccion: str = "127.0.0.1",
                 retardo: int = RETARDO_POR_DEFECTO) -> None:
        self.direccion = direccion
        self.retardo = retardo
        self.consola: Optional[ConsolaFalsa] = None

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((direccion, puerto))
        self._socket.listen(1)
        self.puerto = self._socket.getsockname()[1]

        self._hilo: Optional[threading.Thread] = None
        self._corriendo = False
        self._conexion: Optional[socket.socket] = None

    # ── Ciclo de vida ──────────────────────────────────────────────────────

    def iniciar(self) -> "ServidorFalso":
        """Arranca el hilo aceptador. Devuelve self para encadenar."""
        if self._corriendo:
            return self
        self._corriendo = True
        self._hilo = threading.Thread(target=self._aceptar,
                                      name="servidor-falso", daemon=True)
        self._hilo.start()
        return self

    def detener(self) -> None:
        self._corriendo = False
        try:
            self._socket.close()
        except OSError:
            pass
        # También la conexión viva: si no, el hilo se queda bloqueado en recv()
        # y el cliente nunca se entera de que la "placa" se apagó.
        conexion, self._conexion = self._conexion, None
        if conexion is not None:
            try:
                conexion.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                conexion.close()
            except OSError:
                pass
        if self._hilo is not None and self._hilo is not threading.current_thread():
            self._hilo.join(timeout=2.0)
            self._hilo = None

    def __enter__(self) -> "ServidorFalso":
        return self.iniciar()

    def __exit__(self, *_excepcion) -> None:
        self.detener()

    # ── Atención del cliente ───────────────────────────────────────────────

    def _aceptar(self) -> None:
        while self._corriendo:
            try:
                conexion, _ = self._socket.accept()
            except OSError:
                return                    # el socket se cerró: fin del servidor
            self._conexion = conexion
            try:
                self._atender(conexion)
            finally:
                self._conexion = None
                try:
                    conexion.close()
                except OSError:
                    pass

    def _atender(self, conexion: socket.socket) -> None:
        # Cada cliente arranca una consola nueva: conectarse equivale a
        # resetear la placa, que es lo que hace abrir el puerto serie de un
        # Arduino de verdad (DTR reinicia el micro).
        vivo = [True]

        def emitir(texto: str) -> None:
            # Se escribe línea a línea, como Serial.println: durante un RUN
            # lento el cliente ve el avance, no un volcado al final.
            if vivo[0] and not self._enviar(conexion, texto):
                vivo[0] = False

        consola = ConsolaFalsa(retardo=self.retardo, emisor=emitir)
        self.consola = consola

        consola.banner()

        pendiente = b""
        while self._corriendo and vivo[0]:
            try:
                datos = conexion.recv(4096)
            except OSError:
                return
            if not datos:
                return                    # el cliente cerró

            pendiente += datos
            try:
                texto = pendiente.decode("utf-8")
                pendiente = b""
            except UnicodeDecodeError:
                continue                  # llegó un carácter partido; esperar el resto

            consola.recibir(texto)

    @staticmethod
    def _enviar(conexion: socket.socket, texto: str) -> bool:
        try:
            conexion.sendall(texto.encode("utf-8"))
            return True
        except OSError:
            return False
