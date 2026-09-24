#!/bin/sh
# Installs the gates for EVERY session on this machine: copies this folder to ~/.claude/gates, keeps a copy of
# the contract template beside it, and adds the four hook entries to ~/.claude/settings.json (backed up first).
# Safe to re-run. To remove: delete the four "gates" hook entries from ~/.claude/settings.json.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"; REPO="$(dirname "$HERE")"; DEST="$HOME/.claude/gates"
mkdir -p "$DEST/template/.claude/hooks" "$DEST/template/.claude/skills/follow-spec" "$DEST/template/tools" "$DEST/template/rules"
cp "$HERE"/gate.py "$HERE"/gatelib.py "$HERE"/read-in.py "$HERE"/status.py "$HERE"/sweep.py "$HERE"/install-contract.sh "$HERE"/README.md "$DEST/"
for f in CLAUDE.md DESIGN.md VALIDATION.md CHECKLIST.md SCRUB.local.example.md .gitignore; do cp "$REPO/$f" "$DEST/template/$f"; done
cp "$REPO/tools/check.py" "$DEST/template/tools/"; cp "$REPO/rules/cite-before-claiming.md" "$DEST/template/rules/"
cp "$REPO/.claude/hooks/spec-reminder.py" "$DEST/template/.claude/hooks/"; cp "$REPO/.claude/skills/follow-spec/SKILL.md" "$DEST/template/.claude/skills/follow-spec/"
chmod +x "$DEST"/*.py "$DEST"/*.sh
python3 - <<'PY'
import json, os, shutil, time
p = os.path.expanduser('~/.claude/settings.json')
d = json.load(open(p)) if os.path.exists(p) else {}
if os.path.exists(p): shutil.copy(p, p + '.pre-gates-' + time.strftime('%Y%m%d-%H%M'))
g = 'python3 "$HOME/.claude/gates/gate.py"'
want = {
 'SessionStart': {'matcher': 'startup|resume', 'hooks': [{'type': 'command', 'command': g, 'timeout': 15, 'statusMessage': 'Reading receipt and rules'}]},
 'PreToolUse':   {'matcher': 'Read|Edit|Write|MultiEdit|NotebookEdit|Bash', 'hooks': [{'type': 'command', 'command': g, 'timeout': 15}]},
 'PostToolUse':  {'matcher': 'Read|Edit|Write|MultiEdit', 'hooks': [{'type': 'command', 'command': g, 'timeout': 30}]},
 'Stop':         {'hooks': [{'type': 'command', 'command': g, 'timeout': 15}]},
}
hooks = d.setdefault('hooks', {})
for ev, entry in want.items():
    lst = hooks.setdefault(ev, [])
    lst[:] = [e for e in lst if not any('gates/gate.py' in h.get('command', '') for h in e.get('hooks', []))]
    lst.append(entry)
json.dump(d, open(p, 'w'), indent=2)
print('hooks written to', p)
PY
echo "gates installed globally. Open a new session in any project and try to edit before reading: it must be refused."
