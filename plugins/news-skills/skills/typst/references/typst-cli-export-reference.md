# Typst CLI and export reference

Use this file for `typst compile`, `typst watch`, export target selection, feature flags, PDF standards, and CLI input injection.

## Core commands

### Compile once

```bash
typst compile input.typ output.pdf
```

If no format is specified, Typst exports PDF by default.

### Watch

```bash
typst watch input.typ output.pdf
```

Use for iterative editing.

## Choosing output format

Use `--format` or an output extension.

Examples:

```bash
typst compile --format pdf input.typ output.pdf
typst compile --format png input.typ out-{p}.png
typst compile --format svg input.typ out-{p}.svg
typst compile --format html input.typ output.html
typst compile --format bundle site.typ dist
```

## Page selection

PDF, PNG, and SVG support page filtering:

```bash
typst compile --pages "2,3,7-9,11-" input.typ output.pdf
```

Half-open ranges are allowed.

## CLI inputs and `sys.inputs`

Inject string inputs with `--input key=value`.

```bash
typst compile --input title="Quarterly Report" --input draft=true main.typ report.pdf
```

In Typst:

```typ
#let title-text = sys.inputs.title if "title" in sys.inputs else "Untitled"
#let draft = sys.inputs.draft == "true" if "draft" in sys.inputs else false
```

Rules to remember:
- values are strings
- parse structured data manually
- keep command examples synchronized with `sys.inputs.key` usage in code

## PDF export

PDF is the default target and the most stable general-purpose export format.

### Important flags

- `--pdf-standard ...`
- `--no-pdf-tags`
- `--pages ...`

Example:

```bash
typst compile --pdf-standard ua-1 main.typ accessible.pdf
```

### `--pdf-standard`

Supported values include PDF versions and standards such as:
- `1.4`, `1.5`, `1.6`, `1.7`, `2.0`
- `a-1b`, `a-1a`, `a-2b`, `a-2u`, `a-2a`, `a-3b`, `a-3u`, `a-3a`, `a-4`, `a-4f`, `a-4e`
- `ua-1`

Guidance:
- default PDF is 1.7
- prefer `ua-1` for accessibility-focused workflows today
- PDF/A is for archival goals
- PDF/A and PDF/UA cannot currently be targeted at the same time

### `--no-pdf-tags`

Avoid this unless the user explicitly wants inaccessible visual-only PDF output. Tagged PDF is on by default and provides baseline accessibility.

### Accessibility extras feature flag

Some PDF accessibility helpers are experimental and gated:
- `pdf.table-summary`
- `pdf.header-cell`
- `pdf.data-cell`

Enable with:

```bash
typst compile --features a11y-extras input.typ output.pdf
```

or

```bash
TYPST_FEATURES=a11y-extras typst compile input.typ output.pdf
```

Treat these as unstable.

## PNG export

Use for raster image workflows, not accessibility.

### Important flags

- `--format png`
- `--ppi ...`
- `--pages ...`

Example:

```bash
typst compile --format png --ppi 300 slides.typ slide-{0p}.png
```

Notes:
- default PPI is `144`
- higher PPI is better for print/detail
- PNG text is not directly accessible/extractable

## SVG export

Use for vector image workflows, especially web embedding.

Example:

```bash
typst compile --format svg figures.typ fig-{p}.svg
```

Notes:
- multi-page documents emit multiple files
- output pattern must include `{p}`, `{0p}`, or `{t}` when multiple pages exist
- SVG text is converted to glyph outlines for consistent rendering, so text is not screen-reader/copy-paste accessible

## HTML export

HTML export is experimental.

### Required feature flag

```bash
typst compile --format html --features html input.typ output.html
```

or

```bash
TYPST_FEATURES=html typst compile --format html input.typ output.html
```

### Watch mode behavior

`typst watch` for HTML can also:
- choose port via `--port`
- disable live reload injection via `--no-reload`
- disable serving via `--no-serve`

### Mental model

- HTML export aims for semantic output, not faithful page-layout reproduction.
- Use `target()` plus `html.elem(...)` when templates/show rules need export-specific HTML behavior.
- Typst currently emits standalone HTML files, not fragments.
- CSS is not emitted automatically; custom CSS may still be layered on later.

## Bundle export

Bundle export is also experimental and useful for multi-file sites or multi-output projects.

### Required feature flag

```bash
typst compile --format bundle --features bundle site.typ dist
```

If bundle contents include HTML, enable both features:

```bash
typst compile --format bundle --features bundle,html site.typ dist
```

Equivalent env-var form:

```bash
TYPST_FEATURES=bundle,html typst compile --format bundle site.typ dist
```

### Watch mode extras

Bundle watch mode can:
- choose server port with `--port`
- disable reload script injection with `--no-reload`
- disable serving with `--no-serve`

### Bundle semantics

Bundle export uses Typst `document(...)` and `asset(...)` elements to create output files.

Critical rule:
- introspection, labels, counters, and states are **global across the bundle**
- exception: page counter stays per document

Implication:
- heading numbering/query results may span all bundle documents unless manually reset/scoped
- cross-document links by label are supported and relative paths resolve automatically

## Export recommendations

### Prefer PDF when
- the user wants stable printable output
- accessibility matters and HTML is not required
- the workflow is standard, not experimental

### Prefer HTML when
- semantic web output is the main goal
- the user accepts preview/experimental behavior
- the template can branch on `target()` for export-specific markup

### Prefer bundle when
- one Typst project should emit multiple documents/assets
- cross-document linking or shared source content is useful
- the user understands the experimental nature and bundle-wide introspection semantics

### Prefer PNG/SVG when
- the output is being embedded as an image elsewhere
- accessibility is handled in the surrounding document, not the image itself
