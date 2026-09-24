#!/usr/bin/env python3
"""The gates: deterministic checks on a coding-agent session, outside the model. One script, four hook
events, installed once in ~/.claude/settings.json and governing every project on the machine.

SessionStart  prints the reading receipt's state and the project's RULES.md and START-HERE.md (if any).
PreToolUse    Read: notes the window being read. Edit/Write/MultiEdit/NotebookEdit and any Bash command
              that can write: REFUSED until every line of the project's mandatory reading set has been
              read this session. Also refused: a write into a folder with no contract (no VALIDATION.md
              and no .contract marker in the folder or any folder above it).
PostToolUse   Read: corrects the window to what was actually returned when the tool truncated. Edit/Write:
              runs the project's sweep (gates/sweep.py or .claude/sweep.py) over the file and reports.
Stop          refuses to end the turn while a file listed in .claude/uigate.json changed this session and
              its check has not passed since.

The mandatory set is the project's .claude/mandatory.txt or gates/mandatory.txt; without one it is every
rule file the project has: RULES.md, START-HERE.md, CLAUDE.md, VALIDATION.md, DESIGN.md, the two newest
HANDOFF-*.md. Nothing here depends on the model's cooperation. That is the point.
"""
import sys, os, re, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gatelib as G

WRITEY = re.compile(r'(?<![<|])>(?!>)\s*\S|>>|\btee\b|\bsed\s+-i|\bcp\s|\bmv\s|\brm\s|\brmdir\b|\bmkdir\b|\btouch\b|\bgit\s+(commit|push|add|rm|mv|checkout|reset|rebase|merge|init)|\bopen\(|\.write\(|os\.rename|os\.remove|os\.replace|shutil\.|\bchmod\b|\bln\s|\bcat\s*>|python3?\s+-\s*<<|\bnpm\s+(install|run|init)|\bpip3?\s+install|\bnpx\b')
READONLY_OK = re.compile(r'^\s*(cd\s+\S+\s*(&&|;)\s*)?python3?\s+(\S*/)?(read-in|status|gate|sweep|uicheck)\.py(\s|$)')
SWEEP_EXT = ('.md', '.txt', '.html')
SWEEP_SKIP = ('/_archive/', '/node_modules/', '/backup', '/vendor/', '/dist/', '/.claude/', 'FACTS.md', 'HANDOFF-', 'WHAT-CHANGED-', 'NEXT.md', '/audit-', '/reports/', '/notes/', 'MOVES-', 'her-words-from-sessions')

def out(obj):
    print(json.dumps(obj)); sys.exit(0)

def refuse(msg):
    sys.stderr.write(msg.rstrip() + '\n'); sys.exit(2)

def reading_status(state, root):
    miss = G.missing(state, root)
    if not miss:
        return 'READING RECEIPT: complete for %s.' % G.rel(root, root)
    lines = ['READING RECEIPT: INCOMPLETE for %s. Edits and writes are refused until these are read in full.' % root,
             'Read each with the Read tool (offset + limit windows are fine), or run',
             '  python3 ~/.claude/gates/read-in.py        (lists the chunks)',
             '  python3 ~/.claude/gates/read-in.py <n>    (prints chunk n; every chunk must be printed)',
             'Still unread:']
    for p, gaps in miss:
        lines.append('  %s  lines %s' % (G.rel(p, root), ', '.join('%d-%d' % g for g in gaps)))
    return '\n'.join(lines)

def contract_ok(path):
    p = os.path.abspath(path); home = os.path.expanduser('~')
    for exempt in ('/private/tmp/', '/tmp/', home + '/.claude/', home + '/Library/', home + '/Applications/', home + '/Desktop/'):
        if p.startswith(exempt):
            return True, ''
    d = os.path.dirname(p)
    while True:
        if os.path.exists(os.path.join(d, 'VALIDATION.md')) or os.path.exists(os.path.join(d, '.contract')):
            return True, ''
        parent = os.path.dirname(d)
        if parent == d or d == home or not d.startswith(home):
            break
        d = parent
    return False, ('CONTRACT GATE: %s has no contract (no VALIDATION.md and no .contract marker in it or above it).\n'
                   'Install one first, then retry:\n  sh ~/.claude/gates/install-contract.sh "%s"' % (os.path.dirname(p), os.path.dirname(p)))

def sweep_report(root, path):
    for c in ('gates/sweep.py', '.claude/sweep.py'):
        s = os.path.join(root, c)
        if os.path.exists(s):
            r = subprocess.run([sys.executable, s, path], capture_output=True, text=True)
            return r.stdout.strip()
    return ''

