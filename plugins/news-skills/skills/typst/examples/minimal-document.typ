#set document(title: [Minimal Typst Document])
#set text(lang: "en", region: "US")
#set page(margin: (x: 30mm, y: 25mm), numbering: "1")
#set heading(numbering: "1.")
#set par(justify: true)

#title()

A minimal Typst document with semantic title metadata, language tagging,
page numbering, and cross-references.

= Introduction <intro>

This document is intentionally small but already uses semantic structure.
Refer back to @intro after adding more sections.

== Lists

- Prefer semantic markup.
- Style with `set` and `show` rules.
- Export with target-aware commands.

== Formula

#math.equation(
  block: true,
  alt: "x squared plus y squared equals z squared",
  $ x^2 + y^2 = z^2 $,
)
