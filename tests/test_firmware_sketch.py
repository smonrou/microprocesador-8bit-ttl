"""El sketch completo compila y enlaza.

hal_arduino.cpp, display.cpp, consola.cpp y el .ino solo se compilan dentro
del IDE de Arduino, así que sin esto quedarían sin verificar hasta que llegue
la placa. Se compilan contra un stub de Arduino.h: no emula el hardware, pero
caza erratas, includes olvidados y firmas equivocadas.

La LÓGICA se verifica aparte, con el HAL falso (test_firmware_nucleo.py).
"""

import re
from pathlib import Path

import pytest

SKETCH = Path(__file__).resolve().parent.parent / "firmware" / "microprocesador"


def test_el_sketch_compila_y_enlaza(sketch_compilado):
    assert sketch_compilado.exists()


def test_el_ino_define_setup_y_loop():
    fuente = (SKETCH / "microprocesador.ino").read_text(encoding="utf-8")
    assert re.search(r"void\s+setup\s*\(\s*\)", fuente)
    assert re.search(r"void\s+loop\s*\(\s*\)", fuente)


def test_el_ino_refresca_el_display_en_loop():
    # Los dos dígitos comparten las líneas de segmento: sin refresco continuo
    # solo se vería uno.
    fuente = (SKETCH / "microprocesador.ino").read_text(encoding="utf-8")
    cuerpo = fuente.split("void loop()")[1]
    assert "display::refrescar" in cuerpo


# ── El núcleo no puede tocar el hardware ni calcular ─────────────────────

def test_el_nucleo_no_incluye_arduino():
    # nucleo.cpp debe compilar en la PC: si arrastrara Arduino.h, las pruebas
    # nativas serían imposibles y la paridad con el simulador se perdería.
    fuente = (SKETCH / "nucleo.cpp").read_text(encoding="utf-8")
    assert "Arduino.h" not in fuente
    assert "Serial" not in fuente


def test_el_formato_no_incluye_arduino():
    fuente = (SKETCH / "formato.cpp").read_text(encoding="utf-8")
    assert "Arduino.h" not in fuente
    assert "Serial" not in fuente


def test_el_nucleo_no_manipula_pines_directamente():
    fuente = (SKETCH / "nucleo.cpp").read_text(encoding="utf-8")
    for prohibido in ("digitalWrite", "digitalRead", "pinMode",
                      "PORTA", "PORTC", "PORTL", "PINC"):
        assert prohibido not in fuente, (
            f"nucleo.cpp toca '{prohibido}' directamente; toda la E/S debe "
            f"pasar por hal.h"
        )


def test_el_nucleo_no_calcula_operaciones_de_alu():
    """La regla central del proyecto: el Arduino no calcula.

    Se revisan las funciones del camino de datos buscando operadores
    aritméticos o lógicos entre valores. El resultado tiene que venir SIEMPRE
    de hal::leerF(), nunca de una cuenta en software.
    """
    fuente = (SKETCH / "nucleo.cpp").read_text(encoding="utf-8")
    cuerpo = fuente.split("void Nucleo::faseEscribir()")[1].split("\n}")[0]

    # Lo único permitido por el spec es Z = (F == 0).
    assert "hal::leerF()" in cuerpo
    for prohibido in (" + ", " - ", " & ", " | ", " ^ "):
        assert prohibido not in cuerpo, (
            f"faseEscribir() usa '{prohibido.strip()}': el resultado debe "
            f"leerse del bus F, no calcularse"
        )


def test_la_fase_de_escritura_lee_f_antes_de_pulsar_el_reloj():
    # El 181 es combinacional: tras el pulso, F pasa a valer (A nuevo) OP B.
    # Leerlo después daría un valor distinto y equivocado.
    fuente = (SKETCH / "nucleo.cpp").read_text(encoding="utf-8")
    cuerpo = fuente.split("void Nucleo::faseEscribir()")[1].split("\n}")[0]

    assert cuerpo.index("hal::leerF()") < cuerpo.index("hal::pulsoClockA()")


def test_la_inversion_del_acarreo_vive_solo_en_el_hal():
    # huboAcarreo() devuelve el valor ya corregido; el núcleo no debe
    # reinvertirlo por su cuenta.
    fuente = (SKETCH / "nucleo.cpp").read_text(encoding="utf-8")
    assert "huboAcarreo()" in fuente
    assert "!hal::huboAcarreo()" not in fuente


