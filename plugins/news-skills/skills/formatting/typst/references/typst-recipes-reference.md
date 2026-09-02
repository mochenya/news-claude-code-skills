# Typst recipes reference

Use this file for reusable real-world patterns rather than first-principles reference.

## 1. Template function shell

Use a template function plus `show: template.with(...)` for reusable documents.

```typ
#let article-template(
  title: none,
  author: none,
  draft: false,
  body,
) = {
  set document(title: title)
  set text(lang: "en", region: "US")
  set page(margin: (x: 30mm, y: 25mm), numbering: "1")
  set par(justify: true)

  if title != none {
    align(center)[
      #title(title)
      #if author != none [#author]
      #if draft [*Draft*]
    ]
  }

  body
}

#show: article-template.with(
  title: [Example Article],
  author: [A. Author],
)
```

Use named parameters for the knobs users will change often. Keep document defaults inside the template, not scattered across the body.

## 2. Conditional header/footer with `context`

Use contextual page headers when content depends on current page or local document state.

```typ
#set page(header: context {
  if counter(page).get().first() > 1 [
    #emph([Running Header])
    #h(1fr)
    #counter(page).display("1")
  ]
})
```

Remember: `counter(page).get()` depends on context.

## 3. `context` + `counter` + `query` + `locate`

### Current counter value

```typ
#context counter(heading).get()
```

### Counter at another location

```typ
#context counter(heading).at(<intro>)
```

### Current location

```typ
#context here().page()
```

### Locate labeled content

```typ
#context locate(<target>).position()
```

### Query matching elements

```typ
#context query(heading.where(level: 1))
```

Guideline:
- if the result should vary by placement, keep both lookup and dependent formatting in the same contextual region
- expect compiler iterations for introspection-heavy documents

## 4. Table + figure + reference pattern

Use this when a table needs a caption and cross-reference.

```typ
#figure(
  kind: table,
  caption: [Performance by variant],
  table(
    columns: (2fr, 1fr, 1fr),
    table.header[*Variant*][*Latency*][*Notes*],
    [Baseline], [120 ms], [Control],
    [Optimized], [85 ms], [Recommended],
    table.footer([Best result], [85 ms], [Keep]),
  ),
) <perf-table>

See @perf-table for the comparison.
```

This gives semantics, captioning, and references in one pattern.

## 5. CLI-driven template configuration with `sys.inputs`

Expose stable build knobs through the CLI instead of editing source per run.

```typ
#let report-title = if "title" in sys.inputs { sys.inputs.title } else { "Untitled Report" }
#let audience = if "audience" in sys.inputs { sys.inputs.audience } else { "internal" }
#let draft = if "draft" in sys.inputs { sys.inputs.draft == "true" } else { false }
```

Matching command:

```bash
typst compile \
  --input title="Q1 Revenue Report" \
  --input audience=board \
  --input draft=false \
  report.typ report.pdf
```

Keep command examples and Typst keys identical.

## 6. HTML-specific branching

Use `target()` and `html.elem(...)` in templates/show rules when HTML output needs different structure.

```typ
#show heading: it => {
  if target() == "html" {
    html.elem("section")[
      #html.elem("h2")[#it.body]
    ]
  } else {
    it
  }
}
```

Use sparingly. Prefer content that stays export-agnostic unless a structural HTML difference is necessary.

## 7. Bundle multi-document pattern

Use `document(...)` for each output document and `asset(...)` for raw files.

```typ
#let post = [
  = Blog Post
  Shared content.
]

#document("index.html", title: [Home])[
  #title()
  #link(<post-html>)[Read the post]
]

#document("post.html", title: [Post])[#post] <post-html>
#document("post.pdf", title: [Post])[#post] <post-pdf>
```

Key caution:
- labels, counters, states, and query results are bundle-global
- heading numbering continues across documents unless reset or designed around

## 8. Version-compatibility / polyfill pattern

When behavior differs across Typst versions or experimental features, keep compatibility logic explicit.

```typ
#let maybe-tiling = if "tiling" in std { tiling } else { pattern }
```

Also consider `sys.version` for version-aware branches. Prefer simple compatibility shims over sprawling conditionals.

## 9. Accessible figure and decorative content split

```typ
#pdf.artifact[
  #place(center, dx: 0pt, dy: 0pt, circle(radius: 40pt, fill: luma(240)))
]

#figure(
  alt: "Five-point star with blue outline",
  caption: [Accessible diagram],
  curve(
    stroke: blue,
    curve.move((25pt, 0pt)),
    curve.line((10pt, 50pt)),
    curve.line((50pt, 20pt)),
    curve.line((0pt, 20pt)),
    curve.line((40pt, 50pt)),
    curve.close(),
  ),
)
```

Keep decoration as artifacts and meaningful visuals in semantic figures.

## 10. Recommended response habits for Claude

When solving a real Typst task:
- start from the nearest example in `examples/`
- adapt semantics before styling
- check whether `context` is required before writing introspection logic
- mention feature flags whenever HTML/bundle/a11y-extras behavior is involved
- mention that PNG/SVG are visual exports, not accessibility targets
