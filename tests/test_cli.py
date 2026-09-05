"""Smoke tests. The Typst test needs pandoc and typst on PATH; the CoreText test
needs macOS with swiftc. Both are skipped, not failed, when the tools are absent.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest

from md2pdf import cli

SAMPLE = Path(__file__).resolve().parent.parent / "samples" / "sample.md"


def test_parser_font_shortcuts():
    assert cli.build_parser().parse_args(["a.md", "--serif"]).font == "songti"
    assert cli.build_parser().parse_args(["a.md", "--pingfang"]).font == "pingfang"
    assert cli.build_parser().parse_args(["a.md", "--font", "Sarasa UI SC"]).font == (
        "Sarasa UI SC"
    )


def test_toc_title_and_region_follow_language():
    assert cli.toc_title("zh") == "目录"
    assert cli.toc_title("zh-CN") == "目录"
    assert cli.toc_title("en") == "Contents"
    assert cli.region("zh") == "CN"
    assert cli.region("en") is None


def test_margin_env_must_be_numeric(monkeypatch):
    monkeypatch.setenv("MD2PDF_MARGIN_PT", "wide")
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["a.md"])


def test_missing_input(tmp_path, capsys):
    assert cli.main([str(tmp_path / "nope.md")]) == 1
    assert "file not found" in capsys.readouterr().err


def test_refuses_to_overwrite_input(tmp_path, capsys):
    src = tmp_path / "doc.md"
    src.write_text("# hi\n")
    assert cli.main([str(src), str(src)]) == 2
    assert "output must end in .pdf" in capsys.readouterr().err
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF")
    assert cli.main([str(pdf), str(pdf)]) == 2
    assert "overwrite the input" in capsys.readouterr().err
    link = tmp_path / "link.pdf"
    os.link(pdf, link)
    assert cli.main([str(pdf), str(link)]) == 2
    assert "overwrite the input" in capsys.readouterr().err


def test_margin_range(tmp_path, capsys):
    src = tmp_path / "doc.md"
    src.write_text("# hi\n")
    assert cli.main([str(src), "--margin", "400"]) == 2
    assert "--margin" in capsys.readouterr().err


@pytest.mark.skipif(
    not (shutil.which("pandoc") and shutil.which("typst")),
    reason="pandoc and typst required",
)
def test_typst_engine(tmp_path):
    out = tmp_path / "sample.pdf"
    assert cli.main([str(SAMPLE), str(out), "--toc"]) == 0
    assert out.read_bytes().startswith(b"%PDF")
    assert out.stat().st_size > 10_000


@pytest.mark.skipif(
    sys.platform != "darwin"
    or not (shutil.which("pandoc") and shutil.which("swiftc"))
    or "SSH_CONNECTION" in os.environ,
    reason="macOS with pandoc, swiftc and a graphical session required",
)
def test_coretext_engine(tmp_path):
    out = tmp_path / "sample-pingfang.pdf"
    assert cli.main([str(SAMPLE), str(out), "--font", "PingFang SC"]) == 0
    data = out.read_bytes()
    assert data.startswith(b"%PDF")
    assert b"PingFang" in data
