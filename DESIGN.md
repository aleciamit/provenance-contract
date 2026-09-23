# DESIGN.md

<!-- The visual source of truth. Every number the agent writes comes from here, from a spec dump
in specs/, or from an explicit instruction. Where this document and the source files disagree,
the source files win. Replace every placeholder; delete every row you do not use. -->

## How to read this file

Each ramp lists its steps in order. Rule 3 of the contract depends on this: when the owner says
"a little darker" or "more breathing room", the agent moves one step along the relevant ramp,
says which value it chose, and lets the owner adjust. It never invents a value between steps.

## Surfaces

| Token | Value | Used for |
|---|---|---|
| `--bg` | `#______` | the page |
| `--panel` | `#______` | cards, rails |
| `--paper` | `#______` | the lightest surface |

## Ink

| Token | Value | Used for |
|---|---|---|
| `--ink` | `#______` | headings, the darkest text |
| `--ink-2` | `#______` | body prose |
| `--muted` | `#______` | labels, captions, secondary text |

## Accent ramp

| Step | Token | Value | Used for |
|---|---|---|---|
| 1 | `--accent-soft` | `#______` | selected states, halos |
| 2 | `--accent` | `#______` | links, labels, one large line |
| 3 | `--accent-dark` | `#______` | hover, filled shapes |

Contrast: every text and background pair is measured, never eyeballed. Record the ratio beside
any pair below 7:1.

## Type

| Role | Family | Weights | Sizes |
|---|---|---|---|
| prose | <family> | <weights> | <sizes> |
| headings | <family> | <weights> | <sizes> |
| labels | <family> | <weights> | <sizes> |

Fonts are <self-hosted / loaded from ______>. No other font requests.

## Spacing ramp

`4 · 8 · 12 · 16 · 24 · 32 · 48 · 64` <replace with the project's steps>

## Radii ramp

`2 · 4 · 6 · 8 · 12` <replace with the project's steps>

## Elevation

| Level | Shadow | Used for |
|---|---|---|
| 0 | none | flat surfaces |
| 1 | `______` | cards at rest |
| 2 | `______` | cards on hover, menus |

## Layout

- Frame width: `____px`
- Rail width: `____px`
- Gutter: `____px`
- Breakpoints: `____`, `____`, `____`. Test the smallest one and the band between the others,
  not only phone and desktop.

## Locked decisions

Values that look wrong and are right on purpose. The agent does not "fix" these.

- <example: the sidebar is 300px where the design file says 288, accepted on YYYY-MM-DD>
