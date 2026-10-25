"""t6 third-party crosscheck recalculation (READ-ONLY; prints to stdout, writes nothing).

Recomputes every number Lead claimed in P9_READINESS_20261024.md §四之七 from the
current disk, independently (csv.DictReader / module import, never Get-Content).
Run:  .venv/Scripts/python.exe -B <thisfile>
"""
import csv, importlib.util, json, sys
from collections import Counter
from pathlib import Path

REPO = Path(r"E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code")
OUT = REPO / "outputs" / "physics_completion"
sys.dont_write_bytecode = True

def rows(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

print("== A. plan_compliance.md table: line numbers + status distribution ==")
pc = OUT / "compliance" / "plan_compliance.md"
lines = pc.read_text(encoding="utf-8").splitlines()
table, dist = [], Counter()
for i, ln in enumerate(lines, 1):
    s = ln.strip()
    if s.startswith("|") and s.count("|") >= 4 and "item_id" not in s and set(s) - set("|-: "):
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) >= 5:
            item_id = cells[0].strip("`")
            status = cells[3].strip("`") if len(cells) > 3 else ""
            # columns per FIELDS: item_id|plan_section|requirement|status|measured|evidence|note
            # but md table may differ; detect status by membership
            cand = [c.strip("`") for c in cells]
            st = next((c for c in cand if c in
                       ("satisfied","partial","not_satisfied","blocked_on_production","exempt")), None)
            if st:
                table.append((i, item_id, st))
                dist[st] += 1
for want in ("wp2_state_identity_qc", "wp5_pool_extension", "wp6_explicit_ligand"):
    hits = [t for t in table if t[1] == want]
    print("  %-26s -> md-line(s) %s status %s" % (want, [h[0] for h in hits], [h[2] for h in hits]))
print("  total data rows =", len(table), " dist =", dict(dist))
print("  sum check 22+13+3+2+2 =", 22+13+3+2+2, "| open(partial+not_satisfied+blocked) =",
      dist["partial"] + dist["not_satisfied"] + dist["blocked_on_production"])
# the exact 'measured' cells of the three rows
for i, item_id, st in table:
    if item_id in ("wp2_state_identity_qc","wp5_pool_extension","wp6_explicit_ligand"):
        print("  L%d %s status=%s raw=%s" % (i, item_id, st, lines[i-1][:260]))

print("\n== B. defect ①: state_identity scope ==")
qc = rows(OUT / "state_identity" / "state_identity_qc.csv")
print("  state_identity_qc.csv rows =", len(qc))
col = [c for c in (qc[0].keys() if qc else []) if "frontier" in c.lower()]
print("  frontier columns:", col)
if col:
    print("  frontier_localization_status distribution =",
          dict(Counter(r.get(col[0], "") for r in qc)))
acc = rows(OUT / "state_identity" / "state_identity_acceptance.csv")
print("  acceptance rows =", len(acc), "; 12th check (1-based) =",
      {k: acc[11].get(k) for k in ("check_id", "ok")} if len(acc) >= 12 else "N/A",
      "; all keys sample =", acc[0].keys().__iter__().__length_hint__() if acc else 0)
print("  acceptance check_id+ok list:")
for n, r in enumerate(acc, 1):
    print("   %2d %-55s ok=%s" % (n, r.get("check_id") or r.get("check") or r.get("id") or "?",
                                  r.get("ok") or r.get("passed") or "?"))
fl = rows(OUT / "frontier" / "frontier_localization.csv")
print("  frontier/frontier_localization.csv rows =", len(fl))
if fl:
    fc = [c for c in fl[0] if "status" in c.lower()]
    print("  status distribution =", dict(Counter(r.get(fc[0], "") for r in fl)) if fc else "no status col")
fi = rows(OUT / "frontier" / "frontier_identity_evidence.csv")
print("  frontier/frontier_identity_evidence.csv rows =", len(fi))
if fi:
    vc = [c for c in fi[0] if c.lower() in ("status","identity_status","verification_status")]
    print("  verification col(s) =", vc, " dist =", {c: dict(Counter(r.get(c, "") for r in fi)) for c in vc})

print("\n== C. defect ②: extension cohort ==")
cs = rows(REPO / "data" / "metadata" / "physics_completion_set.csv")
print("  physics_completion_set.csv rows =", len(cs),
      " cohort dist =", dict(Counter(r.get("cohort","") for r in cs)))
print("  rows with cohort==extension:", sum(1 for r in cs if r.get("cohort") == "extension"))
ep = rows(REPO / "data" / "metadata" / "physics_completion_extension_pool.csv")
print("  extension_pool.csv data rows (DictReader, header excluded) =", len(ep))
print("  registration_status dist =", dict(Counter(r.get("registration_status","") for r in ep)))
print("  raw line count incl header:", len((REPO / "data" / "metadata" / "physics_completion_extension_pool.csv").read_text(encoding="utf-8").splitlines()))

spec = importlib.util.spec_from_file_location(
    "srw", REPO / "scripts" / "wp_production" / "strict_readiness_wiring.py")
srw = importlib.util.module_from_spec(spec); spec.loader.exec_module(srw)
print("  derive_pool_extension_trigger(None,False,True) =",
      srw.derive_pool_extension_trigger(None), "|",
      srw.derive_pool_extension_trigger(False), "|",
      srw.derive_pool_extension_trigger(True))
import inspect
src = inspect.getsource(srw.derive_pool_extension_trigger)
print("  trigger fn reads ext_rows/extension count?",
      ("ext" in src or "extension_rows" in src or "cohort" in src))

print("\n== D. defect ③: li_pair two scopes ==")
labels = rows(OUT / "ensembles" / "production_ensemble_labels.csv")
print("  labels rows =", len(labels))
pairs = srw._complete_li_pairs(labels)
print("  trigger-side _complete_li_pairs =", len(pairs), sorted(pairs))
by_mol = {}
for r in labels:
    by_mol.setdefault(r.get("name",""), {})[r.get("state","")] = r.get("acceptance_status","")
mols = sorted({r.get("name","") for r in labels if r.get("name","")})
missing = {m: [s for s in srw.LI_STATES if by_mol[m].get(s) != "accepted"]
           for m in mols if not all(by_mol[m].get(s) == "accepted" for s in srw.LI_STATES)}
print("  mols NOT both-Li-accepted ->", missing)
acc_legs = Counter(v for v in (r.get("acceptance_status","") for r in labels))
print("  labels acceptance_status dist =", dict(acc_legs))
# ledger side: from plan_compliance meta + scientific accepted legs source
print("  wp6_gate_ready(12, 44) =", srw.wp6_gate_ready(12, 44) if hasattr(srw, "wp6_gate_ready") else "n/a (in build_plan_compliance)")
spec2 = importlib.util.spec_from_file_location(
    "bpc", REPO / "scripts" / "wp_production" / "build_plan_compliance.py")
bpc = importlib.util.module_from_spec(spec2)
try:
    spec2.loader.exec_module(bpc)
    print("  build_plan_compliance wp6_gate_ready(12,44) =", bpc.wp6_gate_ready(12, 44),
          "| (9,44)=", bpc.wp6_gate_ready(9, 44), "| (12,48)=", bpc.wp6_gate_ready(12, 48),
          "| (9,48)=", bpc.wp6_gate_ready(9, 48))
except Exception as e:
    print("  exec bpc module failed:", type(e).__name__, e)
wp6 = srw.derive_wp6_trigger(labels, mols, pairs)
print("  derive_wp6_trigger(current labels) =", wp6)
print("\nDONE exit 0 path reached")
