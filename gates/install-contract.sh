#!/bin/sh
# Installs the Provenance Contract template into a folder that has none.
# Usage: sh ~/.claude/gates/install-contract.sh /path/to/project
set -e
D="$1"; T="$HOME/.claude/gates/template"; [ -d "$HOME/Repos/provenance-contract" ] && T="$HOME/Repos/provenance-contract"
[ -n "$D" ] || { echo "usage: install-contract.sh <folder>"; exit 1; }
[ -d "$T" ] || { echo "template missing at $T"; exit 1; }
mkdir -p "$D/.claude/hooks" "$D/.claude/skills/follow-spec" "$D/tools" "$D/rules"
for f in CLAUDE.md DESIGN.md VALIDATION.md CHECKLIST.md SCRUB.local.example.md .gitignore; do [ -e "$D/$f" ] || cp "$T/$f" "$D/$f"; done
[ -e "$D/tools/check.py" ] || cp "$T/tools/check.py" "$D/tools/check.py"
[ -e "$D/rules/cite-before-claiming.md" ] || cp "$T/rules/cite-before-claiming.md" "$D/rules/"
[ -e "$D/.claude/hooks/spec-reminder.py" ] || cp "$T/.claude/hooks/spec-reminder.py" "$D/.claude/hooks/"
[ -e "$D/.claude/skills/follow-spec/SKILL.md" ] || cp "$T/.claude/skills/follow-spec/SKILL.md" "$D/.claude/skills/follow-spec/"
echo "contract installed in $D (nothing that already existed was replaced). The gates will now require VALIDATION.md, CLAUDE.md and DESIGN.md to be read before any edit there."
