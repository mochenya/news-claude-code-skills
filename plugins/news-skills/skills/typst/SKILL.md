---
name: typst
description: This skill should be used when the user asks to write, edit, debug, refactor, template, or export Typst documents; mentions `.typ` files, Typst markup, show/set rules, headings, figures, tables, references, math, accessibility, `typst compile`, `typst watch`, PDF/HTML/bundle export, or wants CLI help for Typst. Use it proactively for Typst authoring and automation tasks, even when the user only describes the document outcome and does not explicitly say “Typst.”
---

# Typst skill

Create, edit, and validate Typst documents with an official-docs-first workflow.

If upstream Typst changes make the bundled practical references outdated in real use, consult the latest upstream documentation:

- https://typst.app/docs/reference/
- https://github.com/typst/typst/tree/main/docs

## Purpose

Use this skill to keep Typst work aligned with the official documentation while staying practical. Prefer semantic Typst elements over visual imitation, keep templates composable with `set` and `show` rules, and treat export behavior and accessibility as first-class constraints instead of afterthoughts.

This skill is intentionally split into a lean entry point plus heavier references and examples. Read only the files needed for the current task.

## Working approach

Start by classifying the task into one or more of these buckets:

1. **Authoring and core language** — syntax, markup, scripting, modules, packages, `std`, `calc`, `sys`, `sys.inputs`.
2. **Layout and styling** — page setup, margins, headers/footers, columns, blocks, boxes, stacks, grids, tables, figures, common math layout.
3. **Semantics and accessibility** — headings, title, references, figures, tables, reading order, artifacts, language, PDF/UA requirements.
4. **CLI and export** — `typst compile`, `typst watch`, output formats, pages, feature flags, PDF standards, HTML/bundle workflows.
5. **Recipes and templates** — reusable document shells, `context` / `query` / `counter` / `locate`, CLI-driven configuration, multi-document bundle patterns.

Then load the matching reference files before proposing code.

## Core principles

- Prefer **semantic elements** (`heading`, `figure`, `table`, `ref`, `bibliography`, lists, `title`) over styling plain text into a lookalike.
- Prefer **`set` rules** for defaults and **show-set rules** for composable styling. Use transformational `show` rules when structure must change, not as the first resort.
- Treat **`context` and introspection as contextual and location-dependent**. Keep computations that depend on `context`, `counter`, `query`, `locate`, or style context inside contextual code.
- Use **`table` for tabular data** and **`grid` for presentational layout**. Do not use `grid` as a semantic table substitute.
- When using **figures, tables, math, images, or export workflows**, proactively check accessibility and target-format constraints.
- Keep HTML and bundle work explicitly marked as **experimental** and include the necessary feature flags in commands.
- When exposing document configuration through the CLI, prefer **`--input key=value` + `sys.inputs.key`** instead of hard-coding variants.

## Decision checklist

Before finalizing Typst code or commands, check these questions:

- Is the structure semantic, not just visually similar?
- Should styling be expressed with `set` / `show` instead of repeated local formatting?
- Does the task rely on context or introspection, and if so, is the logic kept inside contextual code?
- If a table is present, should it use `table.header` / `table.footer` and a caption/reference?
- If math is present, does block math needing accessibility use `math.equation(alt: ...)`?
- If the document is intended to be accessible, are `document(title: ...)`, `text(lang:, region:)`, image alt text, figure alt usage, and `pdf.artifact` handled correctly?
- If exporting to HTML or bundle, are feature flags documented and are limitations stated?
- If exporting to PNG or SVG, has it been made clear that those formats are not accessibility targets on their own?

## Reference files

Read these as needed:

- `references/typst-core-reference.md` — language model, scripting, modules, packages, `std`, `calc`, `sys`, `sys.inputs`.
- `references/typst-layout-reference.md` — page setup, layout containers, figures, tables, and common layout patterns.
- `references/typst-semantics-accessibility-reference.md` — semantics, reading order, alt text, math accessibility, title/lang, PDF/UA.
- `references/typst-cli-export-reference.md` — CLI commands, output formats, pages, PPI, PDF standards, experimental flags.
- `references/typst-recipes-reference.md` — template patterns, contextual headers, introspection recipes, CLI-driven templates, HTML/bundle recipes.

## Example files

Copy and adapt from these when the user needs a starting point or a safe pattern:

- `examples/minimal-document.typ`
- `examples/article-template.typ`
- `examples/report-template.typ`
- `examples/thesis-frontmatter.typ`
- `examples/accessible-figure-and-math.typ`
- `examples/tables-patterns.typ`
- `examples/context-introspection-patterns.typ`
- `examples/html-bundle-patterns.typ`
- `examples/cli-usage.md`

## Output guidance

When responding to a Typst task:

1. State the intended document/export goal briefly.
2. Use the most semantic Typst construct that fits.
3. Mention any accessibility or export caveats that materially affect the result.
4. Provide commands that match the code exactly, especially for `sys.inputs` and experimental feature flags.
5. When relevant, point to the closest example or reference file so the work can be extended consistently.
