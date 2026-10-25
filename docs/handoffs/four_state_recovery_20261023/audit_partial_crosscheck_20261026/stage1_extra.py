#!/usr/bin/env python
# Stage-1 enrichment: numbers a sampling-audit report is likely to assert.
# (a) SHA256 of the four inputs (compare to sampling_audit_index.json)
# (b) round-2 exec CSV row count + status tally
# (c) LI_ROUND2 top-level totals block
# (d) free-conformer source rows inside the 6 kcal window for M / M_plus
from __future__ import annotations
import csv, json, hashlib
from pathlib import Path
REPO = Path(r"E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code")
SAMP = REPO / "outputs" / "physics_completion" / "sampling"
ENS  = REPO / "outputs" / "physics_completion" / "ensembles"
CONFORMERS = SAMP / "sampling_conformer_set.csv"
LI_SCREEN = REPO / "outputs" / "physics_completion" / "li_motif_sampling" / "li_motif_screen.json"
LI_ROUND2 = REPO / "outputs" / "physics_completion" / "li_motif_sampling" / "li_motif_round2_exec_index.json"
STRUCTURES = ENS / "production_ensemble_structures.csv"
EXEC_CSV = LI_ROUND2.parent / "li_motif_round2_exec.csv"
IDX = SAMP / "sampling_audit_index.json"
AUDIT = ("EMC","DEC","DME","TMP")
WINDOW=6.0
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def num(v):
    try: return float(v)
    except (TypeError,ValueError): return None

print("== (a) input SHA256 (mine) vs index ==")
idx = json.loads(IDX.read_text(encoding="utf-8"))
inputs = {"sampling_conformer_set.csv":CONFORMERS,"li_motif_screen.json":LI_SCREEN,
          "li_motif_round2_exec_index.json":LI_ROUND2,"production_ensemble_structures.csv":STRUCTURES}
for name,p in inputs.items():
    mine=sha(p); theirs=idx["inputs"].get(name)
    print(f"{name}: mine={mine} index={theirs} match={mine==theirs}")

print("== (b) exec CSV ==")
rows=list(csv.DictReader(EXEC_CSV.open(encoding="utf-8")))
print("exec_csv rows =", len(rows))
cols=rows[0].keys() if rows else []
print("exec_csv columns =", list(cols))
# tally by any status-like column
for key in ("status","result","outcome"):
    if key in cols:
        t={}
        for r in rows: t[r[key]]=t.get(r[key],0)+1
        print(f"exec_csv tally by '{key}' =", t); break
print("index LI_ROUND2 exec_csv_sha256 =", json.loads(LI_ROUND2.read_text(encoding='utf-8')).get("exec_csv_sha256"))
print("exec_csv_sha256 match =", sha(EXEC_CSV)==json.loads(LI_ROUND2.read_text(encoding='utf-8')).get("exec_csv_sha256"))

print("== (c) LI_ROUND2 totals block ==")
r2=json.loads(LI_ROUND2.read_text(encoding="utf-8"))
print("totals =", json.dumps(r2.get("totals"), ensure_ascii=False))
print("n_checks =", r2.get("n_checks"), " n_failed =", r2.get("n_failed"))

print("== (d) free-conformer rows inside 6 kcal window for M / M_plus ==")
allr=list(csv.DictReader(CONFORMERS.open(encoding="utf-8")))
print("conformer header =", list(allr[0].keys()) if allr else [])
for name in AUDIT:
    for st in ("M","M_plus"):
        sel=[r for r in allr if r.get("name")==name and r.get("state")==st and num(r.get("rel_kcal")) is not None and num(r.get("rel_kcal"))<=WINDOW]
        r1=sum(1 for r in sel if str(r.get("selected_round1","")).strip().lower()=="true")
        idcol = "conformer_id" if "conformer_id" in (allr[0].keys() if allr else []) else ("id" if allr and "id" in allr[0] else None)
        ids=[(r.get(idcol), r.get("rel_kcal"), r.get("selected_round1")) for r in sel] if idcol else []
        print(f"{name}|{st}: window_count={len(sel)} round1_selected={r1}  rows={ids}")
