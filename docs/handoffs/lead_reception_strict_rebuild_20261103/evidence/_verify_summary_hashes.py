import re, hashlib, os, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
txt = open('SUMMARY_draft.md', encoding='utf-8').read()
for pat in ('待补', '待交付', '【待'):
    for m in re.finditer(re.escape(pat), txt):
        print('PLACEHOLDER line', txt[:m.start()].count('\n') + 1, pat)
# 表行：| **name** | `prefix…` 或全哈希
rows = re.findall(r'\|\s*\**`?([^|\n]+?)`?\**\s*\|\s*\**`?([0-9a-f]{8,64})', txt)
ok = miss = mism = 0
for name, exp in rows:
    name = name.strip().strip('*`')
    if not os.path.isfile(name):
        print('NOTFOUND', name); miss += 1; continue
    got = hashlib.sha256(open(name, 'rb').read()).hexdigest()
    if got.startswith(exp.rstrip('…')) or exp.rstrip('…') in got:
        ok += 1
    else:
        print('MISMATCH', name, 'exp', exp[:20], 'got', got[:20]); mism += 1
print(f'hash rows: {len(rows)} | OK {ok} | MISS {miss} | MISMATCH {mism}')
