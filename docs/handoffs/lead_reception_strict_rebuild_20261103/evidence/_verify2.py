import re, hashlib, os, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
txt = open('SUMMARY_draft.md', encoding='utf-8').read()
ok = miss = mism = skip = 0
for line in txt.splitlines():
    if not line.startswith('|'): continue
    m = re.match(r'\|\s*\*\*?([^|]+?)\*\*?\s*\|\s*\*\*?`?([^|]+?)`?\s*\|?\s*\*\*?$', line) or re.match(r'\|\s*`?([^|]+?)`?\s*\|\s*`?([^|]+?)`?\s*\|', line)
    if not m: continue
    names_raw, hashes_raw = m.group(1).strip(), m.group(2).strip()
    if 'HEAD' in names_raw: skip += 1; continue
    names = [re.sub(r'（.*?）', '', x).strip() for x in re.split(r'\s*/\s*', names_raw)]
    hashes = [h.strip().rstrip('…') for h in re.split(r'\s*/\s*', hashes_raw.strip('*` '))]
    if not all(re.fullmatch(r'[0-9a-f]{8,64}', h) for h in hashes): continue
    if len(names) != len(hashes):
        print('COUNT-DIFF', names_raw, len(names), len(hashes)); mism += 1; continue
    for n, h in zip(names, hashes):
        if not os.path.isfile(n): print('NOTFOUND', n); miss += 1; continue
        got = hashlib.sha256(open(n, 'rb').read()).hexdigest()
        if h in got: ok += 1
        else: print('MISMATCH', n, h[:16], got[:16]); mism += 1
print(f'FINAL: OK {ok} | NOTFOUND {miss} | MISMATCH {mism} | HEAD skip {skip}')
