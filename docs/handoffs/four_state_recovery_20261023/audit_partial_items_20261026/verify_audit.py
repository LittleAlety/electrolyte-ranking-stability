# -*- coding: utf-8 -*-
"""READ-ONLY audit recomputation for the 17 open plan-compliance items.

Never writes to outputs/**, scripts/**, tests, or git. Imports the generator
and calls build_rows() (read-only path; its subprocess is aggregator --check).
"""
import csv, json, hashlib, subprocess, sys
from pathlib import Path
from collections import Counter

REPO = Path(r"E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code")
sys.path.insert(0, str(REPO / "scripts" / "wp_production"))

def R(rel):
    p = REPO / rel
    if not p.is_file():
        return None
    with p.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def sha(rel):
    p = REPO / rel
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.is_file() else "MISSING"

def section(t):
    print("\n" + "=" * 8 + " " + t + " " + "=" * 8)

# ---------------- A. full recompute via the generator itself ----------------
section("A. build_rows() recompute (current disk state)")
import wp2_progress
import build_plan_compliance as bpc
snap = wp2_progress.build_snapshot(REPO)
rows = bpc.build_rows(snap)
print("total items:", len(rows))
print("status counts:", dict(Counter(r["status"] for r in rows)))
OPEN = ("partial", "not_satisfied", "blocked_on_production")
for r in rows:
    if r["status"] in OPEN:
        print("-" * 100)
        print("ITEM %s [%s]" % (r["item_id"], r["status"]))
        print("  measured: %s" % r["measured"])

# ---------------- B. frontier products (item 3 dispute) ----------------
section("B. frontier outputs dir")
fdir = REPO / "outputs" / "physics_completion" / "frontier"
if fdir.is_dir():
    for p in sorted(fdir.iterdir()):
        print("  file:", p.name, p.stat().st_size, "mtime", p.stat().st_mtime)
fl = R("outputs/physics_completion/frontier/frontier_localization.csv")
if fl:
    print("frontier_localization rows:", len(fl))
    print("  status counts:", dict(Counter(r.get("status", "") for r in fl)))
fi = R("outputs/physics_completion/frontier/frontier_identity_evidence.csv")
if fi:
    print("frontier_identity_evidence rows:", len(fi))
    print("  identity_qc_status:", dict(Counter(r.get("identity_qc_status", "") for r in fi)))
    print("  missing_artifacts nonempty:", sum(1 for r in fi if (r.get("missing_artifacts") or "").strip()))
    print("  failed_checks nonempty:", sum(1 for r in fi if (r.get("failed_checks") or "").strip()))
thr = REPO / "outputs/physics_completion/state_identity/thresholds.json"
print("thresholds.json text has frontier_localization:", "frontier_localization" in thr.read_text(encoding="utf-8"),
      "| has not_computed:", "not_computed" in thr.read_text(encoding="utf-8"))

# ---------------- C. ensemble labels exact DictReader counts ----------------
section("C. production_ensemble_labels.csv")
el = R("outputs/physics_completion/ensembles/production_ensemble_labels.csv")
print("rows:", len(el), "| acceptance_status:", dict(Counter(r.get("acceptance_status", "") for r in el)))

# ---------------- D. sampling: designated vs executed, escalation ----------------
section("D. sampling")
esc = R("outputs/physics_completion/sampling/sampling_escalation.csv")
print("escalation rows:", len(esc), "| escalation_status:", dict(Counter(r.get("escalation_status", "") for r in esc)))
sa = R("outputs/physics_completion/sampling/sampling_acceptance.csv")
print("acceptance rows:", len(sa), "| ok:", dict(Counter(r.get("ok", "") for r in sa)))
s1 = R("outputs/physics_completion/sampling/sampling_round1.csv")
ex = sorted({r.get("mol_id", "") for r in s1 if r.get("mol_id")}) if s1 else []
print("executed mols:", ex)
designated = sorted({r.get("mol_id", "") for r in R("data/metadata/physics_completion_set.csv")
                     if r.get("cohort") == "sampling_audit"})
print("designated:", designated)
print("executed==designated:", ex == designated)

# ---------------- E. cost ledger ----------------
section("E. cost_ledger.csv")
cl = R("outputs/physics_completion/cost/cost_ledger.csv")
print("rows:", len(cl), "| status:", dict(Counter(r.get("status", "") for r in cl)))

# ---------------- F. round diagnostics ----------------
section("F. round_diagnostics.csv")
rd = R("outputs/physics_completion/active_learning/round_diagnostics.csv")
print("rows:", len(rd))
print("remaining_unqueried_error_status:", dict(Counter(r.get("remaining_unqueried_error_status", "") for r in rd)))
print("cumulative_core_hours_status:", dict(Counter(r.get("cumulative_core_hours_status", "") for r in rd)))
print("all rows have O_3:", all("O_3" in r for r in rd))
print("regret_threshold_ev set:", {r.get("regret_threshold_ev") for r in rd})

# ---------------- G. AB formal replay ----------------
section("G. blind_replay AB")
ab = R("outputs/physics_completion/active_learning/blind_replay/AB_axis_endpoint.csv")
print("AB rows:", len(ab), "| stop_budget_status:", dict(Counter(r.get("stop_budget_status", "") for r in ab)))
idx = json.loads((REPO / "outputs/physics_completion/active_learning/blind_replay/AB_index.json").read_text(encoding="utf-8"))
print("AB_index declared rows:", (idx.get("rows") or {}))
sb = R("outputs/physics_completion/active_learning/success_budget.csv")
print("success_budget rows:", len(sb), "| new_endpoint_status:", dict(Counter(r.get("new_endpoint_status", "") for r in sb)),
      "| required_consecutive==2:", all(r.get("required_consecutive_budget_points") == "2" for r in sb))

