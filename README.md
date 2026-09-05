# md2pdf

Markdown to a well-typeset PDF, with CJK text as a first-class citizen. ([中文说明](README.zh-CN.md))

```
md2pdf report.md
```

One command turns a Markdown file into an A4 PDF that reads like a typeset document, not a printed web page: Chinese, Japanese and Korean text set with proper leading and justification, Latin text in its own font, headings in a contrasting sans-serif, tables that break cleanly across pages, and every font subset-embedded so the file looks the same on any machine.

## Why another Markdown to PDF tool

Most converters print HTML through a browser engine. That works for Latin text and falls apart for CJK: line spacing is too tight, justification opens rivers, tables get pushed whole onto the next page, and the fonts you see on screen are not the fonts that end up in the file. On macOS the system font, PingFang, cannot be embedded by any third-party engine at all, because its glyphs are stored in Apple's [`hvgl` table](https://developer.apple.com/fonts/TrueType-Reference-Manual/RM06/Chap6hvgl.html), which no third-party PDF engine reads.

md2pdf takes two routes around this:

- **Typst engine** (default, every platform). pandoc converts the Markdown to [Typst](https://typst.app), which compiles it with a template tuned for mixed-script text. Fast, small files, deterministic.
- **CoreText engine** (`--pingfang`, macOS only). pandoc converts the Markdown to HTML, and a small WebKit program renders it with the system PingFang font and cuts it into A4 pages at paragraph, list-item and table-row boundaries. This is the only way to get real PingFang into a PDF.

If you do not need CJK typesetting, [md-to-pdf](https://github.com/simonhaenisch/md-to-pdf) or [mdxport-cli](https://github.com/cosformula/mdxport-cli) may fit you better.

## Install

md2pdf is a Python package with no Python dependencies. It calls `pandoc` and `typst` on your PATH.

```
brew install pandoc typst
uv tool install md2pdf-cjk
```

`pipx install md2pdf-cjk` works the same way; the package is [md2pdf-cjk on PyPI](https://pypi.org/project/md2pdf-cjk/) and the command is `md2pdf`. pandoc 3.1.3 or newer is required for the Typst engine.

On Linux, distribution packages of pandoc are often older than 3.1.3; take the `.deb` or tarball from [pandoc's releases](https://github.com/jgm/pandoc/releases) instead. typst comes from [its releases](https://github.com/typst/typst/releases) or `cargo install --locked typst-cli`. On Windows, `winget install JohnMacFarlane.Pandoc` and `winget install Typst.Typst`.

### Fonts

The Typst engine uses fonts installed on your system. The default preset needs Noto Sans CJK; the others use fonts that ship with macOS or are one `brew` away.

| Preset | CJK font | Latin font | Install |
|---|---|---|---|
| `noto` (default) | Noto Sans CJK SC | Helvetica Neue | `brew install --cask font-noto-sans-cjk-sc` |
| `hiragino` | Hiragino Sans GB | Helvetica Neue | ships with macOS |
| `songti` | Songti SC | Libertinus Serif | ships with macOS; Libertinus comes with Typst |
| `wenkai` | LXGW WenKai | Libertinus Serif | `brew install --cask font-lxgw-wenkai` |
| `pingfang` | PingFang SC (CoreText engine) | PingFang SC | ships with macOS |

On Linux, install Noto Sans CJK from your distribution (`fonts-noto-cjk` on Debian and Ubuntu) and pass any other family you have with `--font "Family Name"`. Typst substitutes a fallback for missing Latin families and prints a warning.

The CoreText engine compiles its renderer from source on first use, which needs the Xcode Command Line Tools (`xcode-select --install`). The binary is cached in `~/.cache/md2pdf`. It renders through WebKit, so it needs a logged-in graphical session: it does not work over plain SSH or in headless CI.

## Usage

```
md2pdf input.md [output.pdf]

md2pdf input.md --toc              # table of contents first
md2pdf input.md --landscape        # A4 landscape, for wide tables (Typst engine)
md2pdf input.md --lang en          # English hyphenation, region and "Contents" heading
md2pdf input.md --open             # open the PDF when done

md2pdf input.md --serif            # Songti body, Libertinus Serif for Latin
md2pdf input.md --wenkai           # LXGW WenKai body
md2pdf input.md --hiragino         # Hiragino Sans GB body
md2pdf input.md --pingfang         # system PingFang via the CoreText engine (macOS)
md2pdf input.md --font "Sarasa UI SC"   # any installed CJK family
```

The output path defaults to the input name with a `.pdf` extension. `--open` uses the platform's default PDF viewer. When several font options are given, the last one wins.

pandoc's Markdown dialect is used with citations off and task lists on, so tables, footnotes, definition lists and `- [x]` items all work. YAML front matter sets the title block:

```markdown
---
title: Quarterly Report
subtitle: 2026 Q3
author: Jane Doe
date: 2026-09-05
---
```

Environment variables `MD2PDF_FONT`, `MD2PDF_TEMPLATE` and `MD2PDF_MARGIN_PT` change the defaults for `--font`, `--template` and `--margin`.

## Customising the template

`--template path/to/your.typ` replaces the bundled pandoc Typst template. Start from [`src/md2pdf/templates/typst.typ`](src/md2pdf/templates/typst.typ); the CLI passes `mainfont`, `cjkfont`, `sansfont`, `cjksans` and `monofont` variables on top of pandoc's standard ones.

## Development

```
git clone https://github.com/openwhale-labs/md2pdf
cd md2pdf
uv tool install -e .
uv run --with pytest pytest
```

Tests that need pandoc, typst or macOS are skipped when those are absent. [`samples/sample.md`](samples/sample.md) exercises every element the template styles.

## License

MIT. Copyright (c) 2026 OpenWhale Labs.
