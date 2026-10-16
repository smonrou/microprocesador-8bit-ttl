"""Transporte: el mismo depurador contra el servidor falso o contra el Arduino.

Dos implementaciones con la misma interfaz:

- ``TransporteSocket``  TCP contra ``servidor_falso.ServidorFalso``. Solo
  biblioteca estándar.
- ``TransporteSerial``  puerto serie real, con **pyserial importado de forma
  perezosa** (dentro del método, no arriba del archivo). Así todo el resto del
  depurador — GUI incluida — arranca sin instalar absolutamente nada.

CONCURRENCIA — la regla que no se puede romper:

    Cada transporte corre UN hilo lector que empuja líneas a una
    ``queue.Queue``. Ese hilo NUNCA toca un widget de Tkinter. Tkinter no es
    seguro entre hilos: tocar un widget desde el lector produce cuelgues y
    corrupciones que aparecen semanas después y no se reproducen.
    La GUI vacía la cola desde el hilo principal con ``root.after(50, ...)``,
    que es el único lugar donde se pintan widgets.

Lo que llega a la cola son ``str`` ya sin ``\\r\\n``. Un ``None`` en la cola es
el centinela de "se cortó la conexión": es lo último que se recibe.
"""

import abc
import queue
import socket
import threading
from typing import List, Optional

BAUDIOS_POR_DEFECTO = 115200      # unidad_control.ino: Serial.begin(115200)
FIN_DE_LINEA = "\n"               # lo que el firmware espera para ejecutar
CENTINELA_DESCONEXION = None


class Transporte(abc.ABC):
    """Canal de líneas hacia y desde la unidad de control.

    ``lineas`` es la cola que llena el hilo lector; la GUI la drena.
    """

    def __init__(self) -> None:
        self.lineas: "queue.Queue" = queue.Queue()
        self._hilo: Optional[threading.Thread] = None
        self._corriendo = False

    # ── A implementar por cada transporte ──────────────────────────────────

    @abc.abstractmethod
    def _conectar(self) -> None:
        """Abre el canal. Lanza si no se puede."""

    @abc.abstractmethod
    def _leer_bytes(self) -> bytes:
        """Bloquea hasta que haya datos. Devuelve b"" cuando el canal se cierra."""

    @abc.abstractmethod
    def _escribir_bytes(self, datos: bytes) -> None:
        """Manda datos por el canal."""

    @abc.abstractmethod
    def _cerrar_canal(self) -> None:
        """Cierra el canal (idempotente)."""

    @abc.abstractmethod
    def descripcion(self) -> str:
        """Texto corto para la barra de conexión de la GUI."""

    # ── Ciclo de vida ──────────────────────────────────────────────────────

    @property
    def conectado(self) -> bool:
        return self._corriendo

    def abrir(self) -> "Transporte":
        if self._corriendo:
            return self
        self._conectar()
        self._corriendo = True
        self._hilo = threading.Thread(target=self._bucle_lector,
                                      name="lector-transporte", daemon=True)
        self._hilo.start()
        return self

    def cerrar(self) -> None:
        self._corriendo = False
        self._cerrar_canal()
        if self._hilo is not None and self._hilo is not threading.current_thread():
            self._hilo.join(timeout=2.0)
        self._hilo = None

    def __enter__(self) -> "Transporte":
        return self.abrir()

    def __exit__(self, *_excepcion) -> None:
        self.cerrar()

    # ── Envío ──────────────────────────────────────────────────────────────

    def enviar_linea(self, texto: str) -> None:
        """Manda un comando. El ``\\n`` final es lo que hace que se ejecute
        (``consola::atender`` ejecuta al ver el salto de línea)."""
        if not self._corriendo:
            raise RuntimeError("el transporte no está abierto")
        self._escribir_bytes((texto + FIN_DE_LINEA).encode("utf-8"))

    # ── Recepción ──────────────────────────────────────────────────────────

    def drenar(self, maximo: int = 500) -> List[Optional[str]]:
        """Saca de la cola lo que haya, sin bloquear.

        Pensado para llamarse desde ``root.after``: se limita el lote para que
        una ráfaga larga (un RUN entero) no congele la ventana en un solo turno.
        """
        recibidas: List[Optional[str]] = []
        for _ in range(maximo):
            try:
                recibidas.append(self.lineas.get_nowait())
            except queue.Empty:
                break
        return recibidas

    def _bucle_lector(self) -> None:
        """HILO SECUNDARIO. Solo toca la cola: ni un widget, ni estado de la GUI."""
        pendiente = b""
        try:
            while self._corriendo:
                try:
                    datos = self._leer_bytes()
                except OSError:
                    break
                if not datos:
                    break

                pendiente += datos
                while b"\n" in pendiente:
                    cruda, _, pendiente = pendiente.partition(b"\n")
                    self.lineas.put(cruda.decode("utf-8", errors="replace")
                                    .rstrip("\r"))
        finally:
            # Lo que quedó sin '\n' se entrega igual: el último renglón de un
            # bloque podría estar esperando ahí.
            if pendiente:
                self.lineas.put(pendiente.decode("utf-8", errors="replace")
                                .rstrip("\r"))
            self._corriendo = False
            self.lineas.put(CENTINELA_DESCONEXION)


