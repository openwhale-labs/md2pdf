// md2pdf: pandoc -> Typst template, tuned for CJK text.
//
// Variables the CLI always passes:
//   mainfont / cjkfont  body text, Latin family then CJK fallback
//   sansfont / cjksans  headings, sans-serif for contrast
//   monofont            code, with cjkfont as the CJK fallback
// Standard pandoc variables are honoured as well:
//   title subtitle author date toc toc-depth section-numbering papersize fontsize lang region

#let conf(doc) = {
  set document(title: "$title-meta$")

  set page(
    paper: "$if(papersize)$$papersize$$else$a4$endif$",
    flipped: $if(landscape)$true$else$false$endif$,
    margin: (x: 2.4cm, top: 2.4cm, bottom: 2.6cm),
    numbering: "1",
    number-align: center,
  )

  // Body: Latin font with CJK fallback, CJK-friendly leading, justified.
  set text(
    font: ("$mainfont$", "$cjkfont$"),
    size: $if(fontsize)$$fontsize$$else$11pt$endif$,
    lang: "$if(lang)$$lang$$else$zh$endif$",
$if(region)$
    region: "$region$",
$endif$
  )
  set par(justify: true, leading: 0.92em, spacing: 1.3em, first-line-indent: 0pt)

  // Headings: sans-serif, clear size steps.
  show heading: set text(font: ("$sansfont$", "$cjksans$"))
  set heading(numbering: $if(section-numbering)$"$section-numbering$"$else$none$endif$)
  show heading: it => block(above: 1.5em, below: 0.85em, it)
  show heading.where(level: 1): set text(size: 1.6em)
  show heading.where(level: 2): set text(size: 1.3em)
  show heading.where(level: 3): set text(size: 1.12em)

  show link: set text(fill: rgb("#1a5fb4"))

  // Inline code.
  show raw.where(block: false): it => box(
    fill: rgb("#eff1f4"), inset: (x: 3pt, y: 0pt), outset: (y: 3pt), radius: 2.5pt,
    text(font: ("$monofont$", "$cjkfont$"), size: 0.92em, it),
  )

  // Code blocks.
  show raw.where(block: true): it => block(
    fill: rgb("#f6f8fa"), inset: 10pt, radius: 6pt, width: 100%, breakable: true,
    stroke: 0.5pt + rgb("#e2e6ea"),
    text(font: ("$monofont$", "$cjkfont$"), size: 9.3pt, it),
  )

  // Block quotes.
  show quote.where(block: true): it => block(
    width: 100%, inset: (left: 1em, top: 0.2em, bottom: 0.2em),
    stroke: (left: 3pt + rgb("#d0d7de")),
    text(fill: rgb("#57606a"), it.body),
  )

  // Tables: bold header row, light borders.
  set table(inset: 7pt, stroke: 0.5pt + rgb("#d0d7de"))
  show table.cell.where(y: 0): set text(weight: "bold")
  // pandoc wraps tables in figures, which cannot break across pages by default;
  // a tall table would otherwise be pushed whole onto the next page.
  show figure: set block(breakable: true)
  // pandoc emits align:(auto, ...) inside an outer align(center), which centres
  // long cell text; restore left alignment inside tables.
  show table: set align(left + top)
  // Justification in narrow columns stretches the spacing badly.
  show table.cell: set par(justify: false, leading: 0.72em)

  // Task-list boxes: drawn, not glyphs, since CJK fonts often lack U+2610.
  let checkbox(checked) = box(
    width: 0.85em, height: 0.85em, baseline: 0.1em, radius: 1.5pt,
    stroke: 0.6pt + rgb("#57606a"),
    fill: if checked { rgb("#57606a") } else { none },
    if checked { align(center + horizon, text(fill: white, size: 0.7em, weight: "bold")[✓]) },
  )
  show "☐": checkbox(false)
  show "☒": checkbox(true)

  // Title block.
$if(title)$
  block(width: 100%, breakable: false)[
    #text(font: ("$sansfont$", "$cjksans$"), size: 2em, weight: "bold")[$title$]
$if(subtitle)$
    #linebreak()
    #v(0.2em)
    #text(font: ("$sansfont$", "$cjksans$"), size: 1.2em, fill: rgb("#57606a"))[$subtitle$]
$endif$
  ]
  v(0.3em)
  text(fill: rgb("#57606a"), size: 0.95em)[$for(author)$$author$$sep$ · $endfor$$if(author)$$if(date)$ · $endif$$endif$$date$]
  v(0.5em)
  line(length: 100%, stroke: 0.5pt + rgb("#d0d7de"))
  v(0.7em)
$endif$

$if(toc)$
  outline(title: "$if(toc-title)$$toc-title$$else$Contents$endif$", depth: $if(toc-depth)$$toc-depth$$else$3$endif$, indent: auto)
  pagebreak()
$endif$

  doc
}

$if(highlighting-definitions)$
$highlighting-definitions$
$endif$

// Helpers pandoc's Typst body expects (horizontal rules, definition lists,
// caption placement); a custom template has to provide them.
#let horizontalrule = block(above: 1.2em, below: 1.2em, align(center, line(length: 100%, stroke: 0.5pt + rgb("#d0d7de"))))
#show terms.item: it => block(breakable: false)[
  #text(weight: "bold")[#it.term]
  #block(inset: (left: 1.5em, top: -0.4em))[#it.description]
]
#show figure.where(kind: table): set figure.caption(position: top)
#show figure.where(kind: image): set figure.caption(position: bottom)

#show: conf

$body$
