"""Shared pieces for the gates: project root, the mandatory set, the per-session receipt, coverage math.
Generic: nothing in here knows about any particular project."""
import os, re, glob, json, time

RECEIPTS = os.path.expanduser('~/.claude/reading-receipts')
DEFAULT_SET = ['RULES.md', 'START-HERE.md', 'CLAUDE.md', 'VALIDATION.md', 'DESIGN.md', 'HANDOFF-*.md:newest:2']

def project_root(data=None):
    """The project a hook call belongs to. Starts from the cwd the harness reports (else the process cwd)
    and walks UP to the project: the top folder under ~/Repos, or the nearest ancestor holding .claude,
    .git, CLAUDE.md, VALIDATION.md or .contract. A shell sitting in a subfolder is still in the project."""
    cwd = os.path.abspath(os.path.expanduser((data or {}).get('cwd') or os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()))
    home = os.path.expanduser('~'); repos = os.path.join(home, 'Repos')
    if cwd.startswith(repos + os.sep):
        return os.path.join(repos, cwd[len(repos) + 1:].split(os.sep)[0])
    d = cwd
    while True:
        if any(os.path.exists(os.path.join(d, m)) for m in ('.claude', '.git', 'CLAUDE.md', 'VALIDATION.md', '.contract')):
            return d
        parent = os.path.dirname(d)
        if parent == d or d == home:
            return cwd
        d = parent

def list_file(root):
    for c in ('.claude/mandatory.txt', 'gates/mandatory.txt', 'MANDATORY-READING.txt'):
        p = os.path.join(root, c)
        if os.path.exists(p):
            return p
    return None

def line_count(path):
    with open(path, 'rb') as f:
        n = sum(1 for _ in f)
    return max(n, 1)

def _resolve(specs, root):
    out = []
    for raw in specs:
        raw = raw.strip()
        if not raw or raw.startswith('#'):
            continue
        spec, mode, arg = raw, '', 0
        m = re.match(r'^(.*?):(tail|newest):(\d+)$', raw)
        if m:
            spec, mode, arg = m.group(1), m.group(2), int(m.group(3))
        spec = os.path.expanduser(spec)
        if not os.path.isabs(spec):
            spec = os.path.join(root, spec)
        paths = sorted(glob.glob(spec)) if any(c in spec for c in '*?[') else ([spec] if os.path.exists(spec) else [])
        paths = [p for p in paths if os.path.isfile(p)]
        if mode == 'newest':
            paths = paths[-arg:]
        for p in paths:
            n = line_count(p)
            out.append((p, max(1, n - arg + 1) if mode == 'tail' else 1, n))
    return out

def mandatory(root):
    """The project's mandatory reading set: its list file if it has one, else every rule file it has."""
    lf = list_file(root)
    specs = open(lf, encoding='utf-8').read().splitlines() if lf else DEFAULT_SET
    return _resolve(specs, root)

def receipt_path(session_id):
    os.makedirs(RECEIPTS, exist_ok=True)
    return os.path.join(RECEIPTS, re.sub(r'[^A-Za-z0-9_-]', '_', session_id or 'unknown') + '.json')

def load(session_id):
    p = receipt_path(session_id)
    if os.path.exists(p):
        try:
            return json.load(open(p))
        except Exception:
            pass
    return {'session': session_id, 'started': time.time(), 'windows': {}, 'pending': {}, 'frozen': {}}

def save(session_id, state):
    json.dump(state, open(receipt_path(session_id), 'w'), indent=1)

def mandatory_for(state, root):
    """The set FROZEN per session and per project at first sight, so a session's own handoff or appended
    line never locks that session out. A new session resolves afresh."""
    fz = state.setdefault('frozen', {})
    if isinstance(fz, list):            # receipts written before per-project freezing
        fz = state['frozen'] = {root: fz}
    if root not in fz:
        fz[root] = [[p, s, e] for p, s, e in mandatory(root)]
    return [tuple(x) for x in fz[root]]

def record(state, path, a, b):
    path = os.path.abspath(path)
    w = state['windows'].setdefault(path, [])
    w.append([int(a), int(b)]); w.sort()
    merged = []
    for s, e in w:
        if merged and s <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    state['windows'][path] = merged

def missing(state, root):
    out = []
    for p, s, e in mandatory_for(state, root):
        have = state['windows'].get(os.path.abspath(p), [])
        cur, gaps = s, []
        for a, b in have:
            if b < cur:
                continue
            if a > cur:
                gaps.append((cur, min(a - 1, e)))
            cur = max(cur, b + 1)
            if cur > e:
                break
        if cur <= e:
            gaps.append((cur, e))
        if gaps:
            out.append((p, gaps))
    return out

def rel(p, root):
    p = os.path.abspath(p); home = os.path.expanduser('~')
    return p.replace(root + os.sep, '').replace(home, '~')
