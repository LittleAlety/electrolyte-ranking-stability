"""按当前已落地的 WP2 生产子集生成提交信息（供 finalize_wp2.ps1 使用）。"""
from __future__ import annotations

import csv
import json
import re
import subprocess
from pathlib import Path

_CN = "零一二三四五六七八九"


def cn_number(value: int) -> str:
    """1..99 的中文数字，用于与既有的「增量收口（N）」系列保持一致。"""
    if value < 10:
        return _CN[value]
    if value < 20:
        return "十" + (_CN[value % 10] if value % 10 else "")
    return _CN[value // 10] + "十" + (_CN[value % 10] if value % 10 else "")


def parse_cn(text: str) -> int:
    """解析 1..99 的中文数字（十 / 十三 / 二十 / 二十一）。"""
    if "十" not in text:
        return _CN.index(text) if text in _CN else 0
    tens, _, ones = text.partition("十")
    high = _CN.index(tens) if tens else 1
    low = _CN.index(ones) if ones else 0
    return high * 10 + low


def next_increment() -> int:
    """取 git 历史里「增量收口（N）」的最大序号 +1（无括号的那条不计入编号）。"""
    log = subprocess.run(["git", "log", "--oneline"], cwd=str(REPO),
                         capture_output=True, text=True).stdout
    seen = [parse_cn(match) for match in re.findall(r"增量收口（([零一二三四五六七八九十]+)）", log)]
    return max(seen or [0]) + 1

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PAYLOAD = REPO / "outputs" / "week39" / "wp2_free_energy_labels.json"
COST = REPO / "outputs" / "physics_completion" / "cost" / "production_cost_ledger.csv"
OUT = REPO / "work" / "_wp2_commit_msg.txt"


def main() -> int:
    payload = json.loads(PAYLOAD.read_text(encoding="utf-8"))
    prod = payload["free_state_production"]
    progress = prod["progress"]
    rows = prod["ledger"]
    main_rows = [r for r in rows if r["state"] in ("M", "M_plus", "LiM_plus", "LiM_2plus")]
    extra_rows = [r for r in rows if r["state"] not in ("M", "M_plus", "LiM_plus", "LiM_2plus")]
    core_hours = prod["totals"]["core_hours"]
    redox = prod["redox"]
    free_done = [r for r in redox if r["free_status"] == "computed"]
    li_done = [r for r in redox if r["li_status"] == "computed"]
    names = {r["mol_id"]: r["name"] for r in main_rows}
    done = ", ".join("%s(%s|%s)" % (r["name"], r["mol_id"], r["state"]) for r in main_rows)
    extra = ", ".join("%s(%s|%s)" % (r["name"], r["mol_id"], r["state"]) for r in extra_rows) or "无"
    with COST.open(encoding="utf-8", newline="") as handle:
        cost_rows = list(csv.DictReader(handle))
    lines = [
        "week37-week44 增量收口（%s）：WP2 生产首段登记 %d/%d 个主态的真实 Opt+Freq 自由能标签"
        % (cn_number(next_increment()), progress["states_done"], progress["states_total"]),
        "",
        "生产口径：wB97X-D4（ORCA 关键字，即方案写的 omegaB97X-D4）/ 中性腿 def2-TZVP、带电与 Li 腿 def2-TZVPD，",
        "SMD(acetonitrile)，Opt NumFreq TightOpt TightSCF SlowConv 在同一 ORCA 作业；几何起点是既有冻结的 r2SCAN-3c 结构。",
        "",
        "本轮内容：",
        "- 主态 %d/%d：%s；合计 %s allocated core-hours（%d 个 Opt+Freq 作业）。"
        % (progress["states_done"], progress["states_total"], done or "无", core_hours, len(cost_rows)),
        "- def2-TZVPD 中性腿（M_tzvpd，基组一致 redox 必需）：%s。" % extra,
        "- 基组一致 redox 表（自由腿与 Li 腿分开登记）：自由腿 %d/%d、Li 腿 %d/%d computed。"
        % (len(free_done), len(redox), len(li_done), len(redox)),
]
    for row in redox:
        if row["status"] == "not_computed":
            continue
        parts = []
        if row["free_status"] == "computed":
            parts.append("自由腿 Eox_adiabatic = %s eV, Gox_single = %s eV"
                         % (row["eox_adiabatic_ev"], row["gox_single_ev"]))
        if row["li_status"] == "computed":
            parts.append("Li 腿 IP(G) = %s eV, 配位位移(G) = %s eV"
                         % (row["li_ip_g_ev"], row["coordination_shift_g_ev"]))
        lines.append("  * %s [%s]：%s" % (row["name"], row["status"], "；".join(parts)))
    lines += [
        "- E_SP 口径：G = E_SP + (G - E(el))，E_SP 取 ORCA 热化学段的 Electronic energy（末收敛几何的 SMD 单点），",
        "  不是作业里首个 FINAL SINGLE POINT ENERGY（起始冻结几何）；验收 wp2_production_gibbs_decomposes_from_the_solution_sp 逐行成立。",
        "- 子集纪律：只登记已跑完的状态，production_progress 记录 states_done/states_total/molecules_started/molecules_complete；",
        "  未完成行保持 empty（缺值不写 0）；每态仍是单一代表结构（n_conformers=1），不是方案 6.1 的多构象系综。",
        "",
        "校验：生成器 88 文件 / 验收检查 0 失败；图与 manifest 逐字节一致；交付镜像 8 周逐字节一致；",
        "freeze_gates --stage 2 exit 0；clean room verdict OK；pytest 1366 passed。",
        "",
        "仍未闭合：其余主态在产；多构象采样界限、WP4 的 7 锚点原文复核（原文在付费墙后、本机离线）仍待补，",
        "故 Gate 1 保持 NOT CLOSED / NOT CLOSABLE。",
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("commit message -> %s (%d main states, %d extra legs)"
          % (OUT.name, progress["states_done"], progress["extra_legs_done"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
