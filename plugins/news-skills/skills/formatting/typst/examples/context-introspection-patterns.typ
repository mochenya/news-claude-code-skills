#set document(title: [Context and Introspection Patterns])
#set text(lang: "en", region: "US")
#set page(
  margin: (x: 28mm, y: 24mm),
  numbering: "1",
  header: context {
    let current = query(heading.where(level: 1))
      .filter(h => counter(page).at(h.location()) == counter(page).get())
    if counter(page).get().first() > 1 and current.len() > 0 [
      #current.last().body
      #h(1fr)
      #counter(page).display("1")
    ]
  },
)
#set heading(numbering: "1.")

#title[Context and Introspection Patterns]

#context [Current page counter: #counter(page).get()]

= Introduction <intro>
#lorem(90)

= Background <back>
#lorem(110)

#context [
  Current heading counter: #counter(heading).get()\
  Heading counter at intro: #counter(heading).at(<intro>)\
  Background location: #locate(<back>).position()
]

#pagebreak()

= Queried headings

#context {
  let heads = query(heading.where(level: 1))
  [There are #heads.len() first-level headings in this document.]
}
