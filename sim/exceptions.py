class CpuError(Exception):
    """Base error for the simulated CPU."""


class CpuHaltedError(CpuError):
    """Raised when step() is called after HLT has already executed."""

    def __init__(self, pc: int):
        self.pc = pc
        super().__init__(f"CPU halted (PC=0x{pc:02X}); no more steps possible")


class CycleLimitExceeded(CpuError):
    """Raised by run() when max_cycles instructions completed without HLT."""

    def __init__(self, pc: int, instruction_count: int):
        self.pc = pc
        self.instruction_count = instruction_count
        super().__init__(
            f"Cycle limit exceeded after {instruction_count} instructions "
            f"(PC=0x{pc:02X}); possible infinite loop"
        )
