"""Golden test: reproduce the literal SUB example from contexto_proyecto.md A.9
byte-for-byte. This is the only exact-string test — non-ALU category dumps
are a design choice not spec'd verbatim (see plan doc)."""

from sim.isa import Category, Mode
from sim.trace import InstructionTrace, format_cycle

EXPECTED = (
    "─── Ciclo 3 ───\n"
    "FETCH   PC=0x04  →  IR=0x70 (SUB)\n"
    "DECODE  Opcode 0111 | 1 byte | modo implícito\n"
    "EXECUTE A=0x0C - B=0x05\n"
    "        ALU: M=0 S=0110 Cn=0\n"
    "RESULT  A=0x07   Z=0  C=1\n"
    "PC → 0x05"
)


def test_a9_sub_example_matches_verbatim():
    trace = InstructionTrace(
        cycle_number=3,
        pc_before=0x04,
        ir=0x70,
        opcode=0b0111,
        mnemonic="SUB",
        length=1,
        mode=Mode.IMPLICIT,
        category=Category.ALU,
        a_before=0x0C,
        b_before=0x05,
        alu_m=0,
        alu_s="0110",
        alu_cn=0,
        a_after=0x07,
        z=0,
        c=1,
        pc_after=0x05,
    )
    assert format_cycle(trace) == EXPECTED


def test_state_dump_produced_by_real_cpu_execution():
    # Not an exact-string match against EXPECTED (that scenario is specific
    # to A.9's literal example) — confirms cpu.py feeds trace.py correct,
    # self-consistent values end-to-end for a SUB that is the 3rd instruction.
    from sim.cpu import CPU
    from sim.memory import Memory

    memory = Memory()
    memory.load_bytes([0x00, 0x00, 0x70])  # NOP, NOP, then SUB at 0x02
    cpu = CPU(memory)
    cpu.a, cpu.b = 0x0C, 0x05

    result = None
    for _ in range(3):  # NOP, NOP, SUB — one completed instruction each
        while True:
            result = cpu.step()
            if result.completed:
                break

    trace = result.trace
    assert trace.cycle_number == 3
    assert trace.mnemonic == "SUB"
    assert trace.pc_before == 0x02
    assert trace.pc_after == 0x03
    assert trace.alu_m == 0 and trace.alu_s == "0110" and trace.alu_cn == 0
    assert trace.a_after == 0x07 and trace.z == 0 and trace.c == 1
    dump = format_cycle(trace)
    assert dump.startswith("─── Ciclo 3 ───")
    assert "IR=0x70 (SUB)" in dump
    assert "RESULT  A=0x07   Z=0  C=1" in dump
