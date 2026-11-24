# 抽验 A1 文内哈希清单（只读）；运行：PYTHONIOENCODING=utf-8 python docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/a1_hash_spotcheck.py
import re
import hashlib
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(__file__).resolve().parents[4]
txt = (ROOT / "docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/A1_five_state_coverage.md").read_text(encoding="utf-8")

# 行形如：`path` | `64hex`  或  path：`64hex`
pairs = []
for line in txt.splitlines():
    h = re.findall(r"\b[0-9a-f]{64}\b", line)
    if not h:
        continue
    # 路径候选：含 / 或 . 的反引号片段或裸路径
    cands = re.findall(r"`([^`\s]+\.(?:csv|json|md|txt|xyz|log))`", line)
    if not cands:
        cands = re.findall(r"([\w./\\-]+\.(?:csv|json|md|txt|xyz|log))", line)
    if cands:
        pairs.append((cands[0], h[0]))

print("提取到", len(pairs), "对")
checked = bad = missing = 0
for p, h in pairs[:30]:
    pp = Path(p)
    if not pp.is_absolute():
        pp = ROOT / p
    if pp.exists():
        a = hashlib.sha256(pp.read_bytes()).hexdigest()
        if a == h:
            print("OK      ", pp.name, h[:16])
            checked += 1
        else:
            print("MISMATCH", pp.name, "listed=", h[:16], "actual=", a[:16])
            bad += 1
    else:
        print("NOTFOUND", p)
        missing += 1
print(f"summary: ok={checked} mismatch={bad} notfound={missing} (前30对)")
