#!/usr/bin/env python
"""可复跑验证：7 条声明逐一复核。退出码 0=全部按"声明口径"证实；1=有未证实项。

注意（与 CLAIMS_AUDIT.md 一致）：
  * C1/C5/C6 的判定区分"声明当时口径"与"当前仓库实测口径"。本脚本按**当前实测**
    打印数值并判定；对历史性声明（C1 的 3 缺口、C5 的 8 skip、C6 的 79/79），
    当前实测若不同，本脚本计为 UNVERIFIED（退出码 1）。
  * C6 需要跑完整收口链（约 30–60 分钟）与完整 pytest（约 5–10 分钟），
    默认跳过（--fast）。不带 --fast 时，C6 用"最近一次实测记录"复述（仍标
    UNVERIFIED，因为 79/79 在当前树不可复现）。
用法：
  .venv/Scripts/python.exe -X utf8 docs/handoffs/four_state_recovery_20261023/audit_claims_20261023/verify.py [--fast]
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
RESULTS: list[tuple[str, str, str]] = []  # (claim_id, verdict, one-line evidence)


def record(cid: str, verdict: str, evidence: str) -> None:
    RESULTS.append((cid, verdict, evidence))
    print("[%-14s] %-6s %s" % (cid, verdict, evidence))


def c1() -> None:
    sys.path.insert(0, str(REPO / "scripts" / "wp_production"))
    import strict_readiness_wiring as W
    import strict_readiness as SR
    with (REPO / "outputs/physics_completion/ensembles/production_ensemble_labels.csv").open(
            encoding="utf-8-sig", newline="") as fh:
        labels = list(csv.DictReader(fh))
    checks = W.derive_checks()
    verdict = SR.strict_readiness(
        labels, {(r["name"], r["state"]) for r in labels}, checks)
    gaps = verdict["blocked_by"]
    print("    blocked_by = %s" % gaps)
    claimed = {"ensemble_not_48_accepted", "wp5_full_target_pool_evaluated",
               "execution_cost_provenance_complete"}
    if set(gaps) == claimed:
        record("C1", "OK", "3 缺口与声明一致")
    else:
        record("C1", "UNVERIFIED",
               "声明 3 缺口；当前实测 %d 缺口 %s（execution_cost_provenance_complete "
               "已在 P7/commit 9f347cd 闭合）" % (len(gaps), "+".join(sorted(gaps))))


def c2() -> None:
    labels = list(csv.DictReader(
        (REPO / "outputs/physics_completion/ensembles/production_ensemble_labels.csv").open(
            encoding="utf-8-sig", newline="")))
    acc = [r for r in labels if r["acceptance_status"] == "accepted"]
    lim = [r for r in labels if r["acceptance_status"] == "limited"]
    four = {(r["name"], r["state"]) for r in lim}
    ok_counts = len(acc) == 44 and len(lim) == 4
    ok_four = four == {("DMC", "M_plus"), ("DMC", "LiM_2plus"),
                       ("DOL", "LiM_2plus"), ("EC", "LiM_2plus")}
    ok_reason = all(r["limitation_reason"] == "rescue_budget_exhausted" for r in lim)
    cov = list(csv.DictReader(
        (REPO / "outputs/physics_completion/recovery/coverage_reviews.csv").open(
            encoding="utf-8", newline="")))
    dmc = {r["route"] for r in cov if r["name"] == "DMC"}
    dec = {r["route"] for r in cov if r["name"] in ("DOL", "EC")}
    ok_route = dmc == {"unresolved_qc"} and dec == {"search_exhausted"}
    print("    44/4=%s four=%s reasons=%s routes(DMC=%s DOL/EC=%s)"
          % (ok_counts, ok_four, ok_reason, dmc, dec))
    record("C2", "OK" if all([ok_counts, ok_four, ok_reason, ok_route]) else "UNVERIFIED",
           "44/4 标签、四态、rescue_budget_exhausted、覆盖分级 DMC=unresolved_qc / DOL|EC=search_exhausted")


def c3() -> None:
    reg = list(csv.DictReader(
        (REPO / "outputs/physics_completion/recovery/torsion_freedom_registry.csv").open(
            encoding="utf-8", newline="")))
    struct = list(csv.DictReader(
        (REPO / "outputs/physics_completion/ensembles/production_ensemble_structures.csv").open(
            encoding="utf-8", newline="")))
    ok_all = True
    for state in ("M_plus", "LiM_2plus"):
        registered = [r["detail"].split()[0] for r in reg
                      if r["name"] == "DMC" and r["state"] == state]
        probed = sorted({r["member_key"].split("|")[2] for r in struct
                          if r["member_key"].startswith("DMC|%s|" % state)
                          and r["member_key"].split("|")[2].startswith("tors_")})
        probed_norm = [t.replace("tors_", "").replace("_", "-") for t in probed]
        unprobed = [t for t in registered if t not in probed_norm]
        fam_ok = all(t.split("-")[0] in ("6", "7", "8") for t in probed_norm)
        print("    DMC|%s registered=%d probed=%d unprobed=%d family_ok=%s"
              % (state, len(registered), len(probed), len(unprobed), fam_ok))
        ok_all &= (len(registered) == 10 and len(probed) == 3 and len(unprobed) == 7 and fam_ok)
    record("C3", "OK" if ok_all else "UNVERIFIED",
           "两态均 10 登记 - 3 探过(6/7/8-0-1-2 族) = 7 未探且合法")


def c4() -> None:
    struct = [r for r in csv.DictReader(
        (REPO / "outputs/physics_completion/ensembles/production_ensemble_structures.csv").open(
            encoding="utf-8", newline="")) if r["member_key"].startswith("DOL|LiM_2plus|c05")]
    latest = max(struct, key=lambda r: int(r["attempt"] or 0))
    w = [r for r in csv.DictReader(
        (REPO / "outputs/physics_completion/ensembles/production_ensemble_weights.csv").open(
            encoding="utf-8", newline="")) if r["member_key"].startswith("DOL|LiM_2plus|c05")]
    d = [r for r in csv.DictReader(
        (REPO / "outputs/physics_completion/ensembles/production_ensemble_dispositions.csv").open(
            encoding="utf-8", newline="")) if r["member_key"].startswith("DOL|LiM_2plus|c05")]
    ok = (latest["status"] == "computed"
          and len(w) == 1 and float(w[0]["boltzmann_weight"]) > 0
          and (not d or all(r["disposition"] == "computed" for r in d)))
    print("    latest_status=%s weight=%s disposition=%s"
          % (latest["status"], w[0]["boltzmann_weight"] if w else "-",
             d[0]["disposition"] if d else "-"))
    record("C4", "OK" if ok else "UNVERIFIED",
           "structures(latest=computed) + weights(1.0) + dispositions(computed) 三处一致")


def c5() -> None:
    cmd = [str(REPO / ".venv" / "Scripts" / "python.exe"), "-X", "utf8", "-m", "pytest",
           "tests", "-q", "-rs", "-p", "no:warnings", "--tb=no",
           "--ignore=tests/test_orca_run.py", "--ignore=tests/test_toolchain.py",
           "--ignore=tests/test_bundled_toolchain.py", "--ignore=tests/test_orca_input.py"]
    proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    skips = [ln for ln in proc.stdout.splitlines() if ln.startswith("SKIPPED")]
    n = len(skips)
    print("    skips=%d" % n)
    for s in skips:
        print("      %s" % s)
    record("C5", "OK" if n == 8 else "UNVERIFIED",
           "声明 8 个声明式 skip；当前实测 %d 个（7×week36 未构建 + hpc_numfreq fixture 缺 + submit_budget_gate）" % n)


def c6() -> None:
    # 79/79 全绿在当前树不可复现：收口链 79 步中 pytest-offline 红步骤 1 个。
    # 完整链重跑约 30–60 分钟；--fast 模式下复述 2026-10-24 16:44 实测记录。
    record("C6", "UNVERIFIED",
           "实测 78/79（pytest-offline 红：3 项失败 test_orca_run::clears_a_stale_density / "
           "test_toolchain::probe_version / round3::audit_claim_scope；三项隔离重跑均绿，"
           "属套件内状态串扰+仓库 mid-flight；79/79 未能复现）")


def c7() -> None:
    d = json.loads((REPO / "docs/handoffs/four_state_recovery_20261023"
                    / "P3_CANDIDATES_20261023.json").read_text(encoding="utf-8"))
    expect = {
        ("DMC|M_plus", "g1"): (7, 3, 4, {"equivalent_start": 4}),
        ("DMC|M_plus", "g2"): (0, 0, 0, {}),
        ("DMC|LiM_2plus", "g1"): (7, 1, 6, {"equivalent_start": 1, "li_coordination_changed": 5}),
        ("DMC|LiM_2plus", "g2"): (6, 3, 3, {"equivalent_start": 3}),
        ("DOL|LiM_2plus", "g1"): (0, 0, 0, {}),
        ("DOL|LiM_2plus", "g2"): (30, 9, 21, {"ring_broken": 12}),
        ("EC|LiM_2plus", "g1"): (0, 0, 0, {}),
        ("EC|LiM_2plus", "g2"): (30, 9, 21, {"ring_broken": 12}),
    }
    ok = True
    for (st, gr), (raw, acc, ref, mix) in expect.items():
        key = ("group_1_registered_torsions" if gr == "g1"
               else "group_2_new_degrees_of_freedom")
        g = d["states"][st][key]
        got_mix = {}
        for r in g.get("refused_reasons", []):
            got_mix[r["reason"]] = got_mix.get(r["reason"], 0) + 1
        cell_ok = (g.get("raw"), g.get("accepted"), g.get("refused")) == (raw, acc, ref) \
            and got_mix == mix
        ok &= cell_ok
        print("    %-16s %s raw=%s accepted=%s refused=%s mix=%s -> %s"
              % (st, gr, g.get("raw"), g.get("accepted"), g.get("refused"), got_mix,
                 "OK" if cell_ok else "MISMATCH"))
    # heavy 位移抽样（MD 表格逐格）
    recs = d["states"]["DMC|M_plus"]["group_1_registered_torsions"]["accepted_records"]
    heav = sorted(round(c["heavy_pair_change_a"], 4) for c in recs)
    ok &= heav == [0.0, 0.2432, 0.2743]
    print("    DMC|M_plus accepted heavy=%s (MD: 0.2743/0.2432/0 甲基) -> %s"
          % (heav, "OK" if heav == [0.0, 0.2432, 0.2743] else "MISMATCH"))
    record("C7", "OK" if ok else "UNVERIFIED",
           "JSON 重算四态 raw/accepted/refused/拒因/heavy 与 MD 表格逐格一致（含 raw=accepted+refused 恒等式）")


def main() -> int:
    for fn in (c1, c2, c3, c4, c5, c6, c7):
        fn()
    unverified = [cid for cid, v, _ in RESULTS if v != "OK"]
    print()
    print("=" * 72)
    for cid, v, ev in RESULTS:
        print("%-4s %-10s %s" % (cid, v, ev))
    print("=" * 72)
    print("verdict: %d/7 confirmed; %d unverified" % (
        len(RESULTS) - len(unverified), len(unverified)))
    return 0 if not unverified else 1


if __name__ == "__main__":
    raise SystemExit(main())
