import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import emit_wp2 as e
src = e.baseline_source()
names = [n for n in dir(e) if n.startswith("ANCHOR_")]
bad = 0
for n in sorted(names):
    a = getattr(e, n)
    c = src.count(a)
    if c != 1:
        bad += 1
    print("%-22s count=%d" % (n, c))
print("BAD=%d" % bad)
