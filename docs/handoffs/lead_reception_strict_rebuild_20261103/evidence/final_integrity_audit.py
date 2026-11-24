"""FINAL · 关键哈希交叉核对：证据文档钉住的 sha 逐条对活文件（只读）。

配对来源：P1 §7 哈希表、P3/P4/P5b/P6/P7/P9 各批次终值。
output: evidence/final_integrity_audit.json
"""
import hashlib
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]  # evidence → lead_reception... → handoffs → docs → 仓库根（本文件在 evidence/ 下）

PAIRS = [  # (path, expected_sha 或 sha前缀, 引用文档)
    ("work/dmc_staged_receiver_v5.py",
     "205f1ba93d9a0b69f2ea5f86595eef527da03db6d6aa8b2a331dd25a2ca9bb66", "P1:15,87"),
    ("work/lead_reception_20261102/rev5_baselines/dmc_staged_receiver_v5__rev5.4.py",
     "94186049e5ed6bb3edce3754aa26d5a7c9bb9ba33d986f5879666cba5db69838", "P1:14,88"),
    ("work/admission_closure_20261102/rev5_candidate_d8/dmc_staged_receiver_v5_candidate.py",
     "138df33b6c2a677ac2697825ae3680650c0ea1b3235d219a66e7d4dd13dd153c", "P1:16,89"),
    ("work/dmc_staged_staging_ledger.json",
     "c336acb5051deb31c276dc54c8bfefbcc64bf93d0244c82cb722a8869fd382d2", "P1:37,90"),
    ("work/admission_closure_20261102/D7_FIX_VERIFICATION.json",
     "e0c47ef990ae33c4953cc00098c66af5413069475c7dd9a92e51fa06ed1eb022", "P1:30,91"),
    ("work/admission_closure_20261102/rev5_candidate_d8/MANIFEST_v2_20261103T080255.json",
     "9de6c2e0f09622c82d219c4595ed7ddcbfe0f68ae50d8f0f477a8dd823037b42", "P1:16,92"),
    ("work/test_dmc_staged_receiver_v5.py",
     "ee6b9f2987542aa998e63e9a52f2b6a0bbb79abc4109b254cdc8237181e2a7f2", "P1:31,93"),
    ("work/dmc_staged_receiver.py",
     "32501b7185d61d7ac05ba1cd4f03ae1f4b85d1f5c8225992a8272a1ce7374278", "P1:12,94"),
    ("scripts/wp_production/build_coverage_reviews.py",
     "a7eee5aa", "P3 after"),                       # 前缀（P3 记录前8位）
    ("scripts/wp_production/rebuild_strict_isolated.py",
     "83581f169d26a8d3df1f7a7438a5b06d296ff812fff9458b2a6f20052570fc22", "P6 §1"),
    ("docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/p6_isolated_entry/"
     "baseline/rebuild_strict_isolated.py.orig",
     "468dc00ee21a50f5e8cc605c5e855ec67b4a78823352ce09a6f0cc42a78c0bcd", "P6 §1 baseline"),
    ("docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/p4_five_state_binding/"
     "binding_package.json",
     "4a35436e", "P4"),                              # 前缀
    ("docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/p6_isolated_entry/p6_entry.py",
     "c78de6cdba2bc9aa6c540a7e9d4ac12534f6b410d4529d1ccae39d2779a6a9df", "P6 §2"),
    ("docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/p6_isolated_entry/"
     "shuffle_child.py",
     "0195ef1b946bb3ad2b5f7609e44ff704f0e348e493b8b5818ed5c1d56e53fbe3", "P6 §2"),
    ("docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/p6_isolated_entry/"
     "p6_verification.json",
     "ea4dfbb2fc1ec23907280e18658fe6a00e3eaffb6267e0a023fe958e7c530801", "P6 §3"),
    ("docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/p5_gate_inventory/"
     "admission_state_view.json",
     "0ced646d35c464a095bde48422c8666307f0bea799d7ca43a542d99d24b738e5", "P5b"),
    ("docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/p5_gate_inventory/"
     "admission_state_view.py",
     "20bda96862c9eec20c3a0c2205a9fffc570f02e1fc12e18f9e3fedb7fdc2c18b", "P5b"),
    ("outputs/physics_completion/ensembles/production_ensemble_labels.csv",
     "c21003f5e18a2faaf4e3c8e91c379ea3ab16659706d13786ed25df0038ae0c80", "P9 §4"),
]
EXCLUDED = [  # 明确不可核对项与原因
    {"object": "config/comparability_criterion_v1.json", "why": "按红线不生成，absence 即期望（P5b 实测 absent）"},
]


def main() -> int:
    results = []
    for rel, expected, src in PAIRS:
        p = REPO / rel
        if not p.is_file():
            results.append({"path": rel, "expected": expected, "actual": "MISSING",
                            "match": False, "cited_in": src})
            continue
        actual = hashlib.sha256(p.read_bytes()).hexdigest()
        results.append({"path": rel, "expected": expected, "actual": actual,
                        "match": actual.startswith(expected), "cited_in": src})
    mism = [r for r in results if not r["match"]]
    payload = {
        "schema": "final_integrity_audit/v1",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pairs_checked": len(results), "mismatches": len(mism),
        "results": results, "excluded_unverifiable": EXCLUDED,
    }
    out = HERE / "final_integrity_audit.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"checked": len(results), "mismatches": len(mism)}))
    for r in mism:
        print("MISMATCH", r["path"], r["expected"][:12], "vs", r["actual"][:12])
    print(out)
    return 1 if mism else 0


if __name__ == "__main__":
    sys.exit(main())
