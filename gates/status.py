#!/usr/bin/env python3
"""Shows the reading receipt for the running session and the current project."""
import sys, os, glob, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gatelib as G
root = G.project_root()
files = sorted(glob.glob(os.path.join(G.RECEIPTS, '*.json')), key=os.path.getmtime)
if not files:
    sys.exit('no receipt yet; the SessionStart hook creates one')
st = json.load(open(files[-1])); miss = G.missing(st, root)
print('session', st['session'][:8], '| project', root, '|', 'complete' if not miss else 'INCOMPLETE')
for p, gaps in miss:
    print('  unread  %s  lines %s' % (G.rel(p, root), ', '.join('%d-%d' % g for g in gaps)))
for p, s, e in G.mandatory_for(st, root):
    if all(p != m[0] for m in miss):
        print('  read    %s  lines %d-%d' % (G.rel(p, root), s, e))
