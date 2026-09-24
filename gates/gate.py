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
              its check has not passed since; and refuses to end it on a message that hedges or explains a
              discrepancy with a story, or states a flat diagnosis, and cites nothing (the story gate); and
              refuses a message that claims to have checked something in a turn where no tool ran (the
              verification gate).

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

HOME = os.path.expanduser('~')
PROTECTED_DIRS = (os.path.join(HOME, '.claude', 'gates'), os.path.join(HOME, '.claude', 'reading-receipts'))
PROTECTED_FILES = (os.path.join(HOME, '.claude', 'settings.json'),)
PROTECT_WORDS = re.compile(r'(\.claude/gates|\.claude/settings\.json|install-gates\.sh|push-ok|reading-receipts)')
PUSH = re.compile(r'\bgit\b[^|;&]*\bpush\b|\bgh\s+(pr|release|repo)\s+(create|edit|merge|delete|sync)')

def protected_path(path):
    p = os.path.abspath(os.path.expanduser(path))
    if os.path.basename(p) == 'push-ok':
        return True
    return p in PROTECTED_FILES or any(p == d or p.startswith(d + os.sep) for d in PROTECTED_DIRS)

PROTECT_MSG = ('PROTECTED: the gates, their settings, the receipts and the push marker belong to the owner. A session does not '
               'edit the thing that gates it. Change gate code in the repo copy and ask the owner to run the installer in their '
               'own terminal; the owner creates push-ok themselves.')

def repo_of(cmd, root):
    m = re.search(r'\bgit\s+-C\s+("[^"]+"|\S+)', cmd) or re.search(r'^\s*cd\s+("[^"]+"|\S+)', cmd)
    d = os.path.expanduser(m.group(1).strip('"')) if m else root
    return os.path.abspath(d)

def push_gate(cmd, root):
    """A push happens only when the owner has created push-ok (in the repo's .claude folder, or ~/.claude for
    any repo) in their own terminal. The file is consumed: one touch, one push."""
    repo = repo_of(cmd, root)
    for marker in (os.path.join(repo, '.claude', 'push-ok'), os.path.join(HOME, '.claude', 'push-ok')):
        if os.path.exists(marker):
            os.remove(marker)
            return ''
    return ('PUSH GATE: nothing leaves this machine without the owner. There is no push-ok for %s.\n'
            'The owner allows ONE push by running, in their own terminal:\n  touch "%s/.claude/push-ok"\n'
            'Then run the push again. Do not create that file yourself; a session that does is refused.' % (repo, repo))

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

HEDGE = re.compile(r"\b(may be|might be|might have|may have|could be|could have|likely|unlikely|probably|presumably|possibly|perhaps|"
                   r"seems?( to| like)?|looks? like|appears? to|apparently|my (read|guess|sense|hunch) is|i'?d guess|i guess|if i had to (say|guess)|"
                   r"i suspect|i assume|i imagine|i believe|i think (it|this|that|the)|must (have been|be)|should (have been|be)|"
                   r"in theory|theoretically|typically|usually|tends? to|as far as i can tell|i'?m not (sure|certain)|"
                   r"stale (snapshot|copy|cache|version|read|state|tab|page|build|index)|(a|the) cach(e|ed)|race condition|timing issue|"
                   r"an? (old|older|outdated|earlier) (version|copy|snapshot|build)|left ?over from|artifact of|which (would|could) explain|"
                   r"that (would|could) explain|the only explanation|explains why)\b", re.I)
DIAG = re.compile(r"\b(that'?s why|which is why|the reason (is|was|being)|the (root )?cause( is| was)?|the culprit|the (problem|issue|bug) (is|was) (that|because)|"
                  r"(is|are|was|were) (what'?s )?(causing|breaking)|caused by|"
                  r"(isn'?t|is not|wasn'?t|was not|aren'?t|are not|weren'?t|were not) (on|off|set|enabled|disabled|active|turned on|turned off|wired|hooked up|connected|applied|loaded|present|there|running)|"
                  r"(is|was|are|were) (off|missing|broken|disabled|unset|stale|out of date|misconfigured|not (set|on|enabled|applied|wired))|"
                  r"never (fired|ran|loaded|applied)|"
                  r"(isn'?t|is not|not|wasn'?t|was not) (your|the|my|our|a|an) (problem|issue|concern|cause|factor)|(has|had) nothing to do with)\b", re.I)
CITE = re.compile(r"[\w./-]+\.(py|md|html|css|js|json|txt|sh|rtf|tsx?|jsx?)(:\d+)?|\bline \d+|\bat \d+:\d+|\bnode(-id)? [\d:]+|\bframe \d+|"
                  r"\b(output|printed|returned|exit code|stdout)\b|\b(curl|grep|python3?|node|npm|ls|cat|sed|get_metadata|get_design_context|get_screenshot)\b|"
                  r"\bI (have not|haven'?t) checked\b|\blet me check\b|\bI don'?t know\b", re.I)
