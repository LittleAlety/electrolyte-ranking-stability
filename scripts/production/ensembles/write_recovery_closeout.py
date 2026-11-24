"""Write the concrete closeout and one bounded, unsubmitted evidence proposal."""

from pathlib import Path as _ReorgPath
import sys as _reorg_sys

_reorg_sys.path.insert(0, str(_ReorgPath(__file__).resolve().parents[1]))
import _paths  # noqa: F401,E402  (仓库根 + scripts/production/* 注册到 sys.path)

import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np

from audit_strict_recovery import xyz_geometry

ROOT = _paths.REPO_ROOT
BASE = ROOT / "docs/handoffs/strict_rebuild_20261103"
OUT = BASE / "remote_closure_20261103"
closure = json.loads((OUT / "remote_evidence_closure.json").read_text(encoding="utf-8"))
index = json.loads((BASE / "run_06c49d9e7ebe0688/source_index.json").read_text(encoding="utf-8"))
primary = next(r for r in index["member_sources"] if r["member_key"] == "AN|LiM_2plus|primary" and r["is_current_attempt"])
new_xyz = OUT / "raw/AN_LiM2plus_job.xyz"
old_xyz = ROOT / primary["source_paths"]["registered_final_geometry"]
new_symbols, new_coordinates = xyz_geometry(new_xyz)
old_symbols, old_coordinates = xyz_geometry(old_xyz)
assert new_symbols == old_symbols
x, y = np.array(new_coordinates), np.array(old_coordinates)
xc, yc = x-x.mean(axis=0), y-y.mean(axis=0)
u, _, vt = np.linalg.svd(xc.T @ yc)
if np.linalg.det(u @ vt) < 0:
    u[:, -1] *= -1
rmsd = float(np.sqrt(np.mean(np.sum((xc @ (u @ vt)-yc)**2, axis=1))))
geometry = {"strict_opt_geometry": new_xyz.relative_to(ROOT).as_posix(),
            "strict_opt_geometry_sha256": hashlib.sha256(new_xyz.read_bytes()).hexdigest(),
            "existing_primary_geometry": old_xyz.relative_to(ROOT).as_posix(),
            "existing_primary_geometry_sha256": hashlib.sha256(old_xyz.read_bytes()).hexdigest(),
            "proper_rotation_all_atom_rmsd_a": rmsd,
            "max_raw_coordinate_difference_a": float(np.max(np.abs(x-y))),
            "existing_same_geometry_AnFreq_bound": False,
            "binding_checks": "AN_new_opt_existing_frequency_binding.json"}
(OUT / "AN_geometry_comparison.json").write_text(json.dumps(geometry, indent=2)+"\n")
strict = next(r for r in closure["new_raw_logs"] if r["strict_numerical_candidate"])
strict_text = (ROOT / strict["local_file"]).read_text(encoding="utf-8", errors="replace")
imaginary = re.findall(r"\d+:\s*(-\d+\.\d+)\s+cm\*\*-1\s+\*\*\*imaginary mode", strict_text)
assert imaginary and rmsd > 5.1e-7
proposal = {"proposal_id": "AN_LiM2plus_FIXED_GEOMETRY_ANFREQ_20261103",
            "status": "PROPOSED_NOT_AUTHORIZED_NOT_SUBMITTED", "state": "AN|LiM_2plus",
            "basis": {"new_opt_log": strict["local_file"], "new_opt_log_sha256": strict["sha256"],
                      "five_opt_items": "PASS", "old_frequency_method": "NumFreq",
                      "old_imaginary_frequencies_cm1": [float(x) for x in imaginary],
                      "existing_AnFreq_same_geometry": False, "geometry_binding": geometry},
            "minimal_experiment": "one fixed-geometry AnFreq; no new Opt in this proposal",
            "physical_contract": "wB97X-D4 def2-TZVPD SMD(acetonitrile) TightSCF SlowConv; charge=2 multiplicity=2; exact returned strict-Opt geometry",
            "expected_gate": "target analytic Hessian, imaginary-mode verdict and thermal correction for this strict-Opt candidate; does not alone close identity, registration, dedup or coverage",
            "necessity_scope": "target-frequency evidence is missing for this candidate path; this does not prove every recovery path for the state needs this experiment",
            "stopping_conditions": ["retain unresolved on frozen imaginary-mode failure, SCF failure, species drift or protocol mismatch",
                                    "no automatic displacement, rescue Opt, stricter SCF or second job",
                                    "if frequency passes, return to isolated identity/registration/dedup/coverage review; no formal promotion"],
            "budget": {"unit": "core-hour", "historical_comparator_job": "3706757",
                       "historical_observed_CPUTimeRAW_seconds": 3932,
                       "historical_Opt_NumFreq_core_hours": 3932/3600,
                       "indicative_planning_consumption_core_hours": [0.5, 4.0],
                       "estimate_limit": "heuristic planning range from same-system old Opt+NumFreq; not a measured AnFreq prediction or confidence interval",
                       "existing_profile": "orca_anfreq_only_4c_24h_v1",
                       "allocated_cores": 4, "allocated_wall_hours": 24,
                       "reservation_ceiling_core_hours": 96,
                       "reservation_is_not_expected_consumption": True,
                       "internal_deadline": None, "currency_estimate": None,
                       "authorization_required": "approve this experiment and its reservation separately; no prior profile authorization reused"}}
