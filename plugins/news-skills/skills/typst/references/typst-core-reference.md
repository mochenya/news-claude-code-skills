# Typst core reference

Use this file for language-level Typst decisions: syntax, scripting, modules, packages, and standard-library patterns.

## Mental model

- Typst has three modes: **markup**, **code**, and **math**.
- Most authoring starts in markup. Use `#` to enter code expressions. Use `$...$` for math.
- Typst joins content values naturally, so code blocks can build documents without string assembly.
- Functions are pure; templates and document-wide styling are typically applied through `show` rules and `set` rules, not imperative mutation.

## Syntax essentials

- Use built-in markup when possible:
  - `= Heading`, `== Subheading`
  - `*strong*`, `_emphasis_`
  - `- list item`, `+ numbered item`, `/ Term: definition`
  - `<label>` and `@label` for labels/references
  - raw text with backticks
- Prefer Typst-native markup over manually constructing equivalent text with `text(...)`.
- Use kebab-case for custom identifiers where possible.

## Styling model

### Prefer these layers in order

1. **Element call** for one-off local formatting.
2. **`set` rule** for defaults across a scope.
3. **show-set rule** for styling selected elements while preserving composability.
4. **transformational `show` rule** when the element’s rendered structure must change.

### Practical guidance

- Use `set page(...)`, `set text(...)`, `set par(...)`, `set heading(...)` for document defaults.
- Keep transformational show rules focused; avoid burying lots of unrelated `set` rules inside them.
- If a semantic element already exists, style that element instead of replacing it with plain text.

## Scripting essentials

Use scripting for automation, not to simulate a different language.

### Common building blocks

- `let` bindings for reusable values and functions.
- `if / else` for content variants.
- `for` loops for repeated content.
- Arrays and dictionaries for structured data.
- Destructuring for compact extraction.
- Methods like `.map`, `.filter`, `.join`, `.len()` for data shaping.

### Content vs strings

- Use **content blocks** `[...]` for styled/document content.
- Use **strings** for machine data, labels, CLI values, parsing, and low-level text operations.
- Do not build large visible documents as concatenated strings.

## Modules and packages

### Project files

- `include "file.typ"` inserts rendered content.
- `import "file.typ"` brings a module into scope.
- `import "file.typ": thing` imports selected definitions.

### Packages

- Community packages use `@preview/name:version` imports.
- Prefer small, explicit imports for reusable helpers or templates.
- If package behavior is version-sensitive, keep the version literal visible.

## Standard modules to remember

### `std`

Use `std.name` when a local binding shadows a standard definition.

```typ
#let text = [shadowed]
#std.text(fill: blue)[Actual text element]
```

`std` is also useful for version-compatibility/polyfill patterns when a definition may or may not exist.

### `calc`

Use `calc` for numeric work that goes beyond simple operators.

Typical uses:
- `calc.min`, `calc.max`, `calc.clamp`
- constants like `calc.pi`
- derived sizes and simple layout math

### `sys`

Remember two especially important items:

- `sys.version` — compiler version checks for compatibility logic.
- `sys.inputs` — external CLI inputs injected with `--input key=value`.

## `sys.inputs` pattern

This is one of the most useful CLI-driven automation hooks.

- A CLI flag like `--input theme=dark` becomes `sys.inputs.theme`.
- Values arrive as **strings**.
- Parse structured values manually if needed, e.g. via `json(...)`.

Example:

```typ
#let theme = sys.inputs.theme if "theme" in sys.inputs else "light"
#let draft = sys.inputs.draft == "true" if "draft" in sys.inputs else false
```

Use this for:
- draft/final toggles
- paper size or audience modes
- title/subtitle overrides
- choosing HTML/PDF variants from a single source

Do not imply typed CLI inputs unless you explicitly parse them.

## Context and contextual computations

Some Typst features depend on where content appears, not just what code says.

Important contextual mechanisms:
- `context ...`
- `counter(...)`
- `query(...)`
- `locate(...)`
- `here()`

Rules to remember:
- Values depending on context are opaque until placed.
- Keep dependent logic inside contextual code.
- Compiler iterations may be needed; poorly designed contextual feedback loops can fail to converge.

If a computation needs current page, heading number, nearby labels, or resolved positions, treat it as contextual from the start.

## Data loading and encoding

Use built-in loaders for structured external data when appropriate. Keep in mind:
- Encoded/decoded roundtrips may be lossy for non-plain data.
- Simple arrays/dictionaries/numbers/strings are safest.
- `repr` is for debugging, not stable data interchange.

## Symbols and math helpers

- Use symbol names and math shorthands instead of awkward Unicode guessing when readability improves.
- Outside math, access math items with `math.` prefixes when needed.

## Good defaults for Claude-generated Typst

- Favor idiomatic markup first, functions second, low-level tricks last.
- Write reusable template functions with named parameters and a trailing body/content parameter.
- Put document configuration near the top.
- If a task may vary between runs, expose it via function parameters or `sys.inputs`.
- Mention version-sensitive or experimental behavior explicitly.
