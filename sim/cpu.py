"""CPU — fetch/decode/execute with variable microcycles (contexto_proyecto.md A.8/A.9).

step() advances exactly one microcycle. run() is built on top of step() so
RUN and STEP share the same ALU/flag logic (no duplicated semantics).

Structural guarantee for the critical flag rule (A.5: "solo las 5
operaciones de ALU actualizan Z y C"): only the ALU branch of
_execute_microstep ever assigns self.z / self.c.
"""

from dataclasses import dataclass
from typing import Optional

from . import alu
from .exceptions import CpuHaltedError, CycleLimitExceeded
from .isa import OPCODE_TABLE, Category, InstructionSpec
from .memory import Memory
from .trace import InstructionTrace, format_cycle

DEFAULT_MAX_CYCLES = 10_000

# (M, S3-S0, Cn) per ALU op, for trace display — contexto_proyecto.md A.3/6.6.
# In logic mode (M=1) the carry-in is not significant, but the pin still has
# to be driven to some level: a real input cannot float. The firmware puts it
# HIGH, so the dump reports 1 and matches what a multimeter would read on
# pin 7. (This was None until the B.3 differential test caught the mismatch.)
ALU_CONTROL = {
    "ADD": (0, "1001", 1),
    "SUB": (0, "0110", 0),
    "AND": (1, "1011", 1),
    "OR": (1, "1110", 1),
    "XOR": (1, "0110", 1),
}


@dataclass
class MicrostepResult:
    label: str
    trace: InstructionTrace
    completed: bool = False