# ---------------- H. targeted recheck job_plan statuses ----------------
section("H. targeted_recheck")
jp = R("outputs/physics_completion/pair_evidence/targeted_recheck/job_plan.csv")
print("job_plan rows:", len(jp), "| status:", dict(Counter(r.get("status", "") for r in jp)))
rr = R("outputs/physics_completion/pair_evidence/targeted_recheck/recheck_results.csv")
print("recheck_results rows:", len(rr))

# ---------------- I. mechanism text counts ----------------
section("I. mechanism_cases.md")
mt = (REPO / "outputs/physics_completion/pair_evidence/mechanism_cases.md").read_text(encoding="utf-8")
print("cases rows:", len(R("outputs/physics_completion/pair_evidence/mechanism_cases.csv")),
      "| '待补' count:", mt.count("待补"), "| '部分' count:", mt.count("部分"))

# ---------------- J. pool extension cohorts ----------------
section("J. pool extension")
cs = R("data/metadata/physics_completion_set.csv")
print("set cohorts:", dict(Counter(r.get("cohort", "") for r in cs)))
ep = REPO / "data/metadata/physics_completion_extension_pool.csv"
print("extension_pool exists:", ep.is_file())
if ep.is_file():
    epr = list(csv.DictReader(ep.open(encoding="utf-8-sig", newline="")))
    print("extension_pool rows:", len(epr), "| status:", dict(Counter(r.get("status", r.get("state", "")) for r in epr)))
    print("first row keys:", list(epr[0].keys()) if epr else None)

# ---------------- K. WP6 ----------------
section("K. explicit_ligand")
lg = R("outputs/physics_completion/explicit_ligand/explicit_ligand_plan.csv")
print("plan rows:", len(lg), "| submitted/executed fields:",
      [{k: r.get(k) for k in ("status", "submitted") if k in r} for r in lg][:5])
ldir = REPO / "outputs/physics_completion/explicit_ligand"
others = [p.name for p in ldir.iterdir() if p.is_file() and p.name != "explicit_ligand_plan.csv"] if ldir.is_dir() else []
print("executed files (excluding plan):", others)
import strict_readiness_wiring as srw
print("strict_checks():", srw.derive_checks())
print("check names:", srw.REQUIRED_CHECKS)
try:
    det = srw.derive_check_details()
    for k, v in det.items():
        print("  detail", k, "passed=", v.get("passed"), "problems=", v.get("problems", [])[:3])
except Exception as e:
    print("derive_check_details ERR:", e)

# ---------------- L. stop rules / motif ----------------
section("L. stop rules & motif")
cfg = (REPO / "config/physics_completion_v1.yaml").read_text(encoding="utf-8")
print("'stop_rules' in config:", "stop_rules" in cfg)
mp = R("outputs/physics_completion/li_motif_sampling/motif_plan.csv")
print("motif_plan rows:", len(mp), "| motif_screen_status:", dict(Counter(r.get("motif_screen_status", "") for r in mp)))

# ---------------- M. pilot cost ledger ----------------
section("M. pilot_cost_ledger")
pc = R("outputs/physics_completion/cost/pilot_cost_ledger.csv")
print("rows:", len(pc),
      "| memory MISSING:", sum(1 for r in pc if r.get("memory") == "MISSING"),
      "| retry UNVERIFIABLE:", sum(1 for r in pc if r.get("retry") == "UNVERIFIABLE"),
      "| raw verified:", sum(1 for r in pc if r.get("raw_output_status") == "verified_on_disk"))

# ---------------- N. state identity counts ----------------
section("N. state_identity")
si = R("outputs/physics_completion/state_identity/state_identity_acceptance.csv")
print("acceptance rows:", len(si), "| ok:", dict(Counter(r.get("ok", "") for r in si)))
ic = R("outputs/physics_completion/state_identity/identity_class_counts.csv")
print("class counts:", [(r.get("identity_class"), r.get("n_states")) for r in ic])

# ---------------- O. git & hashes ----------------
section("O. provenance binding")
r_ = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True)
print("git HEAD:", r_.stdout.strip(), "exit", r_.returncode)
r2 = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain"], capture_output=True, text=True)
print("git dirty entries:", len(r2.stdout.strip().splitlines()))
for f in ("outputs/physics_completion/compliance/plan_compliance.md",
          "outputs/physics_completion/compliance/plan_compliance.csv",
          "data/metadata/physics_completion_set.csv",
          "outputs/physics_completion/ensembles/production_ensemble_labels.csv",
          "outputs/physics_completion/frontier/frontier_localization.csv",
          "outputs/physics_completion/state_identity/thresholds.json",
          "outputs/physics_completion/cost/cost_ledger.csv",
          "outputs/physics_completion/pair_evidence/targeted_recheck/job_plan.csv"):
    print("sha16", f, sha(f))
print("meta:", (REPO / "outputs/physics_completion/compliance/plan_compliance_meta.json").read_text(encoding="utf-8")[:400])
print("\nDONE")
