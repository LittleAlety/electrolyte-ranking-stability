"""WP5 tasks A/B: the 12-molecule QC-labelled target pools (v2 input contract).

The legacy C/M/E replay ran on week7 features against y_* columns that are
NOT the production labels.  The plan's acceptance contract needs two task
pools derived from the FINAL ensemble ledger instead:

* task A -- free oxidation label: G_ensemble(M_plus) - G_ensemble(M), eV,
  one row per molecule, from accepted-or-labelled states with a provenance
  column that says which acceptance_status each leg carries;
* task B -- Li shift label: G_ensemble(LiM_2plus) - G_ensemble(LiM_plus), eV,
  same structure.  (Acquiring the free labels is a COST B has to account
  for; the cost linkage stays a separate ledger concern -- MISSING when the
  per-query mapping is not traceable, never fabricated.)

Outputs (new, nothing existing is touched):

    active_learning/blind_replay/target_pool_AB.csv
    active_learning/blind_replay/target_pool_AB_index.json

``--check`` recomputes in memory and byte-compares.  Determinism: the pool is
a pure projection of the labels CSV, so identical inputs give identical
bytes; the index pins the labels sha256.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

LABELS = REPO / "outputs" / "physics_completion" / "ensembles" / "production_ensemble_labels.csv"
OUTDIR = REPO / "outputs" / "physics_completion" / "active_learning" / "blind_replay"
OUT_CSV = OUTDIR / "target_pool_AB.csv"
OUT_INDEX = OUTDIR / "target_pool_AB_index.json"

EH_TO_EV = 27.211386245988

#: v3.0 §13.1 contract:
#:   task A  -- S_f  = Gox_free_ensemble   = G_ens(M+) - G_ens(M)
#:   task B  -- D_c  = coordination_shift  = S_Li - S_f, with S_Li restored
#:              as S_f + D_c (the li = free + shift identity is TESTED row by
#:              row; the bare Li two-state difference is S_Li, NOT the shift).
TASKS = {
    "A": ("M_plus", "M"),
    "B": ("LiM_2plus", "LiM_plus"),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def build_rows() -> list[dict]:
    with LABELS.open(encoding="utf-8") as fh:
        labels = list(csv.DictReader(fh))
    by_key = {(r["name"], r["state"]): r for r in labels}

    def _g(name, state):
        row = by_key.get((name, state))
        return _f(row.get("g_ensemble_eh")) if row else None

    def _pair_ok(name, hi_state, lo_state):
        hi = by_key.get((name, hi_state))
        lo = by_key.get((name, lo_state))
        if not hi or not lo:
            return False, "", ""
        ok = (hi.get("acceptance_status") == "accepted"
              and lo.get("acceptance_status") == "accepted")
        return ok, hi.get("limitation_reason", ""), lo.get("limitation_reason", "")

    rows = []
    for task, (hi_state, lo_state) in TASKS.items():
        for name in sorted({r["name"] for r in labels}):
            g_hi, g_lo = _g(name, hi_state), _g(name, lo_state)
            if g_hi is None or g_lo is None:
                continue
            ok, hi_lim, lo_lim = _pair_ok(name, hi_state, lo_state)
            base = {
                "task": task, "name": name,
                "hi_acceptance": by_key[(name, hi_state)]["acceptance_status"],
                "lo_acceptance": by_key[(name, lo_state)]["acceptance_status"],
                "hi_limitation": hi_lim, "lo_limitation": lo_lim,
                "qc_complete_pair": str(ok),
                "pool_label": "wp5_AB_target_pool_v1",
            }
            if task == "A":
                base["label_S_f_ev"] = "%.9f" % ((g_hi - g_lo) * EH_TO_EV)
                rows.append(base)
                continue
            # task B: the three columns + the identity test (v3.0 §13.1)
            s_f = (_g(name, "M_plus") - _g(name, "M")) * EH_TO_EV
            s_li = (g_hi - g_lo) * EH_TO_EV
            shift = s_li - s_f
            base["label_S_f_ev"] = "%.9f" % s_f
            base["label_S_Li_ev"] = "%.9f" % s_li
            base["label_D_coord_ev"] = "%.9f" % shift
            base["identity_li_equals_free_plus_shift"] = str(
                abs(s_li - (s_f + shift)) < 1e-9)
            rows.append(base)
    return rows

def _fields_of(rows: list[dict]) -> list[str]:
    """Union of keys across BOTH tasks, stable order, task label columns first."""
    base = ["task", "name"]
    labels = []
    for r in rows:
        for k in r:
            if k.startswith("label_") and k not in labels:
                labels.append(k)
    rest = []
    for r in rows:
        for k in r:
            if k not in base and k not in labels and k not in rest:
                rest.append(k)
    return base + labels + rest





def write_outputs(rows: list[dict]) -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    fields = _fields_of(rows)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    index = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "inputs": {str(LABELS.relative_to(REPO)): _sha256(LABELS)},
        "contract": {
            "task_A": "free oxidation shift from FINAL production ensemble labels",
            "task_B": "Li-conditioned shift; the cost of acquiring free "
                      "labels is part of B's budget linkage (cost ledger "
                      "stays separate; MISSING when not traceable)",
            "label_version": "production_ensemble_labels.csv (same version "
                             "as the aggregation step; pinned by input sha256)",
            "qc_pair_column": "qc_complete_pair marks both-legs-accepted rows; "
                              "non-complete pairs stay in the pool with their "
                              "acceptance status visible, never silently dropped",
        },
        "n_rows": len(rows),
    }
    OUT_INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8", newline="\n")


def check() -> int:
    rows = build_rows()
    fields = _fields_of(rows)
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    disk = OUT_CSV.read_text(encoding="utf-8") if OUT_CSV.is_file() else ""
    if disk != buf.getvalue():
        print("CHECK FAILED -- %s drifted" % OUT_CSV.name)
        return 1
    print("CHECK OK -- A/B target pool matches recomputation")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="READ-ONLY: recompute in memory and byte-compare")
    args = ap.parse_args(argv)
    if args.check:
        return check()
    rows = build_rows()
    write_outputs(rows)
    print("wrote %s rows=%d" % (OUT_CSV.name, len(rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
