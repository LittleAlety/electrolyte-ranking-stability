

from pathlib import Path as _ReorgPath
import sys as _reorg_sys

_reorg_sys.path.insert(0, str(_ReorgPath(__file__).resolve().parents[1]))
import _paths  # noqa: F401,E402  (仓库根 + scripts/production/* 注册到 sys.path)

import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
REPO = _paths.REPO_ROOT
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
