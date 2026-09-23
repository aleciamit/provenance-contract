#!/usr/bin/env python3
"""PreToolUse hook. Before every Edit, Write or MultiEdit whose target matches WATCH, put the
spec rule back in front of the agent. Non-blocking: it adds context, it does not refuse the edit.

The skill in .claude/skills/follow-spec/ is the full process. This hook exists because a skill
alone gets skipped under heavy context load; the reminder arrives at the exact moment it matters.

Edit WATCH to match the files that carry visual values in this project.
"""
import sys, json, fnmatch, os

WATCH = ["*.html", "*.css", "*.jsx", "*.tsx", "*.vue", "*.svelte"]

REMINDER = (
    "PROVENANCE RULE. You are editing {name}. If this change sets ANY visual value (px, %, "
    "color, font-family, font-size, font-weight, line-height, padding, margin, gap, width, "
    "height, border, border-radius, box-shadow) for a module that has a spec in specs/, you "
    "MUST copy each value from the matching spec dump and be able to cite its line. Do not "
    "eyeball the image and do not substitute a close-enough design token. Where DESIGN.md holds "
    "the value, cite the token. Where no source exists, stop and ask. Read the source first, "
    "then build from what you read, and state each value with its source when you report."
)

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

path = ((data.get("tool_input") or {}).get("file_path") or "")
name = os.path.basename(path)
if any(fnmatch.fnmatch(name, pat) for pat in WATCH):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": REMINDER.format(name=name),
        }
    }))
sys.exit(0)