# ── Los pendientes de Parte C siguen aislados ────────────────────────────

def test_el_display_documenta_anodo_o_catodo_como_asunto_de_hardware():
    # Parte C punto 4 sigue abierto (los displays no se han comprado), pero ya
    # no es un pendiente de firmware: con la decodificación en hardware, el
    # tipo de display solo cambia el buffer (74LS240/74LS244) y el transistor.
    fuente = (SKETCH / "display.h").read_text(encoding="utf-8")
    assert "Parte C" in fuente
    assert "74LS240" in fuente and "74LS244" in fuente


def test_el_display_contempla_el_transistor_de_digito():
    # El común de un dígito conduce la corriente de hasta 6 segmentos a la vez
    # (el patrón "0"), muy por encima de los 40 mA de un pin. Los ocho comunes
    # los maneja el 74LS138 a través de un transistor cada uno.
    cabecera = (SKETCH / "display.h").read_text(encoding="utf-8")
    assert "transistor" in cabecera
    assert "74LS138" in cabecera


def test_el_display_no_decodifica_en_software():
    """La regla del ingeniero: el Arduino no convierte el dato para mostrarlo.

    La decodificación la hace el 74LS151 (Y = bit, W = complemento). Si vuelve
    a aparecer una tabla de patrones o un pin de segmento en el firmware, la
    conversión regresó al software y el requisito se rompió.
    """
    fuente = (SKETCH / "display.cpp").read_text(encoding="utf-8")
    for prohibido in ("PATRONES", "PIN_SEGMENTO", "0b0111111"):
        assert prohibido not in fuente, (
            f"display.cpp menciona '{prohibido}': la conversión a segmentos "
            f"debe ocurrir en el circuito, no en el Arduino"
        )


def test_el_dato_de_salida_no_pasa_por_el_arduino():
    # mostrarByte() recibe el valor solo para el HAL falso; en la placa el
    # byte viaja del bus F al registro de salida por cable, y el Arduino se
    # limita a pulsar el reloj que lo engancha.
    fuente = (SKETCH / "hal_arduino.cpp").read_text(encoding="utf-8")
    cuerpo = fuente.split("void mostrarByte(")[1].split("\n}")[0]
    assert "display::enganchar()" in cuerpo
    assert "(void)valor;" in cuerpo


# ── Protocolo serial ─────────────────────────────────────────────────────

@pytest.mark.parametrize("comando", [
    "LOAD", "LOADB", "RUN", "STEP", "RESET", "DUMP", "STATE", "VEL",
])
def test_el_protocolo_implementa_el_comando(comando):
    fuente = (SKETCH / "consola.cpp").read_text(encoding="utf-8")
    assert f'"{comando}"' in fuente


def test_load_confirma_cada_escritura():
    # El buffer RX del Arduino son 64 bytes y el .load tiene ~29 líneas: sin
    # confirmación, pegar de golpe podría perder comandos en silencio.
    fuente = (SKETCH / "consola.cpp").read_text(encoding="utf-8")
    cuerpo = fuente.split("void comandoLoad(")[1].split("\n}")[0]
    assert "OK dir=" in cuerpo


def test_los_comandos_desconocidos_responden_error():
    fuente = (SKETCH / "consola.cpp").read_text(encoding="utf-8")
    assert "ERR comando desconocido" in fuente


# ── El PC es hardware (2× 74LS161) ───────────────────────────────────────

def test_el_nucleo_no_guarda_ni_calcula_el_pc():
    # El ingeniero no acepta un PC simulado: incrementarlo en software sería
    # el Arduino calculando. El núcleo solo pide contar o cargar al 161.
    fuente = (SKETCH / "nucleo.cpp").read_text(encoding="utf-8")
    cabecera = (SKETCH / "nucleo.h").read_text(encoding="utf-8")
    assert not re.search(r"\bpc_\b", fuente + cabecera)
    assert "hal::incrementarPC()" in fuente
    assert "hal::cargarPC(operando_)" in fuente
    assert "hal::leerPC()" in fuente


def test_el_pc_se_lee_por_portk():
    fuente = (SKETCH / "hal_arduino.cpp").read_text(encoding="utf-8")
    cuerpo = fuente.split("uint8_t leerPC()")[1].split("\n}")[0]
    assert "PINK" in cuerpo
    assert "DDRK = 0x00" in fuente
