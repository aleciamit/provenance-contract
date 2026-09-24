# The gates

Deterministic checks on a coding-agent session, outside the model. Installed once, they govern every
project on the machine. They exist because instructions to an agent are soft: a session that has read
the rule can still skip it under momentum. A hook cannot be skipped.

| Gate | Event | What it does |
|---|---|---|
| Reading receipt | Read (before and after) | Records every window of every file the session reads, corrected to what the tool returned when it truncated. |
| Reading gate | Edit, Write, MultiEdit, NotebookEdit, Bash | Refuses any edit, write or writing command until every line of the project's mandatory set has been read this session. Read-only commands pass. |
| Contract gate | Edit, Write | Refuses a write into a folder with no `VALIDATION.md` and no `.contract` marker in it or any folder above it. The refusal names the install command. |
| Rules sweep | Edit, Write (after) | If the project has `gates/sweep.py` or `.claude/sweep.py`, runs it over any Markdown, text or HTML file written and reports the hits into the session. |
| UI gate | Stop | If the project has `.claude/uigate.json`, refuses to end the turn while a listed file changed this session and the check's marker is older than the change. |
| Story gate | Stop | Reads the message the session is about to end on and refuses the turn while it hedges (probably, seems to, may be, I assume, I believe, must have been) or explains a discrepancy with a story (a stale snapshot, a cache, an old version, that would explain) with no source beside it: no file and line, no command and output, no question, no admission that it is unchecked. The refusal names each sentence and asks for the check or the question. |
| Session start | SessionStart | Prints the receipt's state and the project's `RULES.md` and `START-HERE.md`, if they exist. |

## Install, on any machine

```bash
git clone https://github.com/aleciamit/provenance-contract ~/Repos/provenance-contract
sh ~/Repos/provenance-contract/gates/install-gates.sh
```

That copies the engine to `~/.claude/gates/`, keeps the contract template beside it, and adds four hook
entries to `~/.claude/settings.json` (backed up first). Open a new session in any project and try to edit
a file before reading anything: it must be refused with the list of what is unread.

## What a project has to read

The project's `.claude/mandatory.txt` (or `gates/mandatory.txt`) if it has one: one entry per line,
relative to the project, globs allowed, `path:tail:N` for the last N lines, `HANDOFF-*.md:newest:3` for
the newest three by name. Without a list, the set is every rule file the project has: `RULES.md`,
`START-HERE.md`, `CLAUDE.md`, `VALIDATION.md`, `DESIGN.md`, and the two newest `HANDOFF-*.md`. A
project with none of those is not gated for reading, and its folders refuse writes until a contract is
installed, which then makes those files mandatory.

The set is frozen per session and per project at first sight, so a handoff the session writes or a line it
appends never locks that same session out. The next session resolves the list afresh.

## Reading counts two ways

Through the Read tool, in windows of any size, or through `python3 ~/.claude/gates/read-in.py <n>` for
every chunk it lists. Both write the same receipt (`~/.claude/reading-receipts/<session id>.json`).
`python3 ~/.claude/gates/status.py` shows what is left. Reading with `cat` does not count: tool output
above about ten kilobytes is cut to a preview, and the same cap is why the files are not printed into
context by a hook. Reading is verified instead of injected.

## Optional files a project can add

- `.claude/sweep.py`: a script that takes one file path and prints its findings, ending with `N hits`.
  The included `sweep.py` is one owner's writing rules; copy and edit it for yours.
- `.claude/uigate.json`: `{"files": ["app/index.html"], "marker": "app/.uicheck-ok", "command": "python3 app/uicheck.py"}`.
  The check writes the marker on pass; the Stop hook compares its age with the files.
- `RULES.md`: the owner's rules in the owner's words, printed first at every session start.

## Limits, said plainly

The story gate is a pattern list over sentences, so a determined session can phrase around it; what it removes is the free version of guessing, where a hedge or an invented cause ends the turn unchallenged. After one refusal the harness lets the next stop through (`stop_hook_active`), so the demand is made once per turn, plainly. Code blocks, inline code and quoted lines are not scanned.

The Bash write check is a pattern list (redirects, tee, sed -i, cp, mv, rm, git commit and push, Python
file writes and so on), not a parser. The gate proves the words passed through the session; it cannot prove
they were applied. The owner's eye still holds the verdict.
