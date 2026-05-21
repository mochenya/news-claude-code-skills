# Typst layout reference

Use this file for page setup, layout containers, tables, figures, and common page-level composition.

## Page setup

Prefer a single top-level `set page(...)` near the start of the document or inside a template.

Important page controls:
- `paper`, `width`, `height`
- `margin`
- `header`, `footer`
- `numbering`, `number-align`
- `columns`
- `binding`
- `header-ascent`, `footer-descent`
- `fill` for page background

### Margin patterns

- Use one length for uniform margins.
- Use a dictionary for asymmetric margins.
- Use `x` / `y` for paired sides.
- Use `rest` to avoid leaving old side values in effect accidentally.
- For books, use `inside` / `outside`, and set `binding` when the default binding side is wrong.

### One-off page overrides

Use `page(...)[body]` when only one section/page needs different settings, such as:
- landscape table pages
- title pages with special margins
- appendices with different columns

Remember: changing page settings can force page breaks.

## Headers, footers, and page numbering

### Simple numbering

Use `set page(numbering: "1")` or other numbering patterns for standard footers.

### Custom footers/headers

Once a custom `footer` is set, `page(numbering: ...)` is ignored. Use `counter(page).display(...)` inside the footer instead.

### Conditional headers/footers

Use `context` in page header/footer content when behavior depends on page number or document content.

Typical pattern:

```typ
#set page(header: context {
  if counter(page).get().first() > 1 [Running header]
})
```

Combine with `query(...)` to suppress headers on pages containing specific labeled content.

## Columns

### Page-level columns

Use `set page(columns: n)` for article-style multi-column documents. This interacts better with floats, footnotes, and page-level behavior than nested `columns(...)`.

### Nested columns

Use `columns(...)` only inside nested layout contexts like boxes, blocks, or custom regions.

### Escaping columns

Use `place(..., float: true, scope: "parent", ...)` to insert content that should temporarily span outside the current column flow, such as wide title blocks.

## Layout containers

These containers are primarily visual, not semantic:
- `block`
- `box`
- `stack`
- `grid`
- `columns`

Use them to arrange content, but do not rely on them to carry meaning for accessibility or downstream export.

### Quick distinctions

- `block` — block layout with spacing/break behavior.
- `box` — inline/container wrapper often used to keep things on one line or adjust inset.
- `stack` — directional stacking of content.
- `grid` — presentational two-dimensional layout.
- `table` — semantic tabular data.

## Table vs grid

This distinction is critical.

### Use `table` when

- rows/columns carry meaning
- users should read values by row/column relationship
- the structure should survive reflow/repurposing
- figures/captions/references should treat it like a real table

### Use `grid` when

- the arrangement is presentational only
- it is page/UI-like layout, card layout, label sheet, or dashboard framing
- no semantic table behavior is intended

Key difference from the docs: `figure` and accessibility semantics react to `table`, not `grid`.

## Table patterns

### Baseline table practice

- Use `table(...)` for tabular data.
- Use `table.header(...)` for header rows.
- Use `table.footer(...)` for footer rows when needed.
- Put the table inside `figure(kind: table, ...)` or rely on `figure(table(...), caption: ...)` when you need captioning/referencing behavior.

### Why `table.header` / `table.footer` matter

- clarify semantic intent
- support repeated headers/footers across pages
- improve accessibility and export quality

### Table styling guidance

- Use table/grid strokes, fills, alignments, and inset deliberately.
- Keep numeric columns aligned consistently.
- Avoid excessive decoration that obscures relationships.
- If the takeaway matters more than the raw matrix, express that takeaway in text or caption too.

## Figures

Use `figure(...)` for content that should carry figure semantics, captions, placement, and references.

Typical uses:
- images
- charts/diagrams
- tables when captioned and referenced as tables
- custom drawn content

Guidance:
- Use the `caption` argument for captions, not loose paragraph text underneath.
- Use labels and `@ref` for cross-references.
- If the figure body itself is not accessible, use `figure(alt: ...)` appropriately.
- If the figure contains an image, prefer image-level alt text over overriding at the figure level.

## Math layout reminders

- Inline math: `$x^2$`
- Display/block math: `$ x^2 $`
- Multi-line aligned derivations use `\` and `&` alignment points.
- For custom math font changes, style `math.equation` with a show-set rule.

## Common template layout patterns

### Title block above columns

- set page columns globally
- place title/author/abstract with `place(... scope: "parent", float: true, ...)`
- then flow body text in columns

### Front matter pages

- custom page function calls for title/front matter pages
- page counter reset only where truly needed
- separate visible title from metadata title only when necessary

### Wide table or landscape page

- use `page(flipped: true)[ ... ]`
- keep the special layout local rather than altering the whole document

## Practical defaults for Claude-generated layouts

- Put page setup once near the top.
- Use semantic containers first (`figure`, `table`, headings), then visual layout containers.
- Reach for `grid` only when the arrangement is not a table.
- For complex headers/footers, assume `context` may be required.
- When producing article/report templates, make page settings and document metadata obvious and easy to edit.