class CPU:
    def __init__(self, memory: Optional[Memory] = None):
        self.memory = memory if memory is not None else Memory()
        self.a = 0
        self.b = 0
        self.pc = 0
        self.ir = 0
        self.z = 0
        self.c = 0
        self.halted = False
        self.instruction_count = 0
        self.output = []

        self._pending_steps = []
        self._current_spec: Optional[InstructionSpec] = None
        self._operand: Optional[int] = None
        self._trace: Optional[InstructionTrace] = None

    def reset(self) -> None:
        """PC, registers and flags to 0 (A.9 RESET). Memory is left intact —
        RESET restarts execution, it doesn't erase a loaded program."""
        self.a = 0
        self.b = 0
        self.pc = 0
        self.ir = 0
        self.z = 0
        self.c = 0
        self.halted = False
        self.instruction_count = 0
        self.output = []
        self._pending_steps = []
        self._current_spec = None
        self._operand = None
        self._trace = None

    # ------------------------------------------------------------------
    # STEP mode
    # ------------------------------------------------------------------

    def step(self) -> MicrostepResult:
        if self.halted:
            raise CpuHaltedError(self.pc)

        if not self._pending_steps:
            return self._begin_instruction()

        label = self._pending_steps.pop(0)
        self._execute_microstep(label)

        if not self._pending_steps:
            self._trace.pc_after = self.pc
            # Las banderas vigentes al terminar. Para las operaciones de ALU
            # ya las puso _write_phase con los mismos valores; para el resto
            # esto es lo que hace que el volcado diga la verdad — un JZ que
            # informara siempre Z=0 no explicaría por qué saltó o no.
            self._trace.z = self.z
            self._trace.c = self.c
            self.instruction_count += 1
            completed_trace = self._trace
            self._current_spec = None
            self._operand = None
            self._trace = None
            return MicrostepResult(label=label, trace=completed_trace, completed=True)

        return MicrostepResult(label=label, trace=self._trace, completed=False)

    def _begin_instruction(self) -> MicrostepResult:
        pc_before = self.pc
        self.ir = self.memory.read(self.pc)
        self.pc = (self.pc + 1) & 0xFF
        opcode = self.ir >> 4
        spec = OPCODE_TABLE[opcode]

        self._current_spec = spec
        self._operand = None
        self._trace = InstructionTrace(
            cycle_number=self.instruction_count + 1,
            pc_before=pc_before,
            ir=self.ir,
            opcode=opcode,
            mnemonic=spec.mnemonic,
            length=spec.length,
            mode=spec.mode,
            category=spec.category,
            register=spec.register,
            a_before=self.a,
            b_before=self.b,
        )
        self._pending_steps = list(spec.microstep_labels[1:])  # FETCH already done
        return MicrostepResult(label="FETCH", trace=self._trace, completed=False)

    def _execute_microstep(self, label: str) -> None:
        spec = self._current_spec
        trace = self._trace

        if label == "DECODE":
            return  # informational only, no state change

        if label == "FETCH2":
            self._operand = self.memory.read(self.pc)
            self.pc = (self.pc + 1) & 0xFF
            trace.operand = self._operand
            return

        if label == "WAIT":
            return  # propagation delay, no-op in simulation

        if label == "EXECUTE":
            self._execute_phase(spec, trace)
            return

        if label == "WRITE":
            self._write_phase(spec, trace)
            return

        raise ValueError(f"unknown microstep label: {label}")

    def _execute_phase(self, spec: InstructionSpec, trace: InstructionTrace) -> None:
        cat = spec.category

        if cat == Category.ALU:
            m, s, cn = ALU_CONTROL[spec.mnemonic]
            trace.alu_m, trace.alu_s, trace.alu_cn = m, s, cn
            return  # actual compute happens at WRITE, mirroring real hardware timing

        if cat == Category.LOAD_DIRECT:
            value = self.memory.read(self._operand)
            if spec.register == "A":
                self.a = value
            else:
                self.b = value
            trace.a_after, trace.b_after = self.a, self.b
            return

        if cat == Category.STORE_DIRECT:
            self.memory.write(self._operand, self.a)
            return

        if cat == Category.LOAD_IMMEDIATE:
            value = self._operand
            if spec.register == "A":
                self.a = value
            else:
                self.b = value
            trace.a_after, trace.b_after = self.a, self.b
            return

        if cat == Category.JUMP_UNCONDITIONAL:
            self.pc = self._operand
            return

        if cat == Category.JUMP_CONDITIONAL:
            condition = (self.z == 1) if spec.mnemonic == "JZ" else (self.z == 0)
            if condition:
                self.pc = self._operand
            return

        if cat == Category.OUTPUT:
            self.output.append(self.a)
            trace.output_value = self.a
            return

        if cat == Category.CONTROL:
            if spec.mnemonic == "HLT":
                self.halted = True
            return  # NOP: nothing

        raise ValueError(f"unhandled category: {cat}")

    def _write_phase(self, spec: InstructionSpec, trace: InstructionTrace) -> None:
        # Only reached for ALU ops. This is the only place Z/C are ever
        # assigned — enforces the "only ALU touches flags" rule structurally.
        func = alu.ALU_FUNCTIONS[spec.mnemonic]
        result, z, c = func(self.a, self.b)
        self.a = result
        self.z = z
        self.c = c
        trace.a_after = self.a
        trace.z = self.z
        trace.c = self.c

    # ------------------------------------------------------------------
    # RUN mode — built on top of step(), same semantics as STEP
    # ------------------------------------------------------------------

    def run(self, max_cycles: int = DEFAULT_MAX_CYCLES) -> int:
        while not self.halted:
            self.step()
            if self.instruction_count > max_cycles:
                raise CycleLimitExceeded(self.pc, self.instruction_count)
        return self.instruction_count

    def run_to_completion_with_trace(self, max_cycles: int = DEFAULT_MAX_CYCLES):
        """Like run(), but returns the list of format_cycle() strings for each
        completed instruction — convenience for manual STEP-mode inspection."""
        dumps = []
        while not self.halted:
            result = self.step()
            if result.completed:
                dumps.append(format_cycle(result.trace))
            if self.instruction_count > max_cycles:
                raise CycleLimitExceeded(self.pc, self.instruction_count)
        return dumps
