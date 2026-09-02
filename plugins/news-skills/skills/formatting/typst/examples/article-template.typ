#let article-template(
  title: [Example Article],
  authors: (),
  abstract: [],
  draft: false,
  body,
) = {
  set document(title: title)
  set text(lang: "en", region: "US", font: "Libertinus Serif")
  set page(
    paper: "us-letter",
    margin: (x: 28mm, y: 24mm),
    columns: 2,
    numbering: "1",
    header: context {
      if counter(page).get().first() > 1 [
        #emph(title)
        #h(1fr)
        #counter(page).display("1")
      ]
    },
  )
  set par(justify: true)
  set heading(numbering: "1.")

  place(
    top + center,
    float: true,
    scope: "parent",
  )[
    #align(center)[
      #std.title()
      #if authors.len() > 0 {
        grid(
          columns: (1fr,) * authors.len(),
          gutter: 12pt,
          ..authors.map(author => [#author]),
        )
      }
      #if draft [*Draft version*]
    ]

    #if abstract != [] {
      block(above: 1em)[
        *Abstract*\
        #abstract
      ]
    }
  ]

  body
}

#show: article-template.with(
  title: [Official-docs-first Typst Article],
  authors: (
    [Ada Author\\Example University],
    [Bert Builder\\Example Lab],
  ),
  abstract: [
    This template demonstrates a title block above a two-column article body,
    contextual running headers, and semantic headings.
  ],
)

= Introduction

This is a two-column article skeleton.

= Method

Use this as a starting point for conference-style drafts.

= Results

The running header starts on page two and later.
