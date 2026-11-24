"""Run C child: run the isolated rebuild with STRUCTURES row order shuffled.

Shuffle happens on a mirror copy inside evidence/p6_isolated_entry/mirror/
(the real ledger is never touched).  INPUTS/run_id stay anchored to the real
files, so the run id matches A/B; the output lands in its own --base dir.
"""
import csv
import hashlib
import io
import random
import shutil
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO / "scripts/wp_production"))
import rebuild_strict_isolated as r  # noqa: E402

MIRROR_DIR = HERE / "mirror"


def main() -> int:
    MIRROR_DIR.mkdir(parents=True, exist_ok=True)
    mirror = MIRROR_DIR / "production_ensemble_structures_shuffled.csv"
    with r.STRUCTURES.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
        fields = list(rows[0].keys())
    random.Random(20261103).shuffle(rows)                       # deterministic permutation
    with mirror.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print("mirror sha256 =", hashlib.sha256(mirror.read_bytes()).hexdigest(), "rows =", len(rows))
    r.STRUCTURES = mirror                                       # only the row order changes
    sys.argv = ["rebuild_strict_isolated.py"] + sys.argv[1:]
    r.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