(OUT / "FIRST_EVIDENCE_PROPOSAL.json").write_text(json.dumps(proposal, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
out_scan = (OUT / "out_hash_and_geometry_scan.txt").read_text(encoding="utf-8-sig")
out_hashes = re.findall(r"^([0-9a-f]{64})\s+(/home/.*)$", out_scan, re.M)
assert out_scan.split("GEOMETRY_TABLE_OUT_FILES", 1)[1].strip() == "OUT_SCAN_COMPLETE"
ledger = [line for line in (OUT / "remote_job_ledger.txt").read_text(encoding="utf-8-sig").splitlines() if re.match(r"^[0-9_]+\|", line)]
integrity = {}
for path, previous in json.loads((BASE / "blocker_resolution_20261103/formal_integrity.json").read_text()).items():
    digest = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
    integrity[path] = {"sha256": digest, "unchanged": digest == previous["sha256"]}
assert all(r["unchanged"] for r in integrity.values())
(OUT / "formal_integrity.json").write_text(json.dumps(integrity, indent=2)+"\n")
summary = {"remote_log_files_checked": closure["remote_log_count"], "same_bytes_as_frozen_local": closure["matched_frozen_local_hashes"],
           "new_logs_returned": len(closure["new_raw_logs"]), "new_opt_five_item_pass": 1,
           "new_fully_qualified_member": 0, "scoped_auxiliary_out_files": len(out_hashes),
           "scheduler_records_returned": len(ledger), "EC_actual_stage_inputs_matched": 4,
           "remote_tar_archives_listed": sum(x.startswith("/home/") for x in (OUT / "remote_archive_members.txt").read_text().splitlines()),
           "scope_ended": "fixed project root/depth9 and root archive inventories; no claim of global filesystem exhaustion",
           "remaining_work": ["AN M+ frontier chain absent in specified local/remote/archive sources; single-basin search-scope adjudication remains",
                              "bind qualified ordinary starts to actual search scope for DEC LiM2+, DEC M+, GBL LiM+, PC M+, TMP M; no active-job pending found",
                              "TMP LiM2+ retain c08 failure plus r2_c48_c00/r3m_c00 strict evidence gaps; TMP M+ retain c10/c33 failures plus r3_c42 strict gap",
                              "per-state minimal experiment designs/budgets for other 36 states have not been prepared",
                              "full JobIDRaw-to-array-alias reconciliation not completed; no accounting ledger changed",
                              "proposal approval, any new calculation and any formal promotion remain separate user decisions"],
           "no_new_physical_computation": True, "historical_status": "45 accepted / 2 limited / 1 provisional unchanged"}
(OUT / "closeout.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print(json.dumps({"remote_logs": summary["remote_log_files_checked"], "aux_out": len(out_hashes), "ledger_rows": len(ledger),
                  "AN_geometry_rmsd_a": rmsd, "proposal_reservation_CH": 96, "protected_files_unchanged": len(integrity)}))
