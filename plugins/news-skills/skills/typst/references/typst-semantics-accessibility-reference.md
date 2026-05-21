# Typst semantics and accessibility reference

Use this file whenever a Typst task involves document structure, cross-references, figures/tables/math, language, or export quality.

## First principle

Accessible Typst starts with semantic source, not post-processing.

Prefer Typst elements that express meaning directly:
- `title`
- `heading`
- `list`, `enum`, `terms`
- `figure`
- `table`
- `ref`, labels, bibliography/citations
- `quote`, emphasis, strong emphasis

Do not fake these with plain text plus styling unless the user explicitly needs a non-semantic effect.

## Document title

Set a machine-readable title before content:

```typ
#set document(title: [Document Title])
```

Then use `#title()` or `#title[Custom Visible Title]` for the visible title.

Important rules:
- Do not use a heading as the document title.
- Do not use the `title` element more than once.
- `document(title: ...)` matters for metadata, PDF viewers, browsers, and accessibility checks.

## Headings

- Use real headings (`=`, `==`, etc.) instead of enlarged bold text.
- Keep heading levels sequential; do not skip levels when going deeper.
- It is fine in Typst to have multiple first-level section headings under the document title.

## References and document structure

- Use labels and `@label` / `ref(...)` instead of manually typing “Figure 2” or “Section 3”.
- Use figure captions via the `caption` argument.
- Use bibliography/citation features instead of hand-built reference lists when citations are involved.

## Reading order

Typst source order defines logical reading order.

When using:
- `place`
- `move`
- floating figures

put the call in source where a screen reader should encounter it, even if the visual placement is elsewhere.

## Layout containers are not semantics

Containers such as `grid`, `stack`, `box`, `block`, and `columns` are mainly visual.

Implications:
- AT often reads their contents in source order only.
- If the layout itself conveys meaning, provide that meaning with semantic elements or text.
- Do not use `grid` to represent tabular data; use `table`.

## Tables

### Semantic rules

- Use `table` for real tabular data.
- Use `table.header(...)` and `table.footer(...)` where appropriate.
- Use captions/references when tables are discussed in the prose.

### Accessibility note

Even accessible tables can be cognitively heavy for AT users. When possible, state the key takeaway in text or caption as well.

## Figures and images

### Images

Use `image(..., alt: "...")`.

Alt text guidance:
- describe what matters in context
- do not say “image of ...” redundantly
- do not add invisible metadata/credits/jokes into alt text
- keep it proportionate to the image’s relevance

### Figures

Use `figure(alt: ...)` only when the figure body is not otherwise accessible and the alternative description should stand in for it.

Important distinction:
- If the figure contains an image, set alt text on the **image**, not both image and figure.
- If the figure contains shapes/curves/visual constructs with semantic meaning, `figure(alt: ...)` is often appropriate.
- If the figure contains a `table`, do **not** replace it with figure alt text; let the table stay semantically available.

## Math accessibility

This is easy to forget and should be checked proactively.

Use `math.equation(alt: ...)` for accessible equations, especially block equations:

```typ
#math.equation(
  block: true,
  alt: "a squared plus b squared equals c squared",
  $ a^2 + b^2 = c^2 $,
)
```

Notes:
- Describe the formula in natural language, as read aloud.
- PDF/UA-1 export requires accessible math descriptions.
- Future HTML/PDF 2.0 improvements are planned, but do not assume they remove the need today.

## Artifacts

Artifacts are content that should be ignored by assistive technology and reflow.

Use `pdf.artifact(...)` for purely decorative content such as:
- decorative separators
- non-informational backgrounds
- ornamental repeated motifs

Do **not** mark meaningful content as artifacts.

Important constraint: once content is inside an artifact, it cannot become semantic again. If decoration and semantic content overlap, stack them with layout tools such as `place` instead of wrapping everything in an artifact.

## Natural language

Set language at the start of the document:

```typ
#set text(lang: "en", region: "US")
```

Why this matters:
- screen reader pronunciation
- translation/repurposing quality
- hyphenation
- typesetting conventions
- localized labels for figures/references

Use scoped `text(lang: ...)` or local `set text(...)` blocks for multilingual fragments.

## PDF/UA basics to remember

For accessible PDF work, check these items:

- `document(title: ...)` is set.
- `text(lang: ..., region: ...)` is set when relevant.
- semantic elements are used instead of visual hacks.
- images have alt text.
- math uses `math.equation(alt: ...)` where needed.
- decorative content is marked with `pdf.artifact` when appropriate.
- PDF tags are not disabled.

Typst writes tagged PDF by default. `--no-pdf-tags` makes files inaccessible and breaks accessible conformance targets.

## Export-format limits

- **PDF** and **HTML** are the accessibility-capable targets.
- **PNG** and **SVG** are not accessibility targets on their own.
- If PNG/SVG output is required, provide textual representation in the surrounding accessible work.
- For highest Universal Access, distributing HTML alongside PDF can be preferable.

## Safe response patterns for Claude

When generating Typst with structure-sensitive content:
- create semantic source first
- style the semantic source second
- mention required metadata/lang/alt constraints explicitly
- warn if a requested visual trick weakens semantics or accessibility
