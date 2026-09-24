#!/usr/bin/env python3
"""Her writing rules, as a sweep over ONE file (Markdown, text or HTML). Reports only; never edits.
The patterns are the ones in portfolio-site/tools/final-sweep.py, applied to the file's prose."""
import re, sys, html
WORDS = r"\b(argue[ds]?|arguing|argument|silently|quietly|quieter|simply|genuinely|merely|cheap|cheaper|drew|drawn|receipts?|afterwards|towards|backwards|any more|whilst|amongst|pushed back|pushback|stochastic|through[- ]line|owe[ds]?|garbled|browser tab|talk it round|won the|winning|vouch|leverage|cadence|socialize|operationalize)\b"
END = r"([^.\n!?]{25,}?)\b(of|to|for|with|about|from|by|into|through|against|on|at|does|do|did|is|isn't|was|are|were|has|had|have|won't|can|could|would|will)([.!?])(?=\s|$)"
def prose(path):
    s = open(path, encoding='utf-8', errors='replace').read()
    if path.endswith('.html'):
        b = s[s.find('<main'):] if '<main' in s else s
        b = re.sub(r'<(script|style).*?</\1>', '', b, flags=re.S); b = re.sub(r'<!--.*?-->', '', b, flags=re.S)
        b = re.sub(r'</(p|h1|h2|h3|li|div|figcaption|td|dd|dt|blockquote)>', '\n', b)
        s = html.unescape(re.sub(r'<[^>]+>', '', b))
    return re.sub(r'[ \t]+', ' ', s)
def main():
    path = sys.argv[1]; t = prose(path); hits = []
    for m in re.finditer(WORDS, t, re.I): hits.append(('word', t[max(0, m.start() - 40):m.end() + 25].replace('\n', ' ')))
    for m in re.finditer(END, t): hits.append(('ending', '...' + m.group(0)[-70:].replace('\n', ' ')))
    for m in re.finditer(r'(^|[.!?:]\s+|\n\s*)So,? [a-zA-Z]', t): hits.append(('So opener', t[m.start():m.start() + 60].replace('\n', ' ').strip()))
    if '—' in t: hits.append(('em dash', '%d found' % t.count('—')))
    if re.search(r'\b(about|roughly|around|takes?|took)\s+(an?\s+)?(\d+|ten|twenty|thirty|forty|few|couple of)\s*(minutes?|hours?|days?|weeks?)\b', t, re.I): hits.append(('time estimate', 'a duration in the text; she banned them'))
    for k, h in hits[:25]: print('  [%s] %s' % (k, h[:140]))
    print('%d hits' % len(hits))
if __name__ == '__main__':
    main()
