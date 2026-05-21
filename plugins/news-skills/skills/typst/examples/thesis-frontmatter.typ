#set document(title: [Sample Thesis])
#set text(lang: "en", region: "US")
#set page(
  paper: "a4",
  margin: (inside: 36mm, outside: 24mm, top: 28mm, bottom: 30mm),
)

#align(center + horizon)[
  #title()

  #block(above: 1.5cm)[
    A thesis submitted in partial fulfillment of the requirements for the degree
    of Master of Science.
  ]

  #block(above: 1.5cm)[
    *Author*\
    Jane Example
  ]

  #block(above: 1cm)[
    *Department*\
    Department of Example Studies
  ]

  #block(above: 1cm)[
    *Supervisor*\
    Prof. Alex Advisor
  ]

  #block(above: 2cm)[May 2026]
]

#pagebreak()
#counter(page).update(1)
#set page(numbering: "i")

= Abstract

This file is a frontmatter starting point. After frontmatter, switch to the main
body template and reset numbering as required by the institution.
