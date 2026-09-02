#let report-title = if "title" in sys.inputs { sys.inputs.title } else { "Quarterly Report" }
#let report-subtitle = if "subtitle" in sys.inputs { sys.inputs.subtitle } else { "Prepared with Typst" }
#let draft = if "draft" in sys.inputs { sys.inputs.draft == "true" } else { false }

#set document(title: [#report-title])
#set text(lang: "en", region: "US", font: "Libertinus Serif")
#set page(
  paper: "a4",
  margin: (inside: 32mm, outside: 24mm, top: 24mm, bottom: 28mm),
  numbering: "1 of 1",
  header: context {
    if counter(page).get().first() > 1 [
      #report-title
      #h(1fr)
      #counter(page).display("1")
    ]
  },
)
#set heading(numbering: "1.")
#set par(justify: true)

#align(center)[
  #title(report-title)
  #text(size: 0.95em, fill: luma(70%))[#report-subtitle]
  #if draft [#block(above: 0.8em)[*Draft*]]
]

= Executive Summary

This report skeleton is driven by CLI inputs and book-style inside/outside
margins.

= Findings

- Keep metadata and language explicit.
- Use contextual headers for running information.
- Expose build variants through `sys.inputs`.

= Appendix

Compile with a command that matches the keys in `sys.inputs`.
