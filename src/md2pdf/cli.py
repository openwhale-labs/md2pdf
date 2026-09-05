"""md2pdf: Markdown to a well-typeset PDF, with CJK text as a first-class citizen.

Two rendering engines:

* Typst (default, all platforms): pandoc converts Markdown to Typst, which
  compiles it to PDF with a CJK-tuned template. Fonts are subset-embedded.
* CoreText (``--font pingfang``, macOS only): pandoc converts Markdown to HTML,
  a small WebKit program renders it with the system PingFang font and cuts it
  into A4 pages. This is the only way to embed PingFang: its glyphs use Apple's
  private ``hvgl`` outline format, which no third-party PDF engine can read.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
TYPST_TEMPLATE = PACKAGE_DIR / "templates" / "typst.typ"
CORETEXT_STYLE = PACKAGE_DIR / "templates" / "coretext.html"
CORETEXT_SOURCE = PACKAGE_DIR / "native" / "htmlpdf.swift"

PANDOC_FROM = "markdown-citations+task_lists"


@dataclass(frozen=True)
class FontPreset:
    """Font families handed to the Typst template.

    ``main``/``cjk`` set the body text (Latin first, CJK fallback);
    ``sans``/``cjk_sans`` set headings. Typst falls back through the list per glyph.
    """

    main: str
    cjk: str
    sans: str
    cjk_sans: str


LATIN_SANS = "Helvetica Neue"
LATIN_SERIF = "Libertinus Serif"
MONO_FONT = "Menlo"

PRESETS: dict[str, FontPreset] = {
    "noto": FontPreset(LATIN_SANS, "Noto Sans CJK SC", LATIN_SANS, "Noto Sans CJK SC"),
    "hiragino": FontPreset(
        LATIN_SANS, "Hiragino Sans GB", LATIN_SANS, "Hiragino Sans GB"
    ),
    "songti": FontPreset(LATIN_SERIF, "Songti SC", LATIN_SANS, "Hiragino Sans GB"),
    "wenkai": FontPreset(LATIN_SERIF, "LXGW WenKai", LATIN_SANS, "Hiragino Sans GB"),
}
CORETEXT_FONT = "pingfang"
CORETEXT_ALIASES = {"pingfang", "pingfangsc", "pingfang sc", "苹方"}
DEFAULT_FONT = "noto"
PANDOC_HINT = "Install pandoc 3.1.3 or newer (macOS: brew install pandoc)."
TYPST_HINT = (
    "Install typst (macOS: brew install typst; "
    "elsewhere: cargo install --locked typst-cli)."
)
A4_WIDTH_PT = 595.28


class Md2PdfError(Exception):
    """A user-facing failure: message is printed without a traceback."""


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="md2pdf",
        description="Markdown to a well-typeset PDF, CJK-aware.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "font presets:\n"
            "  noto      Noto Sans CJK SC (default)\n"
            "  hiragino  Hiragino Sans GB (ships with macOS)\n"
            "  songti    Songti SC body with Libertinus Serif for Latin\n"
            "  wenkai    LXGW WenKai body with Libertinus Serif for Latin\n"
            "  pingfang  system PingFang SC via the CoreText engine (macOS only)\n"
            "  <family>  any other value is used as the CJK family name\n"
        ),
    )
    ap.add_argument("input", help="Markdown file")
    ap.add_argument("output", nargs="?", help="PDF path (default: input with .pdf)")
    ap.add_argument(
        "--font",
        default=os.environ.get("MD2PDF_FONT", DEFAULT_FONT),
        help="font preset or CJK family name (default: %(default)s)",
    )
    shortcuts = ap.add_argument_group("font shortcuts")
    for flags, preset in (
        (("--sans", "--noto"), "noto"),
        (("--hiragino",), "hiragino"),
        (("--serif", "--songti"), "songti"),
        (("--wenkai",), "wenkai"),
        (("--pingfang",), CORETEXT_FONT),
    ):
        shortcuts.add_argument(
            *flags,
            dest="font",
            action="store_const",
            const=preset,
            help=f"same as --font {preset}",
        )
    ap.add_argument(
        "--lang",
        default="zh",
        help="document language for hyphenation and the contents title "
        "(default: %(default)s)",
    )
    ap.add_argument("--toc", action="store_true", help="prepend a table of contents")
    ap.add_argument(
        "--landscape", action="store_true", help="A4 landscape (Typst engine)"
    )
    ap.add_argument(
        "--margin",
        type=float,
        default=os.environ.get("MD2PDF_MARGIN_PT", "56"),
        help="page margin in points (CoreText engine, default: %(default)s)",
    )
    ap.add_argument(
        "--template",
        type=Path,
        default=Path(os.environ["MD2PDF_TEMPLATE"])
        if "MD2PDF_TEMPLATE" in os.environ
        else TYPST_TEMPLATE,
        help="pandoc Typst template (default: the bundled one)",
    )
    ap.add_argument("--open", action="store_true", help="open the PDF when done")
    return ap


def require(command: str, hint: str) -> str:
    path = shutil.which(command)
    if path is None:
        raise Md2PdfError(f"{command} not found on PATH. {hint}")
    return path


def toc_title(lang: str) -> str:
    return "目录" if lang.startswith("zh") else "Contents"


def region(lang: str) -> str | None:
    """Typst region code for the document language; None leaves it unset."""
    return "CN" if lang.startswith("zh") else None


def open_file(path: Path) -> None:
    if sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
    elif sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
    elif shutil.which("xdg-open"):
        subprocess.run(["xdg-open", str(path)], check=False)
    else:
        print(f"md2pdf: no opener found for {path}", file=sys.stderr)


def highlight_off_flag() -> str:
    """pandoc 3.8 renamed --no-highlight and warns on the old spelling."""
    version = subprocess.run(
        ["pandoc", "--version"], capture_output=True, text=True, check=True
    ).stdout.split()[1]
    major, minor = (int(part) for part in version.split(".")[:2])
    return (
        "--syntax-highlighting=none" if (major, minor) >= (3, 8) else "--no-highlight"
    )


def render_typst(
    src: Path,
    out: Path,
    font: str,
    template: Path,
    lang: str,
    toc: bool,
    landscape: bool,
) -> None:
    require("pandoc", PANDOC_HINT)
    require("typst", TYPST_HINT)
    if not template.is_file():
        raise Md2PdfError(f"template not found: {template}")
    preset = PRESETS.get(font) or FontPreset(LATIN_SANS, font, LATIN_SANS, font)
    args = [
        "pandoc",
        str(src),
        "-o",
        str(out),
        "--quiet",
        "--pdf-engine=typst",
        f"--template={template}",
        f"--from={PANDOC_FROM}",
        highlight_off_flag(),
        f"--resource-path={src.parent}",
        "-V",
        f"mainfont={preset.main}",
        "-V",
        f"cjkfont={preset.cjk}",
        "-V",
        f"sansfont={preset.sans}",
        "-V",
        f"cjksans={preset.cjk_sans}",
        "-V",
        f"monofont={MONO_FONT}",
        "-M",
        f"lang={lang}",
    ]
    if region(lang):
        args += ["-V", f"region={region(lang)}"]
    if toc:
        args += ["--toc", "--toc-depth=3", "-V", f"toc-title={toc_title(lang)}"]
    if landscape:
        args += ["-V", "landscape=true"]
    subprocess.run(args, check=True)


def coretext_binary() -> Path:
    """Return the compiled WebKit renderer, building it from source on first use."""
    if sys.platform != "darwin":
        raise Md2PdfError("the CoreText engine (--font pingfang) requires macOS")
    if not CORETEXT_SOURCE.is_file():
        raise Md2PdfError(f"renderer source missing: {CORETEXT_SOURCE}")
    source = CORETEXT_SOURCE.read_bytes()
    xdg = os.environ.get("XDG_CACHE_HOME", "")
    cache_root = Path(xdg) if os.path.isabs(xdg) else Path.home() / ".cache"
    cache = cache_root / "md2pdf"
    # One binary per source revision, so an upgrade never runs a stale renderer.
    binary = cache / f"htmlpdf-{hashlib.sha256(source).hexdigest()[:12]}"
    if binary.is_file():
        return binary
    require("swiftc", "Install the Xcode Command Line Tools: xcode-select --install")
    cache.mkdir(parents=True, exist_ok=True)
    print("compiling the CoreText renderer (first run only)...", file=sys.stderr)
    subprocess.run(
        ["swiftc", "-O", str(CORETEXT_SOURCE), "-o", str(binary)], check=True
    )
    return binary


def render_coretext(src: Path, out: Path, margin: float, lang: str, toc: bool) -> None:
    require("pandoc", PANDOC_HINT)
    binary = coretext_binary()
    with tempfile.TemporaryDirectory(prefix="md2pdf-") as tmp:
        html = Path(tmp) / "document.html"
        args = [
            "pandoc",
            str(src),
            "-s",
            "--quiet",
            "--embed-resources",
            "--metadata",
            f"lang={lang}",
            f"--from={PANDOC_FROM}",
            f"--include-in-header={CORETEXT_STYLE}",
            f"--resource-path={src.parent}",
            "-o",
            str(html),
        ]
        if toc:
            args += ["--toc", "-V", f"toc-title={toc_title(lang)}"]
        subprocess.run(args, check=True)
        subprocess.run([str(binary), str(html), str(out), str(margin)], check=True)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    src = Path(args.input)
    if not src.is_file():
        print(f"md2pdf: file not found: {src}", file=sys.stderr)
        return 1
    out = Path(args.output) if args.output else src.with_suffix(".pdf")
    if out.suffix.lower() != ".pdf":
        print(f"md2pdf: output must end in .pdf: {out}", file=sys.stderr)
        return 2
    if out.exists() and out.samefile(src):
        print(f"md2pdf: output would overwrite the input: {out}", file=sys.stderr)
        return 2
    if not (0 <= args.margin < A4_WIDTH_PT / 2):
        print(
            f"md2pdf: --margin must be between 0 and {A4_WIDTH_PT / 2:.0f} points",
            file=sys.stderr,
        )
        return 2
    if args.font.strip().lower() in CORETEXT_ALIASES:
        args.font = CORETEXT_FONT
    try:
        if args.font == CORETEXT_FONT:
            render_coretext(src, out, args.margin, args.lang, args.toc)
            label = "PingFang SC, CoreText engine"
        else:
            render_typst(
                src,
                out,
                args.font,
                args.template,
                args.lang,
                args.toc,
                args.landscape,
            )
            label = f"{args.font}, Typst engine"
    except Md2PdfError as exc:
        print(f"md2pdf: {exc}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        print(
            f"md2pdf: {exc.cmd[0]} exited with status {exc.returncode}", file=sys.stderr
        )
        return exc.returncode
    print(f"wrote {out} ({label})")
    if args.open:
        open_file(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
