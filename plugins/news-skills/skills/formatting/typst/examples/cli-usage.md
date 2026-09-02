# Typst CLI usage patterns

## Basic PDF compile

```bash
typst compile main.typ output.pdf
```

## Watch a PDF during editing

```bash
typst watch main.typ output.pdf
```

## Compile selected PDF pages with an accessibility standard

```bash
typst compile \
  --pages "1-3,5" \
  --pdf-standard ua-1 \
  main.typ output.pdf
```

Do not add `--no-pdf-tags` when targeting accessible output.

## Pass template parameters through CLI inputs

Given Typst code that reads `sys.inputs.title`, `sys.inputs.subtitle`, and
`sys.inputs.draft`:

```bash
typst compile \
  --input title="Q1 Revenue Report" \
  --input subtitle="Prepared for the board" \
  --input draft=false \
  report-template.typ report.pdf
```

Remember: `sys.inputs` values are strings.

## Export PNG pages for raster workflows

```bash
typst compile --format png --ppi 300 slides.typ slide-{0p}.png
```

PNG is visual output only, not an accessibility target.

## Export SVG pages for vector workflows

```bash
typst compile --format svg diagrams.typ diagram-{p}.svg
```

SVG text is outlined for consistent rendering, so it is not a good accessibility target.

## Experimental HTML export

```bash
typst compile --format html --features html article.typ article.html
```

Equivalent environment-variable form:

```bash
TYPST_FEATURES=html typst compile --format html article.typ article.html
```

## Experimental bundle export with HTML

```bash
typst compile --format bundle --features bundle,html html-bundle-patterns.typ dist
```

Equivalent environment-variable form:

```bash
TYPST_FEATURES=bundle,html typst compile --format bundle html-bundle-patterns.typ dist
```

## Watch experimental HTML or bundle output without serving

```bash
typst watch --format html --features html --no-serve article.typ article.html
```

```bash
typst watch --format bundle --features bundle,html --no-serve site.typ dist
```

## Experimental PDF accessibility extras

```bash
typst compile --features a11y-extras complex-table.typ output.pdf
```

Use this only when intentionally trying unstable PDF accessibility helpers.
