#!/usr/bin/env python3
"""The checker. Run it before handing anything back; a non-zero exit blocks the build.

    python3 tools/check.py            # checks the current directory
    python3 tools/check.py example    # checks another root

Six things go wrong in a hand-built site with no error anywhere, and all six are checked here:

  1. A class exists in the markup and no linked stylesheet defines it. The page renders
     as unstyled text with no error anywhere.
  2. A stylesheet, script, image or page link points at a file that is not there.
  3. Tag counts do not balance.
  4. A </div> closes more than is open, or <main> does not end at depth zero. Balanced
     counts prove nothing about nesting order; this walk does.
  5. An em-dash reaches the page.
  6. A scrubbed term reaches a page, an asset or a file name. The list is read from
     SCRUB.local.md, which is never committed. If the list exists and fails to parse,
     the checker refuses to report clean.

It cannot catch a class that exists but is wrong for the job. Only reading catches that.
"""
import re, sys, os, glob

ROOT     = sys.argv[1] if len(sys.argv) > 1 else '.'
EXCLUDE  = {'node_modules', 'backup', 'dist', 'vendor', '.git'}   # folder names skipped
IGNORE   = set()             # markup-only class names with no styling of their own
ASSET_EXT = ('.css', '.js')  # non-page files that also get the scrub check
EM       = chr(0x2014)      # the em-dash, kept out of this file's own source
BALANCED = ('div', 'p', 'section', 'a', 'ul', 'ol', 'li', 'span', 'main', 'article')

fail = 0
def bad(kind, page, msg):
    global fail
    print("  %-12s %s  %s" % (kind, page, msg)); fail = 1

def rel(p):
    return os.path.relpath(p, ROOT)

# ---- the scrub list ---------------------------------------------------------------

def scrub_patterns():
    path = os.path.join(ROOT, 'SCRUB.local.md')
    if not os.path.exists(path):
        print("  NOTE         SCRUB.local.md not found, scrub check skipped")
        return [], []
    src = open(path, encoding='utf-8').read()
    if '## Never reintroduce' not in src:
        print("  SCRUB PARSE  no '## Never reintroduce' heading, refusing to report clean")
        return None, None
    section = src.split('## Never reintroduce')[1]
    section = section.split('Nothing below this line is parsed as a term.')[0]
    terms = sorted({t.strip() for t in re.findall(r'`([^`]+)`', section) if t.strip()})
    if not terms:
        print("  SCRUB PARSE  zero terms read from SCRUB.local.md, refusing to report clean")
        return None, None
    pats = []
    for t in terms:
        if len(t) <= 3 and t.isupper():      # short codes: case-sensitive, plain boundaries
            pats.append((t, re.compile(r'(?<![A-Za-z0-9])' + re.escape(t) + r'(?![A-Za-z0-9])')))
        else:
            pats.append((t, re.compile(r'(?<![A-Za-z])' + re.escape(t) + r'(?![A-Za-z])', re.I)))
    # Multi-word terms also get matched with every non-alphanumeric stripped, which
    # catches a name written as an email address or a domain.
    squash = [(t, re.compile(re.sub(r'[^a-z0-9]', '', t.lower()))) for t in terms if ' ' in t]
    return pats, squash

def scrub(path, pats, squash):
    text = open(path, encoding='utf-8', errors='replace').read()
    text = re.sub(r'base64,[A-Za-z0-9+/=\s]+', 'base64,', text)   # encoded payloads spell everything
    hits = 0
    flat = re.sub(r'[^a-z0-9]', '', text.lower())
    for term, rx in squash:
        n = len(rx.findall(flat))
        if n:
            bad("SCRUB", rel(path), "%s (run together) x%d" % (term, n)); hits += n
    for term, rx in pats:
        n = len(rx.findall(text))
        if n:
            bad("SCRUB", rel(path), "%s x%d" % (term, n)); hits += n
    return hits

# ---- per-page checks --------------------------------------------------------------

def classes_defined(sheets):
    out = set()
    for p in sheets:
        if os.path.exists(p):
            out |= set(re.findall(r'\.([A-Za-z_][\w-]*)\s*[,{:.\[>~+ ]',
                                  open(p, encoding='utf-8').read() + ' '))
    return out

def links(page, h):
    n = 0
    for ref in re.findall(r'(?:href|src)="([^"]+)"', h):
        if re.match(r'^(https?:|mailto:|tel:|data:|#|//|javascript:)', ref):
            continue
        n += 1
        real = os.path.normpath(os.path.join(os.path.dirname(page),
                                             ref.split('#')[0].split('?')[0]))
        if not os.path.exists(real):
            bad("BROKEN REF", rel(page), "-> %s" % ref)
    return n

def nesting(page, h):
    start = h.find('<main')
    body = h[start:] if start >= 0 else h
    depth, low = 0, 0
    for tok in re.finditer(r'<div\b[^>]*>|</div>', body):
        if tok.group(0).startswith('</'):
            depth -= 1; low = min(low, depth)
        else:
            depth += 1
    if low < 0:
        bad("NESTING", rel(page), "a </div> closes more than is open (min depth %d)" % low)
    if depth != 0:
        bad("NESTING", rel(page), "divs end at depth %d, not 0" % depth)

def pages_under(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE and not d.startswith('.')]
        for f in filenames:
            if f.endswith('.html'):
                out.append(os.path.join(dirpath, f))
    return sorted(out)

pats, squash = scrub_patterns()
if pats is None:
    sys.exit(1)

pages = pages_under(ROOT)
if not pages:
    print("  nothing to check under %s" % ROOT); sys.exit(1)

refs = 0
for page in pages:
    h = open(page, encoding='utf-8', errors='replace').read()
    own = [os.path.normpath(os.path.join(os.path.dirname(page), l))
           for l in re.findall(r'<link[^>]+href="([^"]*\.css)"', h)]
    inline = re.findall(r'<style[^>]*>(.*?)</style>', h, re.S)
    defined = classes_defined(own)
    for block in inline:
        defined |= set(re.findall(r'\.([A-Za-z_][\w-]*)\s*[,{:.\[>~+ ]', block + ' '))
    used = {c for m in re.finditer(r'class="([^"]+)"', h) for c in m.group(1).split()}
    missing = sorted(used - defined - IGNORE)
    refs += links(page, h)
    for tag in BALANCED:
        o = len(re.findall(r'<%s[\s>]' % tag, h)); c = h.count('</%s>' % tag)
        if o != c:
            bad("UNBALANCED", rel(page), "<%s> %d open / %d close" % (tag, o, c))
    nesting(page, h)
    if h.count(EM):
        bad("EM-DASH", rel(page), "%d found" % h.count(EM))
    if pats:
        scrub(page, pats, squash)
    if missing:
        bad("UNDEFINED", rel(page), "%d classes: %s" % (len(missing), ', '.join(missing[:12])))
    else:
        print("  ok           %-32s %3d classes" % (rel(page), len(used)))

if pats:
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE and not d.startswith('.')]
        for f in filenames:
            p = os.path.join(dirpath, f)
            if f.endswith(ASSET_EXT):
                scrub(p, pats, squash)
            for term, rx in pats:
                if rx.findall(f):
                    bad("SCRUB", "filename", "%s in %s" % (term, rel(p)))

print("  %d pages, %d local refs%s" % (len(pages), refs, "" if fail else ", clean"))
sys.exit(fail)
