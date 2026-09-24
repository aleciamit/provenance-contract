#!/usr/bin/env python3
"""A UI check the Stop hook can hold a turn against. Copy it into a project as uicheck.py, edit the
CONFIG block, and point .claude/uigate.json at it:

    {"files": ["index.html"], "marker": ".uicheck-ok", "command": "python3 uicheck.py"}

What it does, per state: loads the URL in headless Chrome, waits for the page to settle, reads the
rendered DOM and the console, and fails the state when the console reports an error (an uncaught
exception, a ReferenceError, a TypeError, a failed resource) or when the page rendered nothing where
something was expected. It writes the marker file only when every state passes. It does not judge how
the page looks; the owner does that. It catches the class of bug a syntax check cannot see, such as a
script that parses and then throws before it draws, leaving a blank page.

    python3 uicheck.py
"""
import subprocess, sys, os, time, select, urllib.request, http.server, threading, socketserver

# ---- CONFIG: edit for the project ---------------------------------------------------------------
BASE = 'http://localhost:3470'                 # where the page is served; see SERVE_DIR to serve a folder
SERVE_DIR = os.path.dirname(os.path.abspath(__file__))   # folder to serve when BASE is not already answering; '' to never serve
STATES = ['/index.html']                       # every URL (path or path?query) the check loads
EXPECT = {                                     # per state: strings that must appear in the rendered DOM, and how many times at least
    '/index.html': {'<main': 1},
}
MARKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.uicheck-ok')
CHROME = os.environ.get('CHROME', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
SETTLE_MS = 4000
# --------------------------------------------------------------------------------------------------

PROFILE = '/tmp/uicheck-profile-%d' % os.getpid()
ERROR_MARKS = ('ERROR:CONSOLE', 'Uncaught', 'ReferenceError', 'TypeError', 'SyntaxError', 'Failed to load resource', 'net::ERR')

def reachable(url):
    try:
        urllib.request.urlopen(url, timeout=3); return True
    except Exception:
        return False

def serve(folder, port):
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k): super().__init__(*a, directory=folder, **k)
        def log_message(self, *a): pass
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.TCPServer(('127.0.0.1', port), Quiet)
    threading.Thread(target=srv.serve_forever, daemon=True).start(); return srv

def load(url):
    """Rendered DOM and console lines. Chrome writes the DOM and then hangs on this platform, so read
    until </html> or the deadline, then kill it."""
    subprocess.run(['rm', '-rf', PROFILE])
    log = open(PROFILE + '.log', 'w')
    p = subprocess.Popen([CHROME, '--headless', '--disable-gpu', '--disable-crashpad', '--disable-component-update',
                          '--disable-background-networking', '--enable-logging=stderr', '--v=0',
                          '--user-data-dir=' + PROFILE, '--no-first-run', '--virtual-time-budget=%d' % SETTLE_MS, '--dump-dom', url],
                         stdout=subprocess.PIPE, stderr=log)
    buf, t = b'', time.time()
    while time.time() - t < 30:
        r, _, _ = select.select([p.stdout], [], [], 0.5)
        if r:
            chunk = os.read(p.stdout.fileno(), 65536)
            if not chunk: break
            buf += chunk
            if b'</html>' in buf: break
    p.kill(); p.wait(); log.close()
    console = [l.strip() for l in open(PROFILE + '.log', errors='replace') if 'CONSOLE' in l or 'ERROR' in l]
    subprocess.run(['rm', '-rf', PROFILE, PROFILE + '.log'])
    return buf.decode('utf-8', 'replace'), console

def main():
    srv = None
    if not reachable(BASE) and SERVE_DIR:
        port = int(BASE.rsplit(':', 1)[-1].split('/')[0]); srv = serve(SERVE_DIR, port); time.sleep(0.5)
    fails = 0
    print('  %-32s %7s %8s  %s' % ('state', 'dom', 'errors', 'verdict'))
    for st in STATES:
        dom, console = load(BASE + st)
        errors = [c for c in console if any(m in c for m in ERROR_MARKS)]
        why = []
        if len(dom) < 200: why.append('nothing rendered')
        for needle, n in EXPECT.get(st, {}).items():
            if dom.count(needle) < n: why.append('expected %r x%d, found %d' % (needle, n, dom.count(needle)))
        if errors: why.append('%d console error(s): %s' % (len(errors), errors[0][:90]))
        ok = not why; fails += 0 if ok else 1
        print('  %-32s %7d %8d  %s %s' % (st, len(dom), len(errors), 'ok  ' if ok else 'FAIL', '; '.join(why)))
    if srv: srv.shutdown()
    if fails:
        print('%d state(s) failed; the marker was not written' % fails); sys.exit(1)
    open(MARKER, 'w').write(time.strftime('%Y-%m-%d %H:%M')); print('all states passed; marker written: ' + MARKER)

if __name__ == '__main__':
    main()
