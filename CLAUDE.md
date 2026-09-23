# CLAUDE.md

<!-- Replace the placeholders. This file owns behavior and architecture. DESIGN.md owns the
numbers. VALIDATION.md owns the process. Keep this file lean; put per-module detail in specs/. -->

**Project:** <name>. <One sentence: what it is and who uses it.>

**Owner:** <name>. The owner designs; the agent builds from the owner's designs. Never frame the
agent as the source of a design decision.

Your job is to make the requested change and nothing else. Not to rewrite copy, restructure
layout, or touch anything uninvited.

## Read first

| | |
|---|---|
| `VALIDATION.md` | The one rule: never guess, open the file and look. Printed into context every session. |
| `DESIGN.md` | The visual source of truth: exact values, tokens, ramps. |
| `specs/` | Per-module spec dumps and exports. Read the dump; never eyeball the image. |
| newest `HANDOFF-*.md` | Decisions, current state, what is blocking. Authoritative. |
| `SCRUB.local.md` | Terms that must never appear in a published file. Local only, never committed. |
| `CHECKLIST.md` | What the previous agent requires of you before you commit anything. |

## What this is

<Two or three sentences. Stack, build step or none, where it deploys.>

## Files

- <path> · <what it is>
- <path> · <what it is>

## Non-negotiables

1. **Never guess.** Open the file and look. See `VALIDATION.md`.
2. **A class name lives in the HTML and the CSS at once.** Rename it in both or neither. Getting
   this wrong renders the page as unstyled text with no error anywhere.
3. **Back up before editing.** `cp <file> backup/<file>-pre-<what>-$(date +%H%M)` into a new
   folder every time, never into an existing backup folder.
4. **Never delete or move the owner's files.** Copy and rename.
5. **Never invent a number**, a label, or a reason for one of the owner's decisions.
6. **Never reintroduce a scrubbed term.** See `SCRUB.local.md`.
7. **Do not rewrite the owner's copy** unless asked for a wording change.
8. **Do not judge the visual from a preview.** Verify by code and by the checker; the owner looks
   at it in their own browser.
9. **Ask before anything leaves the workspace:** commits, pushes, publishes, deletions,
   credentials.

## Before you hand back

```bash
python3 tools/check.py
```

Fails on undefined classes, broken local references, unbalanced tags, bad nesting, em-dashes and
scrubbed terms. If it fails, fix it before you stop. Then state the post-edit self-check from
`VALIDATION.md`, one line per change with its source.
