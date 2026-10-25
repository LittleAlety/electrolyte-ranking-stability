"""Second-round search preregistration for the states this batch cannot recover.

The strict_recovery_v1 batch can lift at most 8 of the 14 limited states; the
other 6 have no registered independent start because the FIRST search method
found nothing:

* ``AN|M_plus``, ``DMC|M_plus``, ``EMC|M_plus`` -- the GFN2 cation search ran
  (``num_confs_per_state = 64``, dedup RMSD threshold 0.35 A, seed 20261021) and
  ``strict_recovery_v1_search_index.json`` records **no new minimum** for them;
  **no per-state RMSD value exists anywhere**, so none is quoted here;
* ``DMC|LiM_2plus``, ``DOL|LiM_2plus``, ``EC|LiM_2plus`` -- the round-3
  coordination-motif search produced no new basin.

Recovering them needs a DIFFERENT search method, and the plan is explicit:
"如决定新一轮搜索，先版本化预注册新池、成本上限和停止规则，再计算；不回填旧池".
So this generator registers the CANDIDATE METHOD CHANGES and what each would
need -- it chooses nothing and launches nothing.  The user decides.

Outputs:

    outputs/physics_completion/recovery/second_search_preregistration_draft.md
    outputs/physics_completion/recovery/second_search_preregistration_index.json

``--check`` recomputes and byte-compares (read-only).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

ENS = REPO / "outputs" / "physics_completion" / "ensembles"
RECOVERY = REPO / "outputs" / "physics_completion" / "recovery"

LABELS = ENS / "production_ensemble_labels.csv"
MANIFEST = RECOVERY / "strict_recovery_v1_manifest.csv"
SEARCH_POOL = RECOVERY / "strict_recovery_v1_search_pool.csv"
# Authoritative per-state search record: num_confs_per_state / states_searched
# / per_state_new_minima.  Read by build_coverage_reviews and
# build_strict_recovery_manifest as well, so it is the single source here too.
SEARCH_INDEX = RECOVERY / "strict_recovery_v1_search_index.json"
LI_EXEC = (REPO / "outputs" / "physics_completion" / "li_motif_sampling"
           / "li_motif_round3_recovery.csv")

OUT_MD = RECOVERY / "second_search_preregistration_draft.md"
EMC_ROUND2_INDEX = RECOVERY / "strict_recovery_v2_emc_index.json"
OUT_INDEX = RECOVERY / "second_search_preregistration_index.json"

#: the method changes a second round could register, per failure mode
CATION_METHODS = (
    ("larger conformational ensemble", "每态 256 起点（当前 64），同一 ETKDGv3 但更大样本"),
    ("different embedding family", "ETKDGv2 / Omega / 系统扭转扫描（当前 ETKDGv3）"),
    ("implicit-solvent screening", "GFN2 + ALPB(acetonitrile) 而非气相（当前气相）"),
    ("higher screening level", "r2SCAN-3c 筛选（当前 GFN2），代价高约一个量级"),
)
COORD_METHODS = (
    ("wider motif enumeration", "增加给体组合与 Li 距离/角度网格（当前 1 父体 × 枚举规则）"),
    ("multiple neutral parents", "对每个中性 M 盆地都做 motif 放置，而非单一父体"),
    ("explicit-solvent motif", "在显式乙腈壳层下构造配位起点"),
    ("MD-derived snapshots", "短程 MD 采样的配位构型作为起点"),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def unrecoverable() -> list[tuple[str, str]]:
    """Limited states with NO registered independent start in the manifest."""
    labels = {(r["name"], r["state"]): r for r in _read(LABELS)}
    man = {(r["name"], r["state"]): r for r in _read(MANIFEST)}
    out = []
    for key, row in sorted(labels.items()):
        if row.get("acceptance_status") == "accepted":
            continue
        m = man.get(key, {})
        if m.get("start_1_basin") or m.get("start_2_basin"):
            continue
        out.append(key)
    return out


def _round2_status(name: str, state: str) -> str:
    """What the executed second round said about this state, if it covered it."""
    if (name, state) != ("EMC", "M_plus") or not EMC_ROUND2_INDEX.is_file():
        return ""
    import json as _json
    doc = _json.loads(EMC_ROUND2_INDEX.read_text(encoding="utf-8"))
    return doc.get("stop_rule_outcome", "")


def _reason(name: str, state: str) -> str:
    labels = {(r["name"], r["state"]): r for r in _read(LABELS)}
    return (labels.get((name, state)) or {}).get("limitation_reason", "")


def _evidence(name: str, state: str) -> str:
    if "Li" in state:
        rows = [r for r in _read(LI_EXEC)
                if r.get("leg_id", "").split("|")[0] == name
                and r.get("leg_id", "").split("|")[-1] == state]
        kept = sum(1 for r in rows if str(r.get("kept", "")).lower() == "true")
        new = sum(1 for r in rows if str(r.get("new_vs_round1", "")).lower() == "true"
                  and str(r.get("kept", "")).lower() == "true")
        return ("round-3 motif 搜索：%d 候选、保留 %d、**新独立盆地 %d**"
                % (len(rows), kept, new))
    rows = [r for r in _read(SEARCH_POOL)
            if r.get("name") == name and r.get("state") == state]
    index = _read_json(SEARCH_INDEX)
    proto = index.get("protocol") or {}
    key = "%s|%s" % (name, state)
    n_confs = proto.get("num_confs_per_state")
    threshold = proto.get("rmsd_threshold_a")
    # A recorded basin row is the only thing that licenses a RMSD number.
    rmsds = sorted({float(r["rmsd_to_nearest_known_a"]) for r in rows
                    if r.get("rmsd_to_nearest_known_a")})
    if rmsds:
        return ("首轮搜索在池内实测 **%d** 条新盆地行（`num_confs_per_state=%s`、"
                "去重阈值 %s Å、seed %s）；与最近已知极小的 RMSD 实测 **%s Å**"
                % (len(rows), n_confs, threshold, proto.get("seed"),
                   " / ".join("%.4f" % v for v in rmsds)))
    if key in (index.get("states_searched") or []):
        return ("已按首轮协议搜索过（`num_confs_per_state=%s`、seed %s、去重阈值 %s Å），"
                "但 index 的 `per_state_new_minima` **没有该态条目** ⇒ **未记录到新极小**；"
                "**逐态 RMSD 全仓无数值出处，故本行不写 RMSD**"
                % (n_confs, proto.get("seed"), threshold))
    return ("**index 的 `states_searched` 不含该态** ⇒ 如实记「未记录」；"
            "**不得把它代写为「新极小 0 个」**")


def render() -> str:
    bad = unrecoverable()
    lines = [
        # 计数由 unrecoverable() 派生：硬编码会在系综变化时静默漂移
        "# 第二轮搜索预注册稿（EMC|M_plus 已执行并排除；剩余 %d 态待用户裁决）" % len(bad),
        "",
        "> 生成器 `build_second_search_preregistration.py`（`--check` 完全只读）。",
        "> 方案原文：「如决定新一轮搜索，先版本化预注册新池、成本上限和停止规则，再计算；不回填旧池。」",
        "",
        "## 本批恢复不了的 %d 态（按限制原因分类）" % len(bad),
        "",
        "| 态 | 限制原因 | 首轮证据 |",
        "|---|---|---|",
    ]
    for name, state in bad:
        lines.append("| %s\\|%s | `%s` | %s |" % (name, state, _reason(name, state),
                                                  _evidence(name, state)))
    lines += [
        "",
        "## 已执行的第二轮：EMC|M_plus（结论：**换方法无效，已排除**）",
        "",
        "用户 2026-10-21 裁决只搜 `EMC|M_plus` 后已实测执行：GFN2-xTB + **ALPB(乙腈)**、"
        "**256** 个 ETKDGv3 起点（首轮 64）、seed 20261022，256/256 全部收敛。",
        "",
        "| 第二轮盆地 | rel (kcal/mol) | 与已有极小 RMSD | 判定 |",
        "|---|---|---|---|",
        "| v2_c042 | 0.000 | 0.0102 Å | 同一盆地 |",
        "| v2_c117 | 2.046 | 0.1181 Å | 同一盆地 |",
        "",
        "**真正新盆地 = 0** → 停止规则触发 `search_method_exhausted`。",
        "",
        "**更关键的是：这个态本来就不缺盆地**——它的 `limitation_reason` 是 "
        "`species_drift_unrecoverable`（`n_unique=2`），结构表显示 `EMC|M_plus|4` 是 "
        "`candidate_bond_graph_changed`：该盆地在生产级优化时**键图改变、重排成别的物种**。"
        "冻结协议对身份改变明令「直接判失败、不重试」，所以换任何搜索方法都补不上它。",
        "",
        "**后果（2026-10-23 更新，此前口径已作废）**：早先由此断言「WP3 的 R4 阶梯里那 2 对"
        "（EMC vs GBL、EMC vs SL）**永久停在 limited**、R4 上限就是 8/12 computed」。"
        "**该断言已过时**：`EMC|M_plus` 后来经**覆盖复核 `qualified_all`**（计入 primary 的 ready 行）"
        "放行（系综 39→41），R4 那 2 对随即可以计算。当前 `closure/flip_persistence.csv` 实测为 "
        "**6 个 rung × 2 对 = 12 格**：**10 `computed` + 2 `computed_screen_only`**，"
        "其中 **`R4` 两对均为 `computed`**、`R4_screen` 仅筛选级。"
        "**漂移结论本身的适用范围也随之收窄**：它只说明「该*失败尝试*的起点会重排成别的物种、"
        "重试无法恢复身份」，**不等于**「该态没有别的盆地」——后者要由覆盖复核判定。",
        "",
        "## 剩余 %d 态：候选方法变更（每项都需单独版本化登记，组合由用户裁决）" % len(bad),
        "",
        "### 阳离子单极小态（%s 的 M_plus）"
        % ("、".join(sorted(n for n, s in bad if s == "M_plus")) or "本次无"),
        "",
        "| 变更 | 具体做法 |",
        "|---|---|",
    ]
    for label, detail in CATION_METHODS:
        lines.append("| %s | %s |" % (label, detail))
    lines += [
        "",
        "### 配位态（DMC/DOL/EC 的 LiM_2plus）",
        "",
        "| 变更 | 具体做法 |",
        "|---|---|",
    ]
    for label, detail in COORD_METHODS:
        lines.append("| %s | %s |" % (label, detail))
    lines += [
        "",
        "## 预注册必须冻结的四件事（缺一不可）",
        "",
        "1. **方法变更的唯一定义**——写明改了哪一项（如 64→256 起点）、其余保持不变；",
        "2. **成本上限**——搜索级（GFN2，**Slurm 计算节点**；本机只做生成/校验/解析）+ "
        "生产级（每条新盆地一条 ORCA 腿，实测恢复腿均值 3–12 core-hours）；",
        "3. **停止条件**——每态新起点 ≤2；两次都无新极小 → 登记 `search_method_exhausted`，"
        "该态在冻结方法族下永久 limited；",
        "4. **不回填旧池**——新盆地进入新的版本化池，旧池记录保持原状。",
        "",
        "## 成本的量级参考（不是承诺）",
        "",
        "* 搜索级：**Slurm 计算节点**上的 GFN2（本机不得运行筛选——见 `GOAL.md:49`、"
        "`PREREGISTRATION_NEW_PROBE_CLASSES_20261023.md:39`、`P4_SUBMIT_RUNBOOK_20261024.md:40`），"
        "每态 256 起点约与首轮 64 起点同量级（分钟到半小时）；",
        "* 生产级：只在**找到新盆地时**才提交，按每态 ≤2 腿计；",
        "* 若 6 态都找到 2 个新盆地：12 腿 × ~6 core-hours ≈ **70 core-hours**；",
        "* 这批的失败模式是「搜索无果」，所以最可能的结果是**只花搜索级成本**。",
        "",
        "**本稿不选方法、不算具体预算、不启动任何计算。已执行的部分只有 EMC|M_plus（用户授权），"
        "其余 %d 态的选定由用户裁决。**" % len(bad),
        "",
    ]
    return "\n".join(lines)


def write_outputs() -> None:
    RECOVERY.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(render(), encoding="utf-8", newline="\n")
    index = {
        "schema_version": "1.0",
        "provenance": "sha256-of-inputs (deterministic; no wall clock)",
        "generator": "scripts/wp_production/build_second_search_preregistration.py",
        "inputs": {str(p.relative_to(REPO)): _sha256(p)
                   for p in (LABELS, MANIFEST, SEARCH_POOL, LI_EXEC) if p.is_file()},
        "decision": "NO method chosen; NO new search launched",
        "unrecoverable_states": ["%s|%s" % k for k in unrecoverable()],
        "rule": ("a second search must be versioned and preregistered (method change, "
                 "cost cap, stop rule) BEFORE any calculation; the old pool is never "
                 "back-filled"),
    }
    OUT_INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8", newline="\n")


def check() -> int:
    disk = OUT_MD.read_text(encoding="utf-8") if OUT_MD.is_file() else ""
    if disk != render():
        print("CHECK FAILED -- %s drifted" % OUT_MD.name)
        return 1
    print("CHECK OK -- second-search preregistration matches recomputation")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="READ-ONLY: recompute in memory and byte-compare")
    args = ap.parse_args(argv)
    if args.check:
        return check()
    write_outputs()
    _n = len(unrecoverable())
    print("second-search draft: %d unrecoverable states; EMC|M_plus excluded by execution, "
          "the other %d await a ruling" % (_n, _n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
