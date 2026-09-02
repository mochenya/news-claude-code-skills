#let site-title = if "title" in sys.inputs { sys.inputs.title } else { "Example Site" }
#let article = [
  = Shared Article
  This content is reused between bundle outputs.
]

#if target() == "html" {
  #html.elem("nav")[
    #html.elem("a", href: "index.html")[Home]
    #html.elem("span")[ | ]
    #html.elem("a", href: "article.html")[Article]
  ]
}

#document("index.html", title: [#site-title])[
  #title(site-title)
  Welcome to the site.

  #link(<article-html>)[Read the article online]
  #linebreak()
  #link(<article-pdf>)[Download the PDF version]
]

#document("article.html", title: [Article])[
  #title[Article]
  #article
] <article-html>

#document("article.pdf", title: [Article PDF])[
  #title[Article PDF]
  #article
] <article-pdf>

#asset(
  "data/site.json",
  json.encode((title: site-title, outputs: ("index.html", "article.html", "article.pdf"))),
)
