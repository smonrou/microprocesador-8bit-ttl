from sim.memory import Memory, SIZE


def test_init_all_zero():
    mem = Memory()
    assert mem.dump() == [0] * SIZE


def test_write_read_roundtrip():
    mem = Memory()
    mem.write(0xC8, 0x2A)
    assert mem.read(0xC8) == 0x2A


def test_no_zone_protection_program_zone_is_writable():
    # A.6: la separación 0x00-0xBF / 0xC0-0xFF es convención, no restricción
    # de hardware. Nada debe impedir escribir en la zona de programa.
    mem = Memory()
    mem.write(0x05, 0xFF)
    assert mem.read(0x05) == 0xFF


def test_load_bytes_at_offset():
    mem = Memory()
    mem.load_bytes([0x11, 0x22, 0x33], start=0xC0)
    assert mem.read(0xC0) == 0x11
    assert mem.read(0xC1) == 0x22
    assert mem.read(0xC2) == 0x33


def test_address_wraps_to_8_bits():
    mem = Memory()
    mem.write(0x100, 0xAB)  # 0x100 & 0xFF == 0x00
    assert mem.read(0x00) == 0xAB
