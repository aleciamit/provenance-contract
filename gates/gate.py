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
Stop          refuses to end the turn while a file listed in .claude/uigate.json was edited BY THIS SESSION and
              its check has not passed since (another session's edits never hold this one); and refuses to end it on a message that hedges or explains a
              discrepancy with a story, or states a flat diagnosis, and cites nothing (the story gate); and
              refuses a message that claims to have checked something in a turn where no tool ran (the
              verification gate).

The mandatory set is the project's .claude/mandatory.txt or gates/mandatory.txt; without one it is every
rule file the project has: RULES.md, START-HERE.md, CLAUDE.md, VALIDATION.md, DESIGN.md, the two newest
HANDOFF-*.md. Nothing here depends on the model's cooperation. That is the point.

Every gate can be switched off in switches.json beside this file (see GATES below for the names).
"""
import sys, os, re, json, subprocess, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gatelib as G

WRITEY = re.compile(r'(?<![<|])>(?!>)\s*\S|>>|\btee\b|\bsed\s+-i|\bcp\s|\bmv\s|\brm\s|\brmdir\b|\bmkdir\b|\btouch\b|\bgit\s+(commit|push|add|rm|mv|checkout|reset|rebase|merge|init)|\bopen\(|\.write\(|os\.rename|os\.remove|os\.replace|shutil\.|\bchmod\b|\bln\s|\bcat\s*>|python3?\s+-\s*<<|\bnpm\s+(install|run|init)|\bpip3?\s+install|\bnpx\b')
READONLY_OK = re.compile(r'^\s*(cd\s+\S+\s*(&&|;)\s*)?python3?\s+(\S*/)?(read-in|status|gate|sweep|uicheck)\.py(\s|$)')
SWEEP_EXT = ('.md', '.txt', '.html')

# Each gate can be turned off in switches.json, kept beside this file. A missing file or a missing key means
# the gate is on, so an older install behaves as before. Only the owner changes the installed copy.
GATES = ('reading', 'contract', 'story', 'verify', 'ui', 'push', 'sweep', 'protect')

def switches():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'switches.json')
    try:
        s = json.load(open(p))
    except Exception:
        s = {}
    return {g: bool(s.get(g, True)) for g in GATES}

ON = switches()
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

NOT_OWNER = ('<system-reminder', 'Stop hook feedback', '[SYSTEM NOTIFICATION', '<task-notification', '<command-',
             'Caveat:', 'PreToolUse:', 'PostToolUse:', '[Request interrupted')
PUSH_WORD = re.compile(r'\b(push(ed|es|ing)?|publish(ed|ing)?)\b', re.I)
PUSH_YES = re.compile(r"\b(you can|you may|go ahead|allow(ed|ing)?|ok(ay)?|yes|yep|sure|please|do it|push it|go for it|permission|approved?)\b", re.I)
PUSH_NO = re.compile(r"\b(don'?t|do not|never|not|no|stop|wait|hold off|without)\b[^.!?\n]{0,25}\b(push|publish)", re.I)

def last_owner_text(transcript_path):
    """The text of the owner's most recent real message: typed by the owner, never a tool result, a hook's
    feedback, a system notice or a reminder."""
    if not transcript_path or not os.path.exists(transcript_path):
        return ''
    last = ''
    for ln in open(transcript_path, encoding='utf-8', errors='replace'):
        try:
            d = json.loads(ln)
        except Exception:
            continue
        a = d.get('attachment') or {}
        if d.get('type') == 'attachment' and a.get('type') == 'queued_command' \
                and (a.get('origin') or {}).get('kind') == 'human' and isinstance(a.get('prompt'), str):
            if a['prompt'].strip():
                last = a['prompt']         # a message the owner typed while a reply was running
            continue
        if d.get('type') != 'user' or d.get('isMeta'):
            continue
        c = (d.get('message') or {}).get('content')
        texts = [c] if isinstance(c, str) else [b.get('text', '') for b in (c or [])
                                                  if isinstance(b, dict) and b.get('type') == 'text']
        texts = [t for t in texts if t.strip() and not t.lstrip().startswith(NOT_OWNER)]
        if texts:
            last = '\n'.join(texts)
    return last

def owner_said_push(transcript_path):
    """The owner's latest message says yes to a push: a push word, a yes word, and no "don't push" or "wait"."""
    t = last_owner_text(transcript_path)
    return bool(t and PUSH_WORD.search(t) and PUSH_YES.search(t) and not PUSH_NO.search(t))

def push_gate(cmd, root, data=None):
    """A push happens only on the owner's yes. The yes is either the owner's own latest message in this chat
    (a push word and a yes word, and no "don't"; it lasts until the owner's next message), or a push-ok file the
    owner created in their own terminal (in the repo's .claude folder, or ~/.claude for every repo), which stands
    until the owner deletes it. Tool output, web pages and files never count as the owner. A session cannot
    create the file (self-protection refuses it)."""
    repo = repo_of(cmd, root)
    for marker in (os.path.join(repo, '.claude', 'push-ok'), os.path.join(HOME, '.claude', 'push-ok')):
        if os.path.exists(marker):
            return ''
    if data and owner_said_push(data.get('transcript_path')):
        return ''
    return ('PUSH GATE: the owner has not said yes to a push from %s.\n'
            'Ask the owner in chat; their own message saying to push allows it until their next message. Or the owner '
            'allows pushes from that repo, once, by running in their own terminal:\n  touch "%s/.claude/push-ok"\n'
            'and deleting that file stops them again. Do not create it yourself; a session that does is refused.' % (repo, repo))

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

def ui_config(root):
    cfg = os.path.join(root, '.claude', 'uigate.json')
    if not os.path.exists(cfg):
        return None
    try:
        return json.load(open(cfg))
    except Exception:
        return None

def note_ui_touch(state, root, fp):
    """Record that THIS session wrote a UI-gated file. fp is absolute or project-relative."""
    c = ui_config(root)
    if not c or not fp:
        return
    rel = G.rel(fp, root) if os.path.isabs(fp) else fp
    if rel in c.get('files', []):
        state.setdefault('ui_touched', {})[rel] = time.time()

SEGMENT = re.compile(r'\|\||&&|;|\n|(?<!\|)\|(?!\|)')
REDIRECT_TO = re.compile(r'(?<![<&\d])>{1,2}\s*("[^"]+"|\'[^\']+\'|[^\s;&|<>]+)')
TEE_TO = re.compile(r'\btee\b((?:\s+-\w+)*)\s+("[^"]+"|\'[^\']+\'|[^\s;&|<>]+)')
FILE_CMD = re.compile(r'^\s*(?:sudo\s+)?(sed\s+-i|rm|rmdir|touch|truncate|mv|cp|install|ln|rsync|mkdir|chmod|chown|git\s+(?:\S+\s+)*(?:checkout|restore|reset|rm|mv))\b')
SCRIPT_WRITE = re.compile(r'open\([^)]*[\'"][wax]|write_?[Tt]ext\(|writeFile(Sync)?\(|\.write\(|os\.(replace|rename|remove)|shutil\.')

def write_tokens(cmd):
    """The paths a Bash command writes to, as far as a pattern can tell: the target of a redirect or tee, every
    file sed -i, rm, touch, mv, chmod, git checkout and the like are given, and the destination of cp, install,
    ln or rsync. 2>&1, &> and redirects to /dev/null name no file. Naming, reading or running a file is not
    writing it."""
    toks = []
    for seg in SEGMENT.split(cmd):
        toks += [m.group(1) for m in REDIRECT_TO.finditer(seg)]
        toks += [m.group(2) for m in TEE_TO.finditer(seg)]
        f = FILE_CMD.match(seg)
        if f:
            args = seg.split()
            toks += args[-1:] if f.group(1) in ('cp', 'install', 'ln', 'rsync') else args
    return [t.strip('"\'') for t in toks]

def bash_ui_writes(cmd, files):
    """The UI-gated files a Bash command WRITES (see write_tokens), plus a file named inside an inline script
    that writes. Files are matched by their project path (search/index.html), never by bare name, so another
    folder's index.html is not this one."""
    hit = set()
    if SCRIPT_WRITE.search(cmd):
        hit.update(rel for rel in files if rel in cmd)
    for t in write_tokens(cmd):
        hit.update(rel for rel in files if t == rel or t.endswith('/' + rel))
    return hit

INSTALLER_RUN = re.compile(r'^\s*(?:sudo\s+)?(?:(?:sh|bash|zsh|source|\.)\s+)?\S*install-gates\.sh\b')
CD_TO = re.compile(r'^\s*cd\s+("[^"]+"|\S+)')
GIT_IN_PROTECTED = re.compile(r'\bgit\s+-C\s+"?\S*\.claude/(gates|reading-receipts)')

def protect_bash(cmd):
    """Self-protection for Bash: refuse a command that RUNS the installer or WRITES a protected path (the installed
    gates, the receipts, settings.json, any push-ok), including through a cd into a protected folder, git -C on
    one, or an inline script that writes and names one. Reading, listing, grepping or diffing them passes."""
    cwd = None
    for seg in SEGMENT.split(cmd):
        if INSTALLER_RUN.match(seg):
            return True
        m = CD_TO.match(seg)
        if m:
            cwd = os.path.expanduser(m.group(1).strip('"'))
            continue
        for t in write_tokens(seg):
            p = os.path.expanduser(t)
            if cwd and not os.path.isabs(p):
                p = os.path.join(cwd, p)
            if protected_path(p):
                return True
    if SCRIPT_WRITE.search(cmd) and PROTECT_WORDS.search(cmd):
        return True
    if GIT_IN_PROTECTED.search(cmd) and WRITEY.search(cmd):
        return True
    return False

def note_ui_touch_bash(state, root, cmd):
    """A Bash command that writes a UI-gated file counts as touching it (see bash_ui_writes)."""
    c = ui_config(root)
    if not c:
        return
    for rel in bash_ui_writes(cmd, c.get('files', [])):
        state.setdefault('ui_touched', {})[rel] = time.time()

def ui_gate(root, state):
    """Hold the turn only for files this session itself edited (Edit, Write, MultiEdit, NotebookEdit, or a writing
    Bash command that named the file) when the check's marker is older than that edit. A file changed by another
    session in the same folder is that session's to check, never this one's."""
    c = ui_config(root)
    if not c:
        return ''
    mark = os.path.join(root, c.get('marker', '.uicheck-ok'))
    mtime = os.path.getmtime(mark) if os.path.exists(mark) else 0
    dirty = [rel for rel, when in state.get('ui_touched', {}).items()
             if os.path.exists(os.path.join(root, rel)) and when > mtime]
    if dirty:
        return ('UI GATE: %s changed in this session and the check has not passed since. Run\n  %s\nand fix what it reports before handing back.'
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
        on = [g for g in GATES if ON[g]]
        head = 'GATES ON: %s.' % (', '.join(on) or 'none')
        parts = [head + (' ' + reading_status(state, root) if ON['reading'] else '')]
        for name in ('RULES.md', 'START-HERE.md'):
            p = os.path.join(root, name)
            if os.path.exists(p):
                parts.append('%s:\n%s' % (name, open(p, encoding='utf-8').read()))
        parts.append('No time estimates, ever.')
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
            if ON['protect'] and fp and protected_path(fp):
                refuse(PROTECT_MSG)
            if ON['reading']:
                miss = G.missing(state, root); G.save(sid, state)
                if miss:
                    refuse(reading_status(state, root))
            if ON['contract']:
                ok, msg = contract_ok(fp)
                if not ok:
                    refuse(msg)
            sys.exit(0)
        if tool == 'Bash':
            cmd = ti.get('command') or ''
            if READONLY_OK.search(cmd):
                sys.exit(0)
            if ON['protect'] and protect_bash(cmd):
                refuse(PROTECT_MSG)
            if ON['push'] and PUSH.search(cmd):
                msg = push_gate(cmd, root, data)
                if msg:
                    refuse(msg)
            if ON['reading'] and WRITEY.search(cmd) and G.missing(state, root):
                G.save(sid, state)
                refuse('This command can write, and the reading receipt is incomplete.\n' + reading_status(state, root))
            if WRITEY.search(cmd):
                note_ui_touch_bash(state, root, cmd); G.save(sid, state)
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
        if tool in ('Edit', 'Write', 'MultiEdit', 'NotebookEdit'):
            fp = ti.get('file_path') or ti.get('notebook_path') or ''
            note_ui_touch(state, root, fp); G.save(sid, state)
            if ON['sweep'] and fp.endswith(SWEEP_EXT) and not any(s in fp for s in SWEEP_SKIP) and os.path.exists(fp):
                rep = sweep_report(root, fp)
                if rep and not rep.endswith('0 hits'):
                    out({'hookSpecificOutput': {'hookEventName': 'PostToolUse', 'additionalContext': 'RULES SWEEP on ' + G.rel(fp, root) + ':\n' + rep}})
            sys.exit(0)
        sys.exit(0)

    if ev == 'Stop':
        if data.get('stop_hook_active'):
            sys.exit(0)
        msgs = [m for m in ((ON['ui'] and ui_gate(root, state)),
                            (ON['story'] and story_gate(data)),
                            (ON['verify'] and verify_gate(data))) if m]
        if msgs:
            refuse('\n\n'.join(msgs))
        sys.exit(0)
    sys.exit(0)

if __name__ == '__main__':
    main()
