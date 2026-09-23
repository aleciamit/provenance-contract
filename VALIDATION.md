# VALIDATION: never guess (read before every edit)

This file exists because an agent will act on a plausible guess instead of reading the actual
file, and every such incident takes one look to prevent and a session to unwind. It is
read into context at the start of every session by the `SessionStart` hook.

## The one rule

**Every visual value and every piece of copy you write must trace to a source. If it does not,
you do not get to invent it. You ask.**

**Before you write a class name, a selector, an anchor, a file path or a diagnosis, open the
thing and look at it. If you have not read it in this session, you do not know what it says.**

A guess that happens to be right is still a violation, because the next one will be wrong.

## Sources of truth, in priority order

1. An explicit instruction in the current conversation.
2. A spec file in `specs/`: a CSS dump, a design export, a documented decision.
3. `CLAUDE.md` and `DESIGN.md`: tokens, locked decisions, the module map.
4. The existing code's established pattern for that exact element.

If none of these cover the value, ask. Do not fill the gap with a plausible number, color, label
or icon.

## What counts as looking

1. Read the exact file you are about to edit, in the region you are about to edit.
2. Read the pattern already used for the same job elsewhere in that file. If a table exists,
   build the second table the way the first one is built. Do not infer structure from a class
   name. A class name is not documentation.
3. `CLAUDE.md`, `DESIGN.md`, the newest handoff.
4. Ask the owner.

## Two kinds of values, never confused

- **Spec-fixed** (styling and copy): sizes, weights, line heights, colors, gaps, padding, radii,
  borders, static labels, icon choice. These match the spec exactly. Do not round, improve or
  substitute a nearby token.
- **Data-driven** (per-record values): anything pulled from a data object. These come only from
  the data, never hardcoded, never changed to match a spec image's sample values. If real data
  looks wrong, say so; do not overwrite it. If data is invalid by a business rule, clamp it to a
  valid value and flag it.

## Pre-edit checklist

1. Have I opened the target file and read the surrounding markup, in this session?
2. For every value I am about to write, which of the sources above supplies it? If the answer is
   my judgment, ask instead.
3. For every class I am about to write, have I seen its rule in the CSS, or seen it used for this
   exact purpose in the markup? If neither, look it up.
4. Am I copying an existing pattern? Then copy its structure, not my memory of it.
5. Am I reusing or moving an existing component? Then preserve its exact classes, font and sizing.
6. Am I changing a value the owner did not mention? Then do not. Touch only what was asked.
7. Is this a restore from backup? HTML and CSS are a matched pair. Restore both or neither, then
   run the checker.
8. Am I about to explain why something is broken? Have I tested that cause, or does it only sound
   right?

## Post-edit self-check

State it back, one line per change:

`<element> · <property>: <value> ← <source, by file and line>`

If any line would read `← (seemed right)`, `← (matched the name)`, `← (design token)` or
`← (from memory)`, revert it and go look. Then confirm: "I changed only what was requested; no
incidental font, size, color or data changes." If that is not true, list every incidental change
and why. Then run:

```bash
python3 tools/check.py
```

## When two sources conflict

Surface it with the exact value from each source and ask which wins. Do not pick one.

## Say when a source fails to load

If a link, spec file, screenshot or dump the owner hands over does not load, comes back empty or
renders as a fragment, say so in the same reply, before reporting anything else. Name the source
that failed and what you did instead. Silence reads as coverage. Never swap the owner's source for
one you found without saying which and why.

## Settled and open, kept visibly apart

- **Settled.** You read it in a file this session, the owner said it, or you fetched it. State it.
- **Open.** You have not checked. Either check it, or put "I have not checked this" in the
  sentence. Never state an open thing in the settled register.

The tell: if a sentence would survive being prefixed with "I have not checked this, but", and you
were about to say it without that prefix, stop.

Hedges are not honesty. "Probably", "seems to", "likely" and "my guess is" are unverified claims
wearing a disclaimer, and the owner still has to read and correct them. There are two legal
moves: go get the data, or ask a one-line question.

## The owner's observations are evidence

When the owner reports how the running thing behaves, that is a report of something they can
see. Do not explain it away from theory. Probe first: read the code path, dump the data, run the
request. "Working as intended" is a conclusion earned with evidence, not an opening assumption.
When the owner offers a diagnosis, test theirs before offering your own.

When the owner corrects you, make the change and continue. Do not re-explain your reasoning,
because it reads as defending the mistake.

## Directives and questions are different

A directive ("use X", "make it Y", "let's try Z") is executed, then shown, with any caveat in one
line underneath. When the subject is visual, the render answers the question.

A question ("how do I", "what is", "can you see") gets an answer. It is not a work order. Do not
create, rename, move or delete any file outside the request. Offering costs the owner one
word; acting costs them a review.

## The rule covers the domain, not only files

If a claim is about the users, the product's behavior, the organization or the owner's intent,
and you did not read it in a file, hear it this session or fetch it, you do not get to state it.
Ask. When you need a fact you do not have, say "I don't know X" and ask for it. "I don't know of
X" is a fact about your memory, not about the world. If X can be checked, check it before saying
it does not exist.

## Known past violations: do not repeat

This section grows. Each entry is dated and names what happened, what it cost, and the rule that
came out of it, so the same conversation never has to happen twice. Format:

- **YYYY-MM-DD · short title.** What was done. What was true instead. Where one look would have
  shown it. **The rule.**

## The pattern in all of these

A hypothesis formed quickly, sounded right, and was acted on before it was checked. The fix is
never cleverness. It is opening the file.
