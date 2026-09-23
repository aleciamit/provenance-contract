---
name: follow-spec
description: MANDATORY before implementing or editing any page, section, module, card or component when a spec dump or design export exists for it in specs/. Enforces reading the actual dump and tracing every size, color, font, spacing, radius and shadow value to a real line in it. Never eyeball from an image, never substitute a close-enough token. Trigger whenever a spec file is provided or referenced, when asked to match the design, or when spacing, padding, color or values are reported wrong.
---

# Follow the spec. Do not eyeball.

When a spec exists, the spec is the law. This skill exists because an agent left to itself builds
from the image plus the design tokens instead of reading the dump, and the rework costs more than
the reading would have.

## The one rule

Every visual value you write (px, %, color, font-family, font-size, font-weight, line-height,
padding, margin, gap, width, height, border, border-radius, box-shadow) is copied from a specific
line in the spec dump. If it is not in the dump, you ask. You do not invent, approximate, or reuse
a token that looks close.

The image is only for layout, which elements exist, copy, and which data fills each slot. It is
never a source for a numeric, color or font value.

## Required process, in order

1. **Locate the files.** List `specs/` first; names drift. Find the dump and the image for this
   module.
2. **Skip what is already built.** Dumps often begin with shared chrome that exists. Find the
   block for the thing you are building.
3. **Read the block in context.** Exports list elements in visual order. Read sequentially and
   map each block to its element by order, width and content, not by guessing. Searching is for
   finding a block and sanity-checking a count; it does not replace reading.
4. **Copy exact values per element.** Container: width, height, padding, gap, direction,
   alignment, background, border, radius, shadow. Text: family, size, weight, line height, color,
   alignment. Write the literal values. Swap in a token only when the dump's value equals that
   token and you have confirmed it.
5. **Style from the dump, data from the record.** A sample value in the spec image belongs to
   the spec's example, not to the live data.
6. **Copy labels verbatim**, including anything that looks like a typo. Flag it and ask; never
   correct it on your own.
7. **If a value is not in the dump, stop and ask.**

## Post-build self-check, stated back when reporting

One line per element, with the dump line it came from:

`<element> · <property>: <value> ← specs/<file>:<line>`

If any line would read `← (eyeballed)`, `← (design token)` or `← (looked right)`, you broke the
rule. Revert that value, read the dump, fix it, then report.

## Smell tests

- "I'll use the standard card padding" → read the dump's padding.
- "The image looks like about a 16px gap" → read the dump's gap.
- "Close enough to the token" → read the dump's value.
- Building the whole component, then checking a couple of values: the wrong order. Read first,
  build from what you read.