def ui_gate(root, state):
    cfg = os.path.join(root, '.claude', 'uigate.json')
    if not os.path.exists(cfg):
        return ''
    try:
        c = json.load(open(cfg))
    except Exception:
        return ''
    mark = os.path.join(root, c.get('marker', '.uicheck-ok'))
    mtime = os.path.getmtime(mark) if os.path.exists(mark) else 0
    started = state.get('started', 0)
    dirty = [f for f in c.get('files', []) if os.path.exists(os.path.join(root, f))
             and os.path.getmtime(os.path.join(root, f)) > started and os.path.getmtime(os.path.join(root, f)) > mtime]
    if dirty:
        return ('UI GATE: %s changed this session and the check has not passed since. Run\n  %s\nand fix what it reports before handing back.'
                % (', '.join(dirty), c.get('command', 'the UI check')))
    return ''

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    ev = data.get('hook_event_name', ''); sid = data.get('session_id', ''); tool = data.get('tool_name', '')
    ti = data.get('tool_input') or {}
    root = G.project_root(data)
    state = G.load(sid)

    if ev == 'SessionStart':
        G.mandatory_for(state, root); G.save(sid, state)
        parts = ['THE GATES ARE ON. ' + reading_status(state, root)]
        for name in ('RULES.md', 'START-HERE.md'):
            p = os.path.join(root, name)
            if os.path.exists(p):
                parts.append('%s:\n%s' % (name, open(p, encoding='utf-8').read()))
        parts.append('Also on: a write into a folder with no contract is refused; a project sweep runs after every write '
                     'when the project has one; a changed UI blocks the end of the turn until its check passes. '
                     'No time estimates, ever.')
        out({'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext': '\n\n'.join(parts)[:9000]}})

    if ev == 'PreToolUse':
        if tool == 'Read':
            fp = ti.get('file_path') or ''
            if fp:
                off = int(ti.get('offset') or 1) or 1; lim = int(ti.get('limit') or 2000)
                state['pending'][fp] = [off, off + lim - 1]; G.save(sid, state)
            sys.exit(0)
        if tool in ('Edit', 'Write', 'MultiEdit', 'NotebookEdit'):
            fp = ti.get('file_path') or ti.get('notebook_path') or ''
            miss = G.missing(state, root); G.save(sid, state)
            if miss:
                refuse(reading_status(state, root))
            ok, msg = contract_ok(fp)
            if not ok:
                refuse(msg)
            sys.exit(0)
        if tool == 'Bash':
            cmd = ti.get('command') or ''
            if READONLY_OK.search(cmd):
                sys.exit(0)
            if WRITEY.search(cmd) and G.missing(state, root):
                G.save(sid, state)
                refuse('This command can write, and the reading receipt is incomplete.\n' + reading_status(state, root))
            sys.exit(0)
        sys.exit(0)

    if ev == 'PostToolUse':
        if tool == 'Read':
            fp = ti.get('file_path') or ''
            if not fp:
                sys.exit(0)
            off = int(ti.get('offset') or 1) or 1
            a, b = state['pending'].pop(fp, [off, off + int(ti.get('limit') or 2000) - 1])
            m = re.search(r'showing lines (\d+)-(\d+) of (\d+)', json.dumps(data.get('tool_response', '')))
            if m:
                a, b = int(m.group(1)), int(m.group(2))
            if os.path.exists(fp):
                b = min(b, G.line_count(fp))
            G.record(state, fp, a, b)
            done = not G.missing(state, root)
            G.save(sid, state)
            if done and not state.get('announced'):
                state['announced'] = True; G.save(sid, state)
                out({'hookSpecificOutput': {'hookEventName': 'PostToolUse', 'additionalContext': reading_status(state, root)}})
            sys.exit(0)
        if tool in ('Edit', 'Write', 'MultiEdit'):
            fp = ti.get('file_path') or ''
            if fp.endswith(SWEEP_EXT) and not any(s in fp for s in SWEEP_SKIP) and os.path.exists(fp):
                rep = sweep_report(root, fp)
                if rep and not rep.endswith('0 hits'):
                    out({'hookSpecificOutput': {'hookEventName': 'PostToolUse', 'additionalContext': 'RULES SWEEP on ' + G.rel(fp, root) + ':\n' + rep}})
            sys.exit(0)
        sys.exit(0)

    if ev == 'Stop':
        if data.get('stop_hook_active'):
            sys.exit(0)
        msg = ui_gate(root, state)
        if msg:
            refuse(msg)
        sys.exit(0)
    sys.exit(0)

if __name__ == '__main__':
    main()
