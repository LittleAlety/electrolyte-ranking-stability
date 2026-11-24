# -*- coding: utf-8 -*-
"""Final candidate entry: calls the sole consumer, then builds the split rollup
and the annex index. Refuses to overwrite differing existing outputs."""

from pathlib import Path as _ReorgPath
import sys as _reorg_sys

_reorg_sys.path.insert(0, str(_ReorgPath(__file__).resolve().parents[1]))
import _paths  # noqa: F401,E402  (仓库根 + scripts/production/* 注册到 sys.path)

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha_text(b):
    return hashlib.sha256(b).hexdigest()


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def write_or_refuse(path, data: bytes, label):
    p = Path(path)
    if p.exists():
        if p.read_bytes() == data:
            print("UNCHANGED: %s" % label)
            return 0
        print("REFUSED: existing %s differs; not overwritten" % label)
        return 1
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    print("WROTE: %s" % label)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--batch", required=True)
    ap.add_argument("--main", required=True)
    ap.add_argument("--rollup", required=True)
    ap.add_argument("--index", required=True)
    ap.add_argument("--consumer", default=str(_paths.script_path("apply_settlement_batch.py")))
    a = ap.parse_args(argv)

    # the entry itself invokes the sole consumer (does not require a prior run)
    r = subprocess.run([sys.executable, a.consumer, "--ledger", a.ledger,
                        "--batch", a.batch], capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        print("REFUSED: consumer exit %d; nothing written" % r.returncode)
        return r.returncode
    led = load(a.ledger)
    rows = list(csv.DictReader(open(a.main, encoding="utf-8")))
    core = [float(x["core_hours"]) for x in rows if x.get("core_hours")]
    hpc = [float(x["hpc_core_hours"]) for x in rows if x.get("hpc_core_hours")]
    ex = sum(Fraction(x["core_hours_exact_fraction"]) for x in led["rows"])
    rollup = {
        "main_production_core_hours": {"n_rows": len(rows), "nonblank": len(core), "sum": round(sum(core), 6)},
        "main_production_hpc_core_hours": {"nonblank": len(hpc), "sum": round(sum(hpc), 6),
                                           "missing": len(rows) - len(hpc)},
        "settlement_batch_slurm_actual": {"n_rows": len(led["rows"]), "exact": str(ex),
                                           "display": round(float(ex), 6)},
        "mixed_total_emitted": False,
    }
    rb = (json.dumps(rollup, ensure_ascii=False, indent=2) + "\n").encode()
    rc = write_or_refuse(a.rollup, rb, "rollup")
    if rc:
        return rc
    led_b = Path(a.ledger).read_bytes()
    roll_b = Path(a.rollup).read_bytes()
    index = {
        "schema": "lead2/cost/settlement_batch_index/v1",
        "scope": "settlement_batch_annex_only",
        "not_project_total": True,
        "ledger": {"path": Path(a.ledger).name, "sha256": sha_text(led_b)},
        "rollup": {"path": Path(a.rollup).name, "sha256": sha_text(roll_b)},
        "status": {"record_exists": True, "formal_aggregation_integrated": False, "reservation_released": False},
    }
    ib = (json.dumps(index, ensure_ascii=False, indent=2) + "\n").encode()
    return write_or_refuse(a.index, ib, "index")


if __name__ == "__main__":
    sys.exit(main())
