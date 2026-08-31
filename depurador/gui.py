"""Panel frontal en Tkinter: por dónde va la información y qué información es.

Este archivo es DELIBERADAMENTE delgado. Todo lo que se puede probar sin
pantalla vive en los otros módulos del paquete (``protocolo``,
``formato_numerico``, ``desensamblador``, ``cargador``, ``transporte``,
``servidor_falso``); aquí solo se construyen widgets y se cablean botones.
En este repo no hay convención de test headless de Tkinter y no se inventa
una: esta es la única pieza de verificación manual, y por eso no debe tener
lógica propia que se pueda equivocar en silencio.

CONCURRENCIA — la regla que no se puede romper:

    El hilo lector del transporte NUNCA toca un widget. Empuja líneas a una
    ``queue.Queue``; este archivo la vacía desde ``root.after(50, ...)``, que
    corre en el hilo principal. Todo widget se pinta ahí y solo ahí.
    Tkinter no es seguro entre hilos: saltarse esto produce cuelgues que
    aparecen semanas después y no se reproducen.

Lo que se ve:

- Registros A y B en binario, hexadecimal, con signo y sin signo A LA VEZ.
- PC e IR con el nemónico ya decodificado.
- Banderas Z y C de la unidad de control, siempre visibles.
- Las líneas de control de la ALU (M / S3-S0 / Cn) de la última operación.
- Los 256 bytes de memoria con la celda del PC resaltada.
- El desensamblado con la instrucción actual marcada.
- Los valores de OUT en los cuatro formatos.
- El tráfico crudo, tal cual viaja por el cable.
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

from . import cargador, desensamblador, formato_numerico, protocolo, transporte
from .servidor_falso import RETARDO_POR_DEFECTO, ServidorFalso

MONOESPACIADA = ("Consolas", 9)
MONOESPACIADA_GRANDE = ("Consolas", 11, "bold")

COLOR_FONDO = "#1e1e1e"
COLOR_PANEL = "#252526"
COLOR_TEXTO = "#d4d4d4"
COLOR_APAGADO = "#6a6a6a"
COLOR_RESALTE = "#264f78"
COLOR_ACTIVO = "#4ec9b0"
COLOR_BANDERA = "#f0c674"
COLOR_ENVIADO = "#569cd6"

MILISEGUNDOS_ENTRE_DRENAJES = 50
FILAS_MEMORIA = 16
COLUMNAS_MEMORIA = 16


class Depurador:
    """La ventana entera. Un solo objeto: no hay estado global."""

    def __init__(self, raiz: tk.Tk) -> None:
        self.raiz = raiz
        self.raiz.title("Depurador — microprocesador de 8 bits")
        self.raiz.configure(bg=COLOR_FONDO)

        # ── Estado observado ───────────────────────────────────────────────
        self.canal: Optional[transporte.Transporte] = None
        self.servidor: Optional[ServidorFalso] = None
        self.ensamblador = protocolo.EnsambladorDeBloques()
        self.memoria: List[int] = [0] * 256
        self.pendientes_de_carga: List[str] = []
        # Durante un RUN no se pide DUMP por instrucción (serían 16 líneas de
        # tráfico por cada una); se pide una sola vez al llegar al HLT.
        self.corriendo = False
        self.registro_a = 0
        self.registro_b = 0
        self.pc = 0
        self.ir = 0
        self.lineas_desensambladas: List[desensamblador.LineaDesensamblada] = []

        self._construir()
        self._pintar_memoria()
        self._pintar_desensamblado()
        self._refrescar_puertos()
        self.raiz.after(MILISEGUNDOS_ENTRE_DRENAJES, self._drenar)
        self.raiz.protocol("WM_DELETE_WINDOW", self._al_cerrar)

    # ══════════════════════════════════════════════════════════════════════
    # Construcción de widgets
    # ══════════════════════════════════════════════════════════════════════

    def _construir(self) -> None:
        self._construir_barra_conexion()

        cuerpo = tk.Frame(self.raiz, bg=COLOR_FONDO)
        cuerpo.pack(fill="both", expand=True, padx=6, pady=4)

        izquierda = tk.Frame(cuerpo, bg=COLOR_FONDO)
        izquierda.pack(side="left", fill="y")
        self._construir_registros(izquierda)
        self._construir_banderas(izquierda)
        self._construir_alu(izquierda)
        self._construir_controles(izquierda)

        centro = tk.Frame(cuerpo, bg=COLOR_FONDO)
        centro.pack(side="left", fill="both", expand=True, padx=6)
        self._construir_memoria(centro)

        derecha = tk.Frame(cuerpo, bg=COLOR_FONDO)
        derecha.pack(side="left", fill="both")
        self._construir_desensamblado(derecha)

        self._construir_registros_de_texto()

    def _marco(self, padre, titulo) -> tk.LabelFrame:
        return tk.LabelFrame(padre, text=titulo, bg=COLOR_PANEL, fg=COLOR_ACTIVO,
                             font=MONOESPACIADA, bd=1, relief="solid",
                             labelanchor="nw", padx=6, pady=4)

    def _etiqueta(self, padre, texto="", color=COLOR_TEXTO,
                  fuente=MONOESPACIADA, **opciones) -> tk.Label:
        return tk.Label(padre, text=texto, bg=COLOR_PANEL, fg=color,
                        font=fuente, anchor="w", **opciones)

    # ── Barra de conexión ──────────────────────────────────────────────────

    def _construir_barra_conexion(self) -> None:
        barra = tk.Frame(self.raiz, bg=COLOR_PANEL, pady=4, padx=6)
        barra.pack(fill="x")

        self.usar_servidor_local = tk.BooleanVar(value=True)
        tk.Checkbutton(
            barra, text="servidor de prueba local", variable=self.usar_servidor_local,
            bg=COLOR_PANEL, fg=COLOR_TEXTO, selectcolor=COLOR_FONDO,
            activebackground=COLOR_PANEL, activeforeground=COLOR_TEXTO,
            font=MONOESPACIADA, command=self._alternar_origen,
        ).pack(side="left")

        tk.Label(barra, text="  puerto serie:", bg=COLOR_PANEL, fg=COLOR_TEXTO,
                 font=MONOESPACIADA).pack(side="left")
        self.puerto_elegido = tk.StringVar()
        self.combo_puertos = ttk.Combobox(barra, textvariable=self.puerto_elegido,
                                          width=14, state="disabled",
                                          font=MONOESPACIADA)
        self.combo_puertos.pack(side="left", padx=4)

        self.boton_refrescar = tk.Button(barra, text="↻", font=MONOESPACIADA,
                                         command=self._refrescar_puertos,
                                         state="disabled")
        self.boton_refrescar.pack(side="left")

        self.boton_conectar = tk.Button(barra, text="Conectar", font=MONOESPACIADA,
                                        width=12, command=self._alternar_conexion)
        self.boton_conectar.pack(side="left", padx=8)

        self.estado_conexion = tk.Label(barra, text="desconectado", bg=COLOR_PANEL,
                                        fg=COLOR_APAGADO, font=MONOESPACIADA)
        self.estado_conexion.pack(side="left")

    # ── Registros A y B ────────────────────────────────────────────────────

    def _construir_registros(self, padre) -> None:
        marco = self._marco(padre, "Registros (74LS273)")
        marco.pack(fill="x", pady=2)

        encabezados = ("", "hex", "binario", "sin signo", "con signo")
        for columna, texto in enumerate(encabezados):
            self._etiqueta(marco, texto, COLOR_APAGADO).grid(
                row=0, column=columna, sticky="w", padx=4)

        self.celdas_registro = {}
        for fila, nombre in enumerate(("A", "B"), start=1):
            self._etiqueta(marco, nombre, COLOR_ACTIVO,
                           MONOESPACIADA_GRANDE).grid(row=fila, column=0, padx=4)
            self.celdas_registro[nombre] = []
            for columna in range(1, 5):
                celda = self._etiqueta(marco, "—", width=11)
                celda.grid(row=fila, column=columna, sticky="w", padx=4)
                self.celdas_registro[nombre].append(celda)

        # PC / IR: variables de la unidad de control, no del camino de datos.
        marco_control = self._marco(padre, "Unidad de control")
        marco_control.pack(fill="x", pady=2)
        self.etiqueta_pc = self._etiqueta(marco_control, "PC  = 0x00  (0)")
        self.etiqueta_pc.pack(fill="x")
        self.etiqueta_ir = self._etiqueta(marco_control, "IR  = 0x00  NOP")
        self.etiqueta_ir.pack(fill="x")
        self.etiqueta_ciclo = self._etiqueta(marco_control, "ciclo —   paso —",
                                             COLOR_APAGADO)
        self.etiqueta_ciclo.pack(fill="x")

    # ── Banderas ───────────────────────────────────────────────────────────

    def _construir_banderas(self, padre) -> None:
        marco = self._marco(padre, "Banderas")
        marco.pack(fill="x", pady=2)

        self.etiquetas_bandera = {}
        for columna, (nombre, ayuda) in enumerate(
                (("Z", "resultado cero"), ("C", "acarreo"))):
            caja = tk.Frame(marco, bg=COLOR_PANEL)
            caja.grid(row=0, column=columna, padx=10, pady=2)
            etiqueta = tk.Label(caja, text=f"{nombre}=0", bg=COLOR_FONDO,
                                fg=COLOR_APAGADO, font=MONOESPACIADA_GRANDE,
                                width=5, relief="solid", bd=1)
            etiqueta.pack()
            tk.Label(caja, text=ayuda, bg=COLOR_PANEL, fg=COLOR_APAGADO,
                     font=("Consolas", 7)).pack()
            self.etiquetas_bandera[nombre] = etiqueta

        self.etiqueta_detenido = self._etiqueta(marco, "CPU lista", COLOR_ACTIVO)
        self.etiqueta_detenido.grid(row=1, column=0, columnspan=2, sticky="w")

    # ── Líneas de control de la ALU ────────────────────────────────────────

    def _construir_alu(self, padre) -> None:
        marco = self._marco(padre, "ALU 2x SN74LS181")
        marco.pack(fill="x", pady=2)
        self.etiqueta_alu = self._etiqueta(marco, "M=—  S=————  Cn=—")
        self.etiqueta_alu.pack(fill="x")
        self.etiqueta_alu_nota = self._etiqueta(
            marco, "(sin operación de ALU todavía)", COLOR_APAGADO)
        self.etiqueta_alu_nota.pack(fill="x")

    # ── Botonera ───────────────────────────────────────────────────────────

    def _construir_controles(self, padre) -> None:
        marco = self._marco(padre, "Ejecución")
        marco.pack(fill="x", pady=2)

        botones = tk.Frame(marco, bg=COLOR_PANEL)
        botones.pack(fill="x")
        self.botones_comando = {}
        for columna, orden in enumerate(("RUN", "STEP", "RESET", "BORRAR")):
            boton = tk.Button(botones, text=orden, font=MONOESPACIADA, width=7,
                              state="disabled",
                              command=lambda o=orden: self._enviar_comando(o))
            boton.grid(row=0, column=columna, padx=2, pady=2)
            self.botones_comando[orden] = boton

        self.boton_estado = tk.Button(botones, text="STATE", font=MONOESPACIADA,
                                      width=7, state="disabled",
                                      command=lambda: self._enviar_comando("STATE"))
        self.boton_estado.grid(row=1, column=0, padx=2, pady=2)
        self.botones_comando["STATE"] = self.boton_estado

        self.boton_dump = tk.Button(botones, text="DUMP", font=MONOESPACIADA,
                                    width=7, state="disabled",
                                    command=self._pedir_memoria)
        self.boton_dump.grid(row=1, column=1, padx=2, pady=2)
        self.botones_comando["DUMP"] = self.boton_dump

        self.boton_cargar = tk.Button(botones, text="Cargar .load",
                                      font=MONOESPACIADA, width=16,
                                      state="disabled", command=self._cargar_archivo)
        self.boton_cargar.grid(row=1, column=2, columnspan=2, padx=2, pady=2)
        self.botones_comando["CARGAR"] = self.boton_cargar

        # VEL: retardo entre instrucciones en RUN, 0-5000 ms (consola.cpp).
        velocidad = tk.Frame(marco, bg=COLOR_PANEL)
        velocidad.pack(fill="x", pady=(6, 0))
        tk.Label(velocidad, text="VEL", bg=COLOR_PANEL, fg=COLOR_TEXTO,
                 font=MONOESPACIADA).pack(side="left")
        self.velocidad = tk.IntVar(value=RETARDO_POR_DEFECTO)
        tk.Scale(velocidad, from_=0, to=5000, resolution=50, orient="horizontal",
                 variable=self.velocidad, bg=COLOR_PANEL, fg=COLOR_TEXTO,
                 troughcolor=COLOR_FONDO, highlightthickness=0, length=170,
                 font=("Consolas", 7)).pack(side="left", fill="x", expand=True)
        self.boton_velocidad = tk.Button(velocidad, text="ms", font=MONOESPACIADA,
                                         state="disabled",
                                         command=self._aplicar_velocidad)
        self.boton_velocidad.pack(side="left")
        self.botones_comando["VEL"] = self.boton_velocidad

    # ── Memoria ────────────────────────────────────────────────────────────

    def _construir_memoria(self, padre) -> None:
        marco = self._marco(padre, "Memoria 256 B  (0x00-0xBF programa · "
                                   "0xC0-0xFF datos, por convención)")
        marco.pack(fill="both", expand=True)

        rejilla = tk.Frame(marco, bg=COLOR_PANEL)
        rejilla.pack()

        for columna in range(COLUMNAS_MEMORIA):
            self._etiqueta(rejilla, f"{columna:X}", COLOR_APAGADO).grid(
                row=0, column=columna + 1, padx=1)

        self.celdas_memoria = []
        for fila in range(FILAS_MEMORIA):
            self._etiqueta(rejilla, f"{fila * 16:02X}", COLOR_APAGADO).grid(
                row=fila + 1, column=0, padx=(0, 4))
            for columna in range(COLUMNAS_MEMORIA):
                celda = tk.Label(rejilla, text="00", bg=COLOR_FONDO, fg=COLOR_TEXTO,
                                 font=MONOESPACIADA, width=2, padx=2)
                celda.grid(row=fila + 1, column=columna + 1, padx=1, pady=1)
                self.celdas_memoria.append(celda)

        self.etiqueta_memoria = self._etiqueta(
            marco, "la celda resaltada es la que apunta el PC", COLOR_APAGADO)
        self.etiqueta_memoria.pack(fill="x", pady=(4, 0))

    # ── Desensamblado ──────────────────────────────────────────────────────

    def _construir_desensamblado(self, padre) -> None:
        marco = self._marco(padre, "Desensamblado")
        marco.pack(fill="both", expand=True)

        self.lista_desensamblado = tk.Listbox(
            marco, font=MONOESPACIADA, bg=COLOR_FONDO, fg=COLOR_TEXTO, width=28,
            height=24, selectbackground=COLOR_RESALTE, selectforeground="white",
            highlightthickness=0, bd=0, activestyle="none")
        self.lista_desensamblado.pack(side="left", fill="both", expand=True)
        barra = tk.Scrollbar(marco, command=self.lista_desensamblado.yview)
        barra.pack(side="right", fill="y")
        self.lista_desensamblado.config(yscrollcommand=barra.set)

    # ── Logs ───────────────────────────────────────────────────────────────

    def _construir_registros_de_texto(self) -> None:
        abajo = tk.Frame(self.raiz, bg=COLOR_FONDO)
        abajo.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        marco_salida = self._marco(abajo, "Salidas (OUT) en los cuatro formatos")
        marco_salida.pack(side="left", fill="both", expand=True, padx=(0, 3))
        self.log_salidas = self._texto(marco_salida, alto=8)

        marco_trafico = self._marco(abajo, "Tráfico crudo (lo que viaja por el cable)")
        marco_trafico.pack(side="left", fill="both", expand=True, padx=(3, 0))
        self.log_trafico = self._texto(marco_trafico, alto=8)
        self.log_trafico.tag_configure("enviado", foreground=COLOR_ENVIADO)
        self.log_trafico.tag_configure("aviso", foreground=COLOR_BANDERA)

    def _texto(self, padre, alto) -> tk.Text:
        caja = tk.Text(padre, height=alto, font=MONOESPACIADA, bg=COLOR_FONDO,
                       fg=COLOR_TEXTO, insertbackground=COLOR_TEXTO,
                       highlightthickness=0, bd=0, wrap="none", state="disabled")
        caja.pack(side="left", fill="both", expand=True)
        barra = tk.Scrollbar(padre, command=caja.yview)
        barra.pack(side="right", fill="y")
        caja.config(yscrollcommand=barra.set)
        return caja

    def _escribir(self, caja: tk.Text, texto: str, etiqueta: str = "") -> None:
        caja.config(state="normal")
        caja.insert("end", texto + "\n", etiqueta or ())
        caja.see("end")
        caja.config(state="disabled")

    # ══════════════════════════════════════════════════════════════════════
    # Conexión
    # ══════════════════════════════════════════════════════════════════════

    def _alternar_origen(self) -> None:
        local = self.usar_servidor_local.get()
        estado = "disabled" if local else "readonly"
        self.combo_puertos.config(state=estado)
        self.boton_refrescar.config(state="disabled" if local else "normal")

    def _refrescar_puertos(self) -> None:
        puertos = transporte.listar_puertos_serie()
        self.combo_puertos["values"] = puertos
        if puertos and not self.puerto_elegido.get():
            self.puerto_elegido.set(puertos[0])
        if not puertos and not transporte.hay_pyserial():
            self.combo_puertos.set("(falta pyserial)")

    def _alternar_conexion(self) -> None:
        if self.canal is not None:
            self._desconectar()
        else:
            self._conectar()

    def _conectar(self) -> None:
        try:
            if self.usar_servidor_local.get():
                # El servidor falso vive dentro de este mismo proceso: es un
                # Arduino de mentira, no un servicio aparte que haya que lanzar.
                self.servidor = ServidorFalso(puerto=0,
                                              retardo=self.velocidad.get()).iniciar()
                self.canal = transporte.TransporteSocket("127.0.0.1",
                                                         self.servidor.puerto)
            else:
                puerto = self.puerto_elegido.get()
                if not puerto or puerto.startswith("("):
                    messagebox.showwarning("Depurador", "Elige un puerto serie.")
                    return
                self.canal = transporte.TransporteSerial(puerto)
            self.canal.abrir()
        except Exception as error:
            self._desconectar()
            messagebox.showerror("Depurador", f"No se pudo conectar:\n{error}")
            return

        self.ensamblador = protocolo.EnsambladorDeBloques()
        self.estado_conexion.config(text=self.canal.descripcion(), fg=COLOR_ACTIVO)
        self.boton_conectar.config(text="Desconectar")
        for boton in self.botones_comando.values():
            boton.config(state="normal")
        self._escribir(self.log_trafico, f"— conectado: {self.canal.descripcion()} —",
                       "aviso")
        self._aplicar_velocidad()
        self._pedir_memoria()

    def _desconectar(self) -> None:
        if self.canal is not None:
            self.canal.cerrar()
            self.canal = None
        if self.servidor is not None:
            self.servidor.detener()
            self.servidor = None
        self.pendientes_de_carga = []
        self.estado_conexion.config(text="desconectado", fg=COLOR_APAGADO)
        self.boton_conectar.config(text="Conectar")
        for boton in self.botones_comando.values():
            boton.config(state="disabled")

    def _al_cerrar(self) -> None:
        self._desconectar()
        self.raiz.destroy()

    # ══════════════════════════════════════════════════════════════════════
    # Envío
    # ══════════════════════════════════════════════════════════════════════

    def _enviar(self, orden: str) -> None:
        if self.canal is None:
            return
        try:
            self.canal.enviar_linea(orden)
        except Exception as error:
            self._escribir(self.log_trafico, f"— error al enviar: {error} —", "aviso")
            self._desconectar()
            return
        self._escribir(self.log_trafico, f"> {orden}", "enviado")

    def _enviar_comando(self, orden: str) -> None:
        self._enviar(orden)
        if orden in ("RESET", "BORRAR"):
            self.pendientes_de_carga = []
            self.corriendo = False
            self._pedir_memoria()

    def _aplicar_velocidad(self) -> None:
        self._enviar(f"VEL {self.velocidad.get()}")

    def _pedir_memoria(self) -> None:
        self._enviar("DUMP")

    def _cargar_archivo(self) -> None:
        ruta = filedialog.askopenfilename(
            title="Abrir un .load generado por «python -m asm»",
            initialdir=os.path.join(os.getcwd(), "programas"),
            filetypes=[("Guiones de carga", "*.load"), ("Todos", "*.*")])
        if not ruta:
            return
        try:
            lineas = cargador.leer_lineas(ruta)
        except OSError as error:
            messagebox.showerror("Depurador", f"No se pudo leer:\n{error}")
            return

        # Una línea a la vez, esperando el OK/ERR de cada una: el buffer de
        # recepción del Arduino son 64 bytes y mandarlas de golpe perdería
        # comandos EN SILENCIO (consola.h).
        self.pendientes_de_carga = list(lineas)
        self._escribir(self.log_trafico,
                       f"— cargando {os.path.basename(ruta)} "
                       f"({len(lineas)} líneas, una a una) —", "aviso")
        self._enviar_siguiente_de_la_carga()

    def _enviar_siguiente_de_la_carga(self) -> None:
        if not self.pendientes_de_carga:
            return
        self._enviar(self.pendientes_de_carga.pop(0))
        if not self.pendientes_de_carga:
            self._pedir_memoria()

    # ══════════════════════════════════════════════════════════════════════
    # Recepción — HILO PRINCIPAL, disparado por root.after
    # ══════════════════════════════════════════════════════════════════════

    def _drenar(self) -> None:
        """Vacía la cola del transporte y pinta. ÚNICO sitio que toca widgets
        con datos que vienen del hilo lector."""
        try:
            if self.canal is not None:
                for linea in self.canal.drenar():
                    if linea is transporte.CENTINELA_DESCONEXION:
                        self._escribir(self.log_trafico, "— conexión cerrada —",
                                       "aviso")
                        self._desconectar()
                        break
                    for mensaje in self.ensamblador.agregar(linea):
                        self._atender_mensaje(mensaje)
        finally:
            self.raiz.after(MILISEGUNDOS_ENTRE_DRENAJES, self._drenar)

    def _atender_mensaje(self, mensaje: protocolo.Mensaje) -> None:
        self._escribir(self.log_trafico, mensaje.texto)

        if mensaje.es_bloque:
            self._actualizar_alu(mensaje.texto)
            return

        linea = mensaje.texto
        if linea.startswith("#"):
            self._actualizar_desde_claves(
                protocolo.parsear_linea_clave_valor(linea) or {})
            return

        fila = protocolo.parsear_fila_dump(linea)
        if fila is not None:
            direccion, bytes_leidos = fila
            for desplazamiento, byte in enumerate(bytes_leidos):
                self.memoria[(direccion + desplazamiento) & 0xFF] = byte
            self._pintar_memoria()
            self._pintar_desensamblado()
            return

        if linea == "--- RUN ---":
            self.corriendo = True
            return
        if linea == "--- HLT ---":
            # STA pudo cambiar la memoria; hay que volver a leerla.
            self.corriendo = False
            self._pedir_memoria()
            return

        if protocolo.es_respuesta_final(linea):
            if linea.startswith("ERR"):
                self.corriendo = False
            self._enviar_siguiente_de_la_carga()

    # ── Pintado ────────────────────────────────────────────────────────────

    def _actualizar_desde_claves(self, datos: dict) -> None:
        if "paso" in datos:
            self.etiqueta_ciclo.config(text=f"ciclo —   paso {datos['paso']}")
            return

        es_estado = "ciclo" not in datos          # línea de STATE/RESET

        if "pc" in datos:
            self.pc = int(datos["pc"])
        if "ir" in datos:
            self.ir = int(datos["ir"])

        # Las líneas #ciclo= del firmware NO siempre traen A y B: nucleo.cpp
        # reinicia la traza y solo rellena los campos que toca la instrucción
        # (ver protocolo.registros_significativos). Conservar el último valor
        # conocido es más honesto que pintar un 0 inventado; STATE los trae
        # siempre, leídos de los registros físicos a través de la ALU.
        a_valida = b_valida = True
        if not es_estado:
            a_valida, b_valida = protocolo.registros_significativos(
                str(datos.get("op", "")))
        if a_valida and "a" in datos:
            self.registro_a = int(datos["a"])
        if b_valida and "b" in datos:
            self.registro_b = int(datos["b"])

        self._pintar_registros()

        mnemonico = str(datos.get("op") or desensamblador.mnemonico_de(self.ir))
        self.etiqueta_pc.config(text=f"PC  = 0x{self.pc:02X}  ({self.pc})")
        self.etiqueta_ir.config(text=f"IR  = 0x{self.ir:02X}  {mnemonico}")
        if "ciclo" in datos:
            self.etiqueta_ciclo.config(
                text=f"ciclo {datos['ciclo']}   instrucción completa")

        for nombre in ("z", "c"):
            if nombre in datos:
                encendida = int(datos[nombre]) == 1
                self.etiquetas_bandera[nombre.upper()].config(
                    text=f"{nombre.upper()}={int(datos[nombre])}",
                    fg=COLOR_BANDERA if encendida else COLOR_APAGADO,
                    bg="#3a3320" if encendida else COLOR_FONDO)

        if "halted" in datos:
            detenida = int(datos["halted"]) == 1
            self.etiqueta_detenido.config(
                text="CPU DETENIDA (usa RESET)" if detenida else "CPU lista",
                fg=COLOR_BANDERA if detenida else COLOR_ACTIVO)

        if "salida" in datos:
            resumen = formato_numerico.resumen_numerico(int(datos["salida"]))
            self._escribir(
                self.log_salidas,
                f"OUT  hex {resumen.hexadecimal}   bin {formato_numerico.binario_agrupado(resumen.byte)}"
                f"   sin signo {resumen.sin_signo:>3}   con signo "
                f"{formato_numerico.con_signo_con_letrero(resumen.byte):>4}")

        self._pintar_memoria()
        self._pintar_desensamblado()

        # En modo STEP se refresca la memoria al cerrar cada instrucción: así
        # se ve el efecto de un STA en la celda de destino.
        if "ciclo" in datos and not self.corriendo:
            self._pedir_memoria()

    def _pintar_registros(self) -> None:
        for nombre, valor in (("A", self.registro_a), ("B", self.registro_b)):
            resumen = formato_numerico.resumen_numerico(valor)
            textos = (resumen.hexadecimal,
                      formato_numerico.binario_agrupado(resumen.byte),
                      str(resumen.sin_signo),
                      formato_numerico.con_signo_con_letrero(resumen.byte))
            for celda, texto in zip(self.celdas_registro[nombre], textos):
                celda.config(text=texto)

    def _actualizar_alu(self, bloque: str) -> None:
        control = protocolo.extraer_control_alu(bloque)
        if control is None:
            # La línea "ALU: ..." sencillamente no está en el bloque cuando la
            # instrucción no fue de ALU. Se deja el último control visible.
            self.etiqueta_alu_nota.config(
                text="(la última instrucción no usó la ALU)")
            return
        self.etiqueta_alu.config(
            text=f"M={control['M']}  S={control['S']}  Cn={control['Cn']}")
        modo = "aritmético" if control["M"] == 0 else "lógico"
        self.etiqueta_alu_nota.config(text=f"M={control['M']} → modo {modo}")

    def _pintar_memoria(self) -> None:
        for direccion, celda in enumerate(self.celdas_memoria):
            byte = self.memoria[direccion]
            es_pc = direccion == self.pc
            celda.config(
                text=f"{byte:02X}",
                bg=COLOR_RESALTE if es_pc else COLOR_FONDO,
                fg="white" if es_pc else (COLOR_TEXTO if byte else COLOR_APAGADO))

    def _pintar_desensamblado(self) -> None:
        self.lineas_desensambladas = desensamblador.desensamblar(self.memoria,
                                                                 0x00, 0xBF)
        self.lista_desensamblado.delete(0, "end")
        for linea in self.lineas_desensambladas:
            bytes_texto = " ".join(f"{b:02X}" for b in linea.bytes_crudos)
            self.lista_desensamblado.insert(
                "end", f"{linea.direccion:02X}  {bytes_texto:<5}  {linea.texto}")

        indice = desensamblador.indice_por_direccion(self.lineas_desensambladas)
        self.lista_desensamblado.selection_clear(0, "end")
        if self.pc in indice:
            posicion = indice[self.pc]
            self.lista_desensamblado.selection_set(posicion)
            self.lista_desensamblado.see(posicion)


def main() -> None:
    raiz = tk.Tk()
    Depurador(raiz)
    raiz.mainloop()
