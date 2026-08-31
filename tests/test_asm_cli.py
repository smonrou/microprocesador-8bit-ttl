"""CLI: python -m asm programa.asm"""

import pytest

from asm.__main__ import main

GOOD_SOURCE = "LDI A,#5\nLDI B,#7\nADD\nOUT\nHLT\n"
BAD_SOURCE = "LDX 5\nLDA 300\n"


def write_source(tmp_path, text, name="prog.asm"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_writes_three_artifacts(tmp_path):
    source = write_source(tmp_path, GOOD_SOURCE)
    assert main([str(source)]) == 0

    assert (tmp_path / "prog.bin").exists()
    assert (tmp_path / "prog.lst").exists()
    assert (tmp_path / "prog.load").exists()


def test_binary_artifact_is_256_bytes(tmp_path):
    source = write_source(tmp_path, GOOD_SOURCE)
    main([str(source)])
    assert len((tmp_path / "prog.bin").read_bytes()) == 256


def test_output_dir_flag(tmp_path):
    source = write_source(tmp_path, GOOD_SOURCE)
    out = tmp_path / "build"
    assert main([str(source), "-o", str(out)]) == 0
    assert (out / "prog.bin").exists()


def test_listing_only_writes_nothing(tmp_path, capsys):
    source = write_source(tmp_path, GOOD_SOURCE)
    assert main([str(source), "--listing-only"]) == 0

    assert not (tmp_path / "prog.bin").exists()
    assert "TABLA DE SÍMBOLOS" in capsys.readouterr().out


def test_run_flag_executes_on_simulator(tmp_path, capsys):
    source = write_source(tmp_path, GOOD_SOURCE)
    assert main([str(source), "--run"]) == 0
    assert "[12]" in capsys.readouterr().out   # 5 + 7 = 12


def test_bad_source_exits_1_with_errors_on_stderr(tmp_path, capsys):
    source = write_source(tmp_path, BAD_SOURCE)
    assert main([str(source)]) == 1

    stderr = capsys.readouterr().err
    assert "línea 1" in stderr and "línea 2" in stderr


def test_bad_source_writes_no_artifacts(tmp_path):
    source = write_source(tmp_path, BAD_SOURCE)
    main([str(source)])
    assert not (tmp_path / "prog.bin").exists()


def test_missing_file_exits_1(tmp_path, capsys):
    assert main([str(tmp_path / "noexiste.asm")]) == 1
    assert "no se pudo leer" in capsys.readouterr().err


def test_warnings_go_to_stderr(tmp_path, capsys):
    source = write_source(tmp_path, ".ORG 0x10\nHLT\n")
    assert main([str(source)]) == 0
    assert "aviso:" in capsys.readouterr().err
