"""State-dump formatting — reproduces the A.9 STEP-mode block format.

"Ciclo N" = the N-th *completed instruction* (session decision), not each
microstep. The ALU-op rendering matches the literal SUB example in A.9
byte-for-byte (see tests/test_state_dump.py). Non-ALU renderings are a
design choice, not spec'd verbatim, and are not exact-string tested.
"""

from dataclasses import dataclass
from typing import Optional

from .isa import Category, Mode

MODE_TEXT = {
    Mode.IMPLICIT: "modo implícito",
    Mode.DIRECT: "modo directo",
    Mode.IMMEDIATE: "modo inmediato",
    Mode.NONE: "sin operando",
}

ALU_SYMBOLS = {
    "ADD": "+",
    "SUB": "-",
    "AND": "&",
    "OR": "|",
    "XOR": "^",
}


@dataclass
class InstructionTrace:
    cycle_number: int
    pc_before: int
    ir: int = 0
    opcode: int = 0
    mnemonic: str = ""
    length: int = 1
    mode: Mode = Mode.NONE
    category: Optional[Category] = None
    operand: Optional[int] = None
    register: Optional[str] = None
    a_before: int = 0
    b_before: int = 0
    alu_m: Optional[int] = None
    alu_s: Optional[str] = None
    alu_cn: Optional[int] = None
    a_after: int = 0
    b_after: int = 0
    z: int = 0
    c: int = 0
    pc_after: int = 0
    output_value: Optional[int] = None


def _execute_result_lines_alu(trace: InstructionTrace):
    op_symbol = ALU_SYMBOLS.get(trace.mnemonic, "?")
    execute = f"EXECUTE A=0x{trace.a_before:02X} {op_symbol} B=0x{trace.b_before:02X}"
    alu = f"        ALU: M={trace.alu_m} S={trace.alu_s} Cn={trace.alu_cn}"
    result = f"RESULT  A=0x{trace.a_after:02X}   Z={trace.z}  C={trace.c}"
    return [execute, alu, result]


def _execute_result_lines_other(trace: InstructionTrace):
    cat = trace.category
    if cat == Category.LOAD_DIRECT:
        reg = trace.register
        value = trace.a_after if reg == "A" else trace.b_after
        execute = f"EXECUTE Mem[0x{trace.operand:02X}] → {reg}"
        result = f"RESULT  {reg}=0x{value:02X}"
    elif cat == Category.STORE_DIRECT:
        execute = f"EXECUTE A → Mem[0x{trace.operand:02X}]"
        result = f"RESULT  Mem[0x{trace.operand:02X}]=0x{trace.a_before:02X}"
    elif cat == Category.LOAD_IMMEDIATE:
        reg = trace.register
        value = trace.a_after if reg == "A" else trace.b_after
        execute = f"EXECUTE #0x{trace.operand:02X} → {reg}"
        result = f"RESULT  {reg}=0x{value:02X}"
    elif cat == Category.JUMP_UNCONDITIONAL:
        execute = f"EXECUTE PC ← 0x{trace.operand:02X}"
        result = f"RESULT  salto incondicional"
    elif cat == Category.JUMP_CONDITIONAL:
        taken = trace.pc_after == trace.operand
        execute = f"EXECUTE {trace.mnemonic} 0x{trace.operand:02X} (Z={trace.z})"
        result = f"RESULT  {'salta' if taken else 'no salta'}"
    elif cat == Category.OUTPUT:
        execute = f"EXECUTE Muestra A"
        result = f"RESULT  A=0x{trace.a_before:02X}"
    else:  # CONTROL: NOP, HLT
        execute = f"EXECUTE {trace.mnemonic}"
        result = f"RESULT  —"
    return [execute, result]


def format_cycle(trace: InstructionTrace) -> str:
    lines = [f"─── Ciclo {trace.cycle_number} ───"]
    lines.append(
        f"FETCH   PC=0x{trace.pc_before:02X}  →  IR=0x{trace.ir:02X} ({trace.mnemonic})"
    )
    bytes_text = "1 byte" if trace.length == 1 else "2 bytes"
    opcode_bin = format(trace.opcode, "04b")
    mode_text = MODE_TEXT[trace.mode]
    lines.append(f"DECODE  Opcode {opcode_bin} | {bytes_text} | {mode_text}")

    if trace.category == Category.ALU:
        lines.extend(_execute_result_lines_alu(trace))
    else:
        lines.extend(_execute_result_lines_other(trace))

    lines.append(f"PC → 0x{trace.pc_after:02X}")
    return "\n".join(lines)


def format_microstep(label: str, trace: InstructionTrace) -> str:
    return f"{label}  (Ciclo {trace.cycle_number} en curso, PC=0x{trace.pc_before:02X})"
