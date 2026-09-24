#!/usr/bin/env python3
"""Prints the project's mandatory reading set in numbered chunks small enough to land in context whole,
and records each chunk on the session's receipt. For sessions that read through Bash.

    python3 ~/.claude/gates/read-in.py          list the chunks (run from the project folder)
    python3 ~/.claude/gates/read-in.py 7        print chunk 7 (and record it)
"""
import sys, os, glob, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gatelib as G
CHUNK = 7000

def session_id():
    sid = os.environ.get('CLAUDE_SESSION_ID')
    if sid:
        return sid
    files = sorted(glob.glob(os.path.join(G.RECEIPTS, '*.json')), key=os.path.getmtime)
    return json.load(open(files[-1]))['session'] if files else 'unknown'

def main():
    root = G.project_root(); sid = session_id(); st = G.load(sid)
    items = G.mandatory_for(st, root); G.save(sid, st)
    cs = []
    for p, s, e in items:
        lines = open(p, encoding='utf-8', errors='replace').read().splitlines()[s - 1:e]
        i = 0
        while i < len(lines):
            size, j = 0, i
            while j < len(lines) and size + len(lines[j]) + 1 <= CHUNK:
                size += len(lines[j]) + 1; j += 1
            if j == i: j = i + 1
            cs.append((p, s + i, s + j - 1, '\n'.join(lines[i:j]))); i = j
    if len(sys.argv) < 2:
        print('%d chunks in the mandatory set for %s. Print each one: read-in.py <n>' % (len(cs), root))
        for k, (p, a, b, _) in enumerate(cs, 1):
            print('  %3d  %s  lines %d-%d' % (k, G.rel(p, root), a, b))
        return
    k = int(sys.argv[1])
    if not 1 <= k <= len(cs):
        sys.exit('no chunk %d; there are %d' % (k, len(cs)))
    p, a, b, body = cs[k - 1]
    print('===== chunk %d of %d · %s · lines %d-%d =====' % (k, len(cs), G.rel(p, root), a, b)); print(body)
    G.record(st, p, a, b); G.save(sid, st)
    left = G.missing(st, root)
    print('===== recorded. %s =====' % ('receipt complete' if not left else '%d file(s) still have unread lines' % len(left)))

if __name__ == '__main__':
    main()
