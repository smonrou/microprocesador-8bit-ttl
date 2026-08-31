"""256-byte von Neumann memory (contexto_proyecto.md A.2/A.6). No zone protection —
program and data share one address space, an instruction may legally write
into the program zone.
"""

SIZE = 256


class Memory:
    def __init__(self):
        self.cells = bytearray(SIZE)

    def read(self, address: int) -> int:
        return self.cells[address & 0xFF]

    def write(self, address: int, value: int) -> None:
        self.cells[address & 0xFF] = value & 0xFF

    def load_bytes(self, data, start: int = 0) -> None:
        for offset, byte in enumerate(data):
            self.write(start + offset, byte)

    def dump(self, start: int = 0, end: int = SIZE - 1):
        return list(self.cells[start:end + 1])

    def reset(self) -> None:
        self.cells = bytearray(SIZE)
