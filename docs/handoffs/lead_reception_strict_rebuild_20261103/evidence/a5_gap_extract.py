#!/usr/bin/env python3
"""a5_gap_extract.py — A5 36态缺口机制分组提取（只读，标准库）。
用法: python a5_gap_extract.py   (cwd = 仓库根 电解液溶剂HB-Code)
退出码 0 = 断言全过。
"""
import csv, hashlib, io, json, sys
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

H = "docs/handoffs/strict_rebuild_20261103"
GAP = f"{H}/run_06c49d9e7ebe0688/gap_actions.json"
DEC = f"{H}/recovery_decisions_20261103_v9/decisions.csv"
RECHECK = f"{H}/verification_20261103/coverage_recheck.json"
LAB = "outputs/physics_completion/ensembles/production_ensemble_labels.csv"
REV = "outputs/physics_completion/recovery/coverage_reviews.csv"

EXPECT = {  # 本轮起点实测冻结值
    GAP: "e7ce5ba931dc42157ce2dd12cd7fbd27d6776ade59d274fa1f537620172a9113",
    DEC: "ac430d378c05444c9f2afc08b0ac477b6221ff4d64a78dedd7d3f8136cc1ae5d",
    LAB: "c21003f5e18a2faaf4e3c8e91c379ea3ab16659706d13786ed25df0038ae0c80",
    REV: "e89188f6eac28bbf2dd309a95ec19ea9b1cc78969a262883820f939eec28ba40",
}

def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()

print("=== 源文件哈希 ===")
for p in (GAP, DEC, RECHECK, LAB, REV):
    h = sha(p)
    mark = "OK(=冻结)" if EXPECT.get(p) == h else ("(本轮实测)" if p not in EXPECT else "**漂移**")
    print(f"  {h}  {p}  {mark}")
    assert EXPECT.get(p, h) == h, f"共享面漂移: {p}"

gap = json.load(open(GAP, encoding="utf-8"))
dec = {r["state_key"]: r for r in csv.DictReader(open(DEC, encoding="utf-8-sig"))}
lab = {(r["name"] + "|" + r["state"]): r for r in csv.DictReader(open(LAB, encoding="utf-8-sig"))}
rc = json.load(open(RECHECK, encoding="utf-8"))

NAMED = {"DEC|LiM_2plus", "DEC|M_plus", "GBL|LiM_plus", "PC|M_plus", "TMP|M",
         "AN|M_plus", "AN|LiM_2plus", "TMP|M_plus", "TMP|LiM_2plus"}
NONACC = {"DMC|M_plus", "DMC|LiM_2plus", "EC|LiM_2plus"}
assert len(gap) == 48 and len(dec) == 48 and len(lab) == 48
s36 = [e["state_key"] for e in gap
       if e["state_key"] not in NAMED and e["state_key"] not in NONACC]
assert len(s36) == 36, len(s36)
acc = Counter(r["acceptance_status"] for r in lab.values())
print(f"\nlabels 口径: {dict(acc)} (45 accepted − 9 具名 = 36)")

groups = {"G1_species": [], "G2_missing_row": [], "G3_zero_reg": [],
          "G4_cov_closed": [], "G5_three_gates": []}
print(f"\n{'state':24s} {'group':14s} {'cov':17s} {'reg':>3s} {'exceed':>6s} {'missing':>7s} {'species':>7s} {'notcur':>6s} action")
for e in gap:
    k = e["state_key"]
    if k not in set(s36):
        continue
    f = Counter(r.split(":")[0] for m in e.get("current_member_blockers", [])
                for r in m.get("reasons", []))
    L, D = lab[k], dec[k]
    species = f["SPECIES_IDENTITY_UNVERIFIED"] > 0
    miss_no_exceed = f["FIVE_ITEM_MISSING"] and not f["FIVE_ITEM_EXCEEDS_STRICT_LIMIT"]
    zero_reg = L["n_registered"] == "0"
    cov_res = L["coverage_status"] == "resolved_by_review"
    if species:                      g = "G1_species"
    elif miss_no_exceed:             g = "G2_missing_row"
    elif zero_reg:                   g = "G3_zero_reg"
    elif cov_res:                    g = "G4_cov_closed"
    else:                            g = "G5_three_gates"
    groups[g].append(k)
    notcur = f["NOT_CURRENT_NUMERIC_MEMBER"] + f["NOT_IN_FORMAL_CANDIDATE_REGISTER"]
    act = ("补Energy检索" if "补 Energy change" in D["zero_compute_next_action_or_bounded_experiment"]
           else "有界实验提案路径(条件性)")
    print(f"{k:24s} {g:14s} {L['coverage_status']:17s} {L['n_registered']:>3s} "
          f"{f['FIVE_ITEM_EXCEEDS_STRICT_LIMIT']:>6d} {f['FIVE_ITEM_MISSING']:>7d} "
          f"{f['SPECIES_IDENTITY_UNVERIFIED']:>7d} {notcur:>6d} {act}")

print("\n=== 分组计数（分区校验 4+2+2+4+24=36） ===")
tot = 0
for g, ks in groups.items():
    print(f"  {g:14s} {len(ks):2d}  {', '.join(sorted(ks)) if g != 'G5_three_gates' else '(24态, 见上表)'}")
    tot += len(ks)
assert tot == 36

# 机制频次（36态内）
n_ident = n_exceed = n_tol = n_spec = 0
for e in gap:
    if e["state_key"] not in set(s36):
        continue
    f = Counter(r.split(":")[0] for m in e.get("current_member_blockers", [])
                for r in m.get("reasons", []))
    n_ident += f["PRIMARY_IDENTITY_SEPARATE_SOURCE_NOT_REVERIFIED"] > 0
    n_exceed += f["FIVE_ITEM_EXCEEDS_STRICT_LIMIT"] > 0
    n_tol += f["PRINTED_OPT_TOLERANCE_DIFFERS"] > 0
    n_spec += f["SPECIES_IDENTITY_UNVERIFIED"] > 0
print(f"\n36态机制频次: 身份源未复核={n_ident}  五项超限={n_exceed}  打印容差不一致={n_tol}  物种未验证={n_spec}")
assert (n_ident, n_exceed, n_tol, n_spec) == (36, 34, 34, 4)

# recovery_class / budget 全校验
assert all(dec[k]["recovery_class"] == "检索尚未完成" for k in s36)
assert all(dec[k]["new_computation_budget"] == "NONE_JUSTIFIED_YET" for k in dec)
print("recovery_class(36) = 检索尚未完成 ×36  OK")
print("new_computation_budget(48) = NONE_JUSTIFIED_YET ×48  OK")
print(f"\ncoverage_recheck.json sha = {sha(RECHECK)}")
print("\nALL ASSERTIONS PASSED")
