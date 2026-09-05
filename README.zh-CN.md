# md2pdf

把 Markdown 排成一份像样的 PDF,中文排版是第一优先级。([English](README.md))

```
md2pdf report.md
```

一条命令,Markdown 变成 A4 PDF,读起来像排过版的文档,而不是打印出来的网页:中日韩文字有合适的行距和两端对齐,西文走自己的字体,标题用对比明显的无衬线体,表格跨页时按行断开,所有字体子集内嵌,换任何一台机器打开都是同一个样子。

## 为什么又造一个 Markdown 转 PDF

市面上大多数转换器都是把 HTML 交给浏览器引擎打印。西文没问题,中文就散架:行距太紧、两端对齐拉出大空档、高一点的表格整块被推到下一页、屏幕上看到的字体和文件里嵌进去的不是同一套。macOS 上更麻烦,系统字体苹方的字形存在 Apple 的 [`hvgl` 表](https://developer.apple.com/fonts/TrueType-Reference-Manual/RM06/Chap6hvgl.html)里,没有第三方 PDF 引擎能读它。

md2pdf 走两条路绕开这些问题:

- **Typst 引擎**(默认,所有平台)。pandoc 把 Markdown 转成 [Typst](https://typst.app),再用一套为中西混排调过的模板编译成 PDF。快、文件小、结果稳定。
- **CoreText 引擎**(`--pingfang`,仅 macOS)。pandoc 把 Markdown 转成 HTML,一个小 WebKit 程序用系统苹方渲染,再按段落、列表项、表格行的边界切成 A4 页。这是唯一能把真苹方嵌进 PDF 的办法。

如果你不需要中文排版,[md-to-pdf](https://github.com/simonhaenisch/md-to-pdf) 或 [mdxport-cli](https://github.com/cosformula/mdxport-cli) 可能更合适。

## 安装

md2pdf 是一个没有 Python 依赖的 Python 包,运行时调用 PATH 上的 `pandoc` 和 `typst`。

```
brew install pandoc typst
uv tool install md2pdf-cjk
```

用 `pipx install md2pdf-cjk` 也一样;PyPI 上的包名是 [md2pdf-cjk](https://pypi.org/project/md2pdf-cjk/),命令名是 `md2pdf`。Typst 引擎要求 pandoc 3.1.3 或更新。

Linux 发行版仓库里的 pandoc 常常比 3.1.3 旧,建议从 [pandoc 的 releases](https://github.com/jgm/pandoc/releases) 拿 `.deb` 或 tarball;typst 从[它的 releases](https://github.com/typst/typst/releases) 下载,或 `cargo install --locked typst-cli`。Windows 用 `winget install JohnMacFarlane.Pandoc` 和 `winget install Typst.Typst`。

### 字体

Typst 引擎用系统里已经安装的字体。默认预设需要思源黑体,其余预设用 macOS 自带的字体,或者一条 `brew` 命令就能装上。

| 预设 | 中文字体 | 西文字体 | 安装 |
|---|---|---|---|
| `noto`(默认) | 思源黑体 Noto Sans CJK SC | Helvetica Neue | `brew install --cask font-noto-sans-cjk-sc` |
| `hiragino` | 冬青黑体 Hiragino Sans GB | Helvetica Neue | macOS 自带 |
| `songti` | 宋体 Songti SC | Libertinus Serif | macOS 自带;Libertinus 随 Typst 附带 |
| `wenkai` | 霞鹜文楷 LXGW WenKai | Libertinus Serif | `brew install --cask font-lxgw-wenkai` |
| `pingfang` | 苹方 PingFang SC(CoreText 引擎) | 苹方 | macOS 自带 |

Linux 上从发行版装思源黑体(Debian 和 Ubuntu 是 `fonts-noto-cjk`),其他已装的字体用 `--font "字体名"` 指定。缺少西文字体时 Typst 会自动替换并打印一条警告。

CoreText 引擎第一次使用时从源码编译渲染器,需要 Xcode Command Line Tools(`xcode-select --install`),编译结果缓存在 `~/.cache/md2pdf`。它通过 WebKit 渲染,需要一个已登录的图形会话:纯 SSH 或无头 CI 环境下不能用。

## 用法

```
md2pdf input.md [output.pdf]

md2pdf input.md --toc              # 文前加目录
md2pdf input.md --landscape        # A4 横向,放宽表格(Typst 引擎)
md2pdf input.md --lang en          # 英文断字与地区设置,目录标题为 Contents
md2pdf input.md --open             # 生成后打开

md2pdf input.md --serif            # 宋体正文,西文用 Libertinus Serif
md2pdf input.md --wenkai           # 霞鹜文楷正文
md2pdf input.md --hiragino         # 冬青黑体正文
md2pdf input.md --pingfang         # 系统苹方,走 CoreText 引擎(macOS)
md2pdf input.md --font "Sarasa UI SC"   # 任何已安装的中文字体
```

输出路径默认是输入文件名换成 `.pdf` 后缀。`--open` 用系统默认的 PDF 查看器打开。同时给了多个字体选项时,最后一个生效。

Markdown 方言是 pandoc 的,关闭了引文、开启了任务列表,所以表格、脚注、定义列表和 `- [x]` 都能用。YAML 头部设置标题区:

```markdown
---
title: 季度报告
subtitle: 2026 Q3
author: 张三
date: 2026-09-05
---
```

环境变量 `MD2PDF_FONT`、`MD2PDF_TEMPLATE`、`MD2PDF_MARGIN_PT` 分别改 `--font`、`--template`、`--margin` 的默认值。

## 自定义模板

`--template path/to/your.typ` 替换内置的 pandoc Typst 模板。可以从 [`src/md2pdf/templates/typst.typ`](src/md2pdf/templates/typst.typ) 改起;命令行在 pandoc 的标准变量之外还会传入 `mainfont`、`cjkfont`、`sansfont`、`cjksans`、`monofont`。

## 开发

```
git clone https://github.com/openwhale-labs/md2pdf
cd md2pdf
uv tool install -e .
uv run --with pytest pytest
```

需要 pandoc、typst 或 macOS 的测试在缺少对应工具时自动跳过。[`samples/sample.md`](samples/sample.md) 覆盖了模板处理的每一种元素。

## 许可证

MIT。Copyright (c) 2026 OpenWhale Labs。