VERIFY = re.compile(r"\b(i (checked|verified|confirmed|tested|ran|re-?ran|looked|opened|probed|measured|inspected|read)|"
                    r"(tests?|checks?|the check|the build|the sweep) (pass|passes|passed|is clean|are clean)|it works( now)?|works now|"
                    r"(is|are) (confirmed|verified)|all (good|clear|green)|(confirmed|verified) (that|it|the))\b", re.I)

def last_assistant_text(transcript_path):
    if not transcript_path or not os.path.exists(transcript_path):
        return ''
    text = ''
    for ln in open(transcript_path, encoding='utf-8', errors='replace'):
        try:
            d = json.loads(ln)
        except Exception:
            continue
        if d.get('type') != 'assistant':
            continue
        c = (d.get('message') or {}).get('content')
        parts = [c] if isinstance(c, str) else [b.get('text', '') for b in (c or []) if isinstance(b, dict) and b.get('type') == 'text']
        t = '\n'.join(x for x in parts if x)
        if t.strip():
            text = t
    return text

def story_scan(text):
    """Sentences that hedge or explain a discrepancy with a story, and carry no source, no question and no
    admission that the thing is unchecked. Code blocks, inline code and quoted lines are ignored."""
    t = re.sub(r'```.*?```', ' ', text, flags=re.S)
    t = re.sub(r'`[^`]*`', ' ', t)
    t = '\n'.join(l for l in t.splitlines() if not l.lstrip().startswith('>'))
    hits = []
    for sent in re.split(r'(?<=[.!?])\s+|\n+', t):
        s = sent.strip()
        if len(s) < 12 or s.endswith('?'):
            continue
        m = HEDGE.search(s) or DIAG.search(s)
        if m and not CITE.search(s):
            hits.append((m.group(0), s[:160]))
    return hits

def turn_tool_calls(transcript_path):
    """How many tool calls the assistant made since the owner's last real message (tool results do not count
    as owner messages)."""
    if not transcript_path or not os.path.exists(transcript_path):
        return None
    n = 0
    for ln in open(transcript_path, encoding='utf-8', errors='replace'):
        try:
            d = json.loads(ln)
        except Exception:
            continue
        c = (d.get('message') or {}).get('content')
        blocks = c if isinstance(c, list) else []
        if d.get('type') == 'user':
            if isinstance(c, str) or any(isinstance(b, dict) and b.get('type') == 'text' for b in blocks):
                n = 0                      # a real owner message starts a new turn
        elif d.get('type') == 'assistant':
            n += sum(1 for b in blocks if isinstance(b, dict) and b.get('type') == 'tool_use')
    return n

def verify_gate(data):
    """A message that says it checked something, in a turn where nothing was checked."""
    text = last_assistant_text(data.get('transcript_path'))
    t = re.sub(r'```.*?```', ' ', text, flags=re.S); t = re.sub(r'`[^`]*`', ' ', t)
    claims = [s.strip()[:160] for s in re.split(r'(?<=[.!?])\s+|\n+', t) if VERIFY.search(s) and not s.strip().endswith('?')]
    if not claims:
        return ''
    calls = turn_tool_calls(data.get('transcript_path'))
    if calls is None or calls > 0:
        return ''
    lines = ['VERIFICATION GATE: this message says something was checked, and no tool ran in this turn: no file was',
             'opened, no command was run, no probe was made. Either do the check now and state what it printed, or',
             'say plainly that it was not checked.']
    for c in claims[:8]:
        lines.append('  ' + c)
    return '\n'.join(lines)

def story_gate(data):
    hits = story_scan(last_assistant_text(data.get('transcript_path')))
    if not hits:
        return ''
    lines = ['STORY GATE: the message you were about to end on states things it has not checked. A hedge or an',
             'explanation with no source beside it does not get to end the turn. For each line below, do one of two',
             'things now: open the file or run the probe and state what you found, with the file and line or the',
             'command and its output; or turn the sentence into a question for the owner. Then end the turn.']
    for word, sent in hits[:12]:
        lines.append('  [%s]  %s' % (word, sent))
    return '\n'.join(lines)

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
            if fp and protected_path(fp):
                refuse(PROTECT_MSG)
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
            if PROTECT_WORDS.search(cmd) and (WRITEY.search(cmd) or 'install-gates.sh' in cmd):
                refuse(PROTECT_MSG)
            if PUSH.search(cmd):
                msg = push_gate(cmd, root)
                if msg:
                    refuse(msg)
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
        msgs = [m for m in (ui_gate(root, state), story_gate(data), verify_gate(data)) if m]
        if msgs:
            refuse('\n\n'.join(msgs))
        sys.exit(0)
    sys.exit(0)

if __name__ == '__main__':
    main()
