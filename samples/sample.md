---
title: 排版示例
subtitle: A bilingual sample for md2pdf
author: OpenWhale Labs
date: 2026-09-05
---

# 中文段落

这是一段中文正文。md2pdf 把 Markdown 交给 pandoc 转成 Typst,再由 Typst 排成 PDF:两端对齐、行距按中文调过、字体子集内嵌,换一台机器打开也是同样的样子。混排的英文 like this 和数字 3.14 走西文字体,汉字走中文字体,逐字回退。

行内代码 `pandoc --pdf-engine=typst` 和**加粗**、*斜体*、[链接](https://github.com/openwhale-labs/md2pdf) 都按常规 Markdown 处理。

## English paragraph

The same template handles Latin text with a sans-serif body, sensible heading steps and a light table style. Long lines justify without the rivers you get from naive CJK justification, because the leading and spacing are set for mixed-script text.

## 表格

| 引擎 | 平台 | 字体来源 | 分页方式 |
|---|---|---|---|
| Typst | macOS、Linux、Windows | 系统已装的开源字体 | Typst 排版 |
| CoreText | 仅 macOS | 系统苹方 PingFang SC | 按元素边界切 A4 |

## 代码块

```python
def greet(name: str) -> str:
    return f"你好,{name}"
```

## 引用与列表

> 引用块用左侧竖线和灰色文字区分,跨页时可以断开。

- 无序列表第一项
- 第二项带 `代码`
  - 嵌套一级

1. 有序列表
2. 第二项

- [x] 已完成的任务
- [ ] 未完成的任务

---

术语
: 定义列表由 pandoc 的 Markdown 方言支持,模板里单独排版。
