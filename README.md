# The Provenance Contract

Five rules a designer holds an AI coding agent to, so that the decisions stay the designer's.
They live in files at the root of every project the agent works in, rather than in anyone's
head, and they survive a change of model, session or collaborator because a new agent reads
the same files before touching anything.

This repository is the contract as a template: the three files, the hook that puts the rule
in front of the agent before every edit, the skill that spells out how to read a spec, the
checker that blocks a build on a violation, and the acceptance checklist one agent writes for
the next. Copy it into a project, fill in the numbers, and the agent works under it from the
first session.

The write-up of where these rules came from, with the incidents that produced each one, is at
[aleciamitchell.com/method](https://aleciamitchell.com/method) (password protected; ask).

## The five rules

1. **Every value has to cite its source.** Nothing generated ships unless it traces back to a
   design token, a line of spec, a documented decision, or something the owner said. Where there
   is no source, the agent asks instead of approximating.
2. **Conflicts surface, and a person resolves them.** When two sources disagree, the agent lays
   out both values and the options. It never picks a winner on its own.
3. **Feedback like "a little darker" becomes a real value from the system.** The agent takes the
   nearest value that exists in the design system, says which one it chose, and lets the owner
   adjust it.
4. **The agent checks what a machine can check, and the owner checks what it looks like.**
   Compilation, types, references, leak scans and contrast measurements belong to the agent. It
   is not allowed to say something looks right.
5. **Discuss before building, and wait for the owner's go before anything leaves.** Commits,
   pushes, publishes, deletions and anything near credentials wait for a yes, every time. Inside
   the workspace the agent works in a temporary copy and the loop goes around until both sides are
   satisfied.

Underneath all five: **automate the work, never automate the verdict.**

## What is in this repository

| File | Job |
|---|---|
| `CLAUDE.md` | Behavior. What the project is, the module map, the non-negotiables, what to read first. |
| `DESIGN.md` | Numbers. Tokens, type, spacing, radii, the ramps that rule 3 maps feedback onto. |
| `VALIDATION.md` | The rule. Never invent a value or a word; open the file; ask when there is no source. Grows a log of past violations. |
| `.claude/settings.json` | Wires the hooks and holds the permission rules the agent cannot override. |
| `.claude/hooks/spec-reminder.py` | Runs before every Edit or Write and puts the spec rule back in front of the agent at the moment it matters. |
| `.claude/skills/follow-spec/SKILL.md` | The full process for building from a spec dump rather than eyeballing an image. |
| `rules/cite-before-claiming.md` | A rule for conversation, not only for edits: nothing about the product is stated as fact unless it was just read and can be cited by file and line. |
| `CHECKLIST.md` | The acceptance checklist an outgoing agent writes for whoever builds next, and the next agent runs before it touches anything. |
| `tools/check.py` | The checker. Undefined classes, broken local references, unbalanced tags, bad nesting, em-dashes and scrubbed terms. Exit code 1 blocks the build. |
| `SCRUB.local.example.md` | The shape of the local, never-committed list of terms that must not reach a published file. |
| `example/` | A two-file page the checker passes, for trying it out. |

## Install

1. Copy `CLAUDE.md`, `DESIGN.md`, `VALIDATION.md`, `CHECKLIST.md`, `rules/`, `tools/` and
   `.claude/` into the project root.
2. Fill in `CLAUDE.md` and `DESIGN.md` for the project. Delete the placeholder lines.
3. Copy `SCRUB.local.example.md` to `SCRUB.local.md`, add the real terms, and keep it out of
   version control. The template `.gitignore` already excludes it.
4. Run the checker once so the agent sees it pass:

```bash
python3 tools/check.py
```

The agent reads `VALIDATION.md` at the start of every session because the `SessionStart` hook
prints it into context, and it reads the spec reminder before every edit because the
`PreToolUse` hook fires on Edit, Write and MultiEdit.

## The checker

`tools/check.py` walks every HTML page under the root it is given and reports:

- a class used in the markup that no linked stylesheet defines (the page renders as unstyled text
  with no error anywhere);
- a stylesheet, script, image or page link that points at a file that is not there;
- tag counts that do not balance, and a `</div>` that closes more than is open;
- an em-dash in the page;
- any term from `SCRUB.local.md` in a page, an asset or a file name. Short all-caps codes match
  case-sensitively; multi-word terms are also matched with every separator stripped, which is what
  catches a name written as an email address or a domain.

It refuses to report clean when the scrub list exists but fails to parse, because a checker that
reports clean on an empty list is worse than none. It cannot catch a class that exists but is
wrong for the job. Only reading catches that.

## The hook and the skill

The skill is the full process. The hook exists because a skill alone gets skipped under heavy
context load. The hook reads the tool call, and when the file being edited matches the patterns
at the top of `spec-reminder.py` it injects one paragraph: read the spec dump first, copy each
value from it, cite the line, never eyeball the image. Edit the patterns to match the project.

## The loop

Discuss what to build and why. The agent works in a temporary copy. Review the result. Go around
again. Anything that leaves the workspace waits for a yes. The freedom is real because it is
scoped to whatever can be undone.

## The succession checklist

Before a model or a session changes, the outgoing agent writes `CHECKLIST.md` for whoever builds
next: the leak checks, the integrity checks, the collateral-damage checks and the owner's standing
rules, with a report format and the instruction to wait at the commit gate. The next agent runs
every check and pastes the results before it acts. The checklist has caught defects shipped by the
same agent that wrote it.

## License

MIT. See `LICENSE`.