class TransporteSocket(Transporte):
    """TCP contra el servidor falso. Sin dependencias de terceros."""

    def __init__(self, host: str = "127.0.0.1", puerto: int = 5555,
                 espera: float = 5.0) -> None:
        super().__init__()
        self.host = host
        self.puerto = puerto
        self.espera = espera
        self._socket: Optional[socket.socket] = None

    def _conectar(self) -> None:
        self._socket = socket.create_connection((self.host, self.puerto),
                                                timeout=self.espera)
        self._socket.settimeout(None)     # el lector bloquea a gusto

    def _leer_bytes(self) -> bytes:
        if self._socket is None:
            return b""
        return self._socket.recv(4096)

    def _escribir_bytes(self, datos: bytes) -> None:
        if self._socket is None:
            raise RuntimeError("el socket no está abierto")
        self._socket.sendall(datos)

    def _cerrar_canal(self) -> None:
        if self._socket is None:
            return
        try:
            self._socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self._socket.close()
        except OSError:
            pass
        self._socket = None

    def descripcion(self) -> str:
        return f"TCP {self.host}:{self.puerto}"


class TransporteSerial(Transporte):
    """Puerto serie real (Arduino Mega).

    ``import serial`` vive DENTRO de ``_conectar``: mientras nadie intente
    conectarse a hardware de verdad, el depurador no necesita pyserial.
    """

    def __init__(self, puerto: str, baudios: int = BAUDIOS_POR_DEFECTO,
                 espera: float = 0.2) -> None:
        super().__init__()
        self.puerto = puerto
        self.baudios = baudios
        self.espera = espera
        self._serie = None

    def _conectar(self) -> None:
        try:
            import serial                  # import perezoso: solo aquí
        except ImportError as error:       # pragma: no cover - depende del entorno
            raise RuntimeError(
                "hace falta pyserial para hablar con el Arduino real: "
                "pip install -r requirements.txt"
            ) from error

        # timeout corto: read() vuelve con b"" cada `espera` segundos, que es
        # lo que permite que cerrar() termine el hilo sin matarlo a la fuerza.
        self._serie = serial.Serial(self.puerto, self.baudios,
                                    timeout=self.espera)

    def _leer_bytes(self) -> bytes:
        # OJO: en el bucle lector, b"" significa "el canal se cerró". Un
        # read() con timeout devuelve b"" también cuando simplemente no llegó
        # nada, así que aquí se reintenta hasta tener datos o hasta que
        # cerrar() baje `_corriendo`. Ese timeout corto es justamente lo que
        # deja terminar el hilo sin matarlo a la fuerza.
        while self._corriendo and self._serie is not None:
            try:
                esperando = self._serie.in_waiting
            except Exception:              # pragma: no cover - puerto arrancado
                return b""
            datos = self._serie.read(esperando if esperando else 1)
            if datos:
                return datos
        return b""

    def _escribir_bytes(self, datos: bytes) -> None:
        if self._serie is None:
            raise RuntimeError("el puerto serie no está abierto")
        self._serie.write(datos)
        self._serie.flush()

    def _cerrar_canal(self) -> None:
        if self._serie is None:
            return
        try:
            self._serie.close()
        except Exception:                  # pragma: no cover - depende de pyserial
            pass
        self._serie = None

    def descripcion(self) -> str:
        return f"Serie {self.puerto} @ {self.baudios}"


def listar_puertos_serie() -> List[str]:
    """Los puertos serie disponibles, o ``[]`` si pyserial no está instalado.

    Devolver la lista vacía en vez de reventar es deliberado: el flujo con el
    servidor falso no necesita pyserial y la GUI tiene que arrancar igual.
    """
    try:
        from serial.tools import list_ports     # import perezoso
    except ImportError:
        return []
    try:
        return [puerto.device for puerto in list_ports.comports()]
    except Exception:                            # pragma: no cover
        return []


def hay_pyserial() -> bool:
    """¿Se puede hablar con hardware real desde este equipo?"""
    try:
        import serial            # noqa: F401  (solo se comprueba que exista)
    except ImportError:
        return False
    return True
