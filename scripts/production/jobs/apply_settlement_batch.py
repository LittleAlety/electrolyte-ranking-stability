# -*- coding: utf-8 -*-
"""Single settlement-batch consumer (candidate for release).

CLI: --ledger PATH --batch JSON [--dry-run]
Exit 0: applied or NO-OP. Exit 1: refused, nothing written.
"""

from pathlib import Path as _ReorgPath
import sys as _reorg_sys

_reorg_sys.path.insert(0, str(_ReorgPath(__file__).resolve().parents[1]))
import _paths  # noqa: F401,E402  (仓库根 + scripts/production/* 注册到 sys.path)

import argparse
import json
import os
import sys
import tempfile
from fractions import Fraction


def load(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def frac(row):
    return Fraction(row["core_hours_exact_fraction"])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--batch", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    batch = load(a.batch)
    keys = [r["normalized_key"] for r in batch["rows"]]
    dup = sorted({k for k in keys if keys.count(k) > 1})
    if dup:
        print("REFUSED: duplicate key inside batch: %s; nothing written" % dup)
        return 1
    ledger = load(a.ledger) if os.path.exists(a.ledger) else {"schema": batch["schema"], "rows": []}
    lkeys = [r["normalized_key"] for r in ledger.get("rows", [])]
    ldup = sorted({k for k in lkeys if lkeys.count(k) > 1})
    if ldup:
        print("REFUSED: duplicate key in existing ledger: %s; nothing written" % ldup)
        return 1
    by_key = {r["normalized_key"]: r for r in ledger.get("rows", [])}
    add, skip, conflict = [], [], []
    for r in batch["rows"]:
        k = r["normalized_key"]
        if k in by_key:
            (skip if frac(by_key[k]) == frac(r) else conflict).append(k)
        else:
            add.append(k)
    if conflict:
        print("REFUSED: conflicting core-hours: %s; nothing written" % conflict)
        return 1
    if not add:
        print("NO-OP: nothing appended (skipped=%d); no write" % len(skip))
        return 0
    if a.dry_run:
        print("DRY-RUN: would append %d, skip %d" % (len(add), len(skip)))
        return 0
    rows = list(ledger.get("rows", [])) + [r for r in batch["rows"] if r["normalized_key"] in set(add)]
    total = sum(frac(r) for r in rows)
    expected = Fraction(batch["totals"]["core_hours_exact"])
    if total != expected:
        print("REFUSED: recomputed total %s != declared %s; nothing written" % (total, expected))
        return 1
    ledger["rows"] = rows
    ledger["totals"] = dict(batch["totals"], recomputed_from_rows=str(total))
    d = os.path.dirname(os.path.abspath(a.ledger))
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(ledger, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, a.ledger)
    print("OK: appended=%d skipped=%d total=%s" % (len(add), len(skip), total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
