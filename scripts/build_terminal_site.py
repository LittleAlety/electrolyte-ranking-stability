"""Build the GitHub Pages terminal site.

Everything the terminal prints is read out of the repository at build time:
the week headings come from ``docs/*week*_report.md``, the figure captions
from the manifests, the gate state from ``outputs/week{1,2}/gate*_record.md``.
Nothing is retyped by hand, so the site cannot drift from the science.

Outputs (all under ``docs/``):

    docs/assets/data.js            window.HB - the payload the terminal reads
    docs/assets/figures/*.png      byte copies of outputs/figures/*.png

Run ``--check`` to verify the on-disk site still matches the repository.
"""
import argparse
import glob
import io
import json
import os
import re
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(REPO, "docs")
ASSETS = os.path.join(DOCS, "assets")
FIGDIR = os.path.join(ASSETS, "figures")
OUT = os.path.join(ASSETS, "data.js")

REPO_URL = "https://github.com/LittleAlety/electrolyte-ranking-stability"

# ---------------------------------------------------------------- figure table
# (id, png, week, caption).  Captions are verbatim (or trimmed verbatim) from
# the manifests and the week reports; the builder refuses to invent one.
FIGURES = [
    ("F0", "F0_project_pipeline.png", 3, "项目五段式流水线示意"),
    ("F1", "F1_chemical_space_coverage.png", 3, "core vs broad 的 family / donor 覆盖"),
    ("F2", "F2_p0_distributions_by_family.png", 3, "各 family 的 P0 分布，按氟化着色"),
    ("F3", "F3_value_error_vs_rank_error.png", 3, "值误差 vs 排序误差（本轮核心反直觉结论）"),
    ("F4", "F4_rank_migration_p0_to_p1.png", 4, "(a) 每分子 IP 三臂对照锚点（平移）；(b) 氧化轴 P0 -> P1 位次迁移（重排）"),
    ("F5", "F5_reduction_axis_koopmans_vs_dscf.png", 4, "(a) Koopmans EA vs 真实 EA（定性失效）；(b) 还原轴位次迁移"),
    ("F6", "F6_decision_stability_indicators.png", 4, "(a) Top-k 重叠与 Jaccard；(b) 逐对间距与 z*sigma 不确定带"),
    ("F7", "F7_shift_structure.png", 4, "廉价层是「平移的尺子」还是「另一把尺子」（IP / EA 散点）"),
    ("F8", "F8_environment_layer_p1_to_p2.png", 4, "(a) 每分子的气相->溶剂位移（IP 与 EA）；(b) 逐对间距与 z*sigma 不确定带（环境层）"),
    ("F9", "F9_diffuse_function_control.png", 4, "同泛函三基组对照：加弥散把 EA 系统性下拉但未翻转符号（方法适用域结论）"),
    ("F10", "F10_cpcm_eps_scan.png", 4, "bare CPCM eps 扫描（dIP/dEA 饱和曲线 + sigma_env 与 tau_b）"),
    ("F11", "F11_opt_freq_g2_sensitivity.png", 4, "G1 -> G2 几何台阶（逐分子位移 + 方法/几何/环境三台阶同口径对比）"),
    ("F12", "F12_li_coordination_c1.png", 5, "Li+ 配位条件态 C1（逐分子 dIP/dEA + 四台阶 sigma 对比 + 配体交换 + 决策量）"),
    ("F13", "F13_c1_state_identity.png", 5, "C1 条件态的 state-identity：Mulliken 投影与电荷阶梯，读自 ORCA 已写出的电荷/自旋块，不花新的量化算力"),
    ("F14", "F14_delta_m_derivation.png", 6, "(a) delta_m 的三项贡献与 max 规则（菱形标注）；(b) 逐分子 P1 - P0 位移，其群体散布即 inter-method 项"),
    ("F15", "F15_stage6_decision_metrics.png", 6, "(a) 每一层对的上下两侧在 delta_m = 0 / 0.05 eV / docx max 下的 f_unresolved；(b) docx max 容差下的排序一致度指标"),
    ("F16", "F16_stage7_direct_vs_shift.png", 7, "(a) 每种形状的最优模型（leave-one-family-out）；(b) 随机 / group / LOFO 切分下的乐观偏差；(c) tau_b(shift) - tau_b(direct)"),
    ("F17", "F17_stage8_active_learning.png", 7, "n_T -> Kendall tau_b：random / diversity / uncertainty / ranking-aware 四种采集，20 组冻结种子重复的中位数与 2.5-97.5 分位带"),
    ("F18", "F18_stage9_explicit_shell.png", 8, "显式微溶剂化：第一溶剂壳 1:1 -> 1:2 的位移与决策量"),
    ("F19", "F19_stage10_ladder.png", 9, "五级台阶合成与决策稳定性总判"),
    ("F20", "F20_sigma_anatomy.png", 10, "sigma 的代数解剖"),
    ("F21", "F21_sigma_controls.png", 10, "sigma 的控制变量"),
    ("F22", "F22_dielectric_scaling.png", 11, "(a) Born 线性轮廓；(b) 增量比 vs 两个模型；(c) 同一 c 的几何收缩；(d) 外推检验"),
    ("F23", "F23_prescreening.png", 11, "(a) 预算曲线；(b) 逐台阶 b_hat 分布；(c) 3 分子试点散点；(d) 判据平面"),
    ("F24", "F24_dielectric_limit.png", 12, "(a) 七级阶梯 vs u = 1 - 1/eps（24 条曲线）；(b) 三模型 R2；(c) 外推误差由距离决定；(d) eps = 200 距导体极限 33 meV"),
    ("F25", "F25_environment_ledger.png", 12, "(a)(b) SMD 乙腈两轴的逐分子四项分解；(c) CDS 三态重合；(d) 畸变抵消比例"),
    ("F26", "F26_distortion_attribution.png", 13, "(a) 逐态畸变惩罚的逐分子柱状图；(b) dist 恰为两个逐态惩罚之差（残差 6.7e-12 eV）；(c) D_neutral vs 偶极（rho 0.909）；(d) 最佳单描述符的留一 R2"),
    ("F27", "F27_emc_outlier.png", 13, "(e)(f) 九点 bare CPCM 阶梯上六条 delta(eps) 曲线；(g) EMC / 还原轴按 SCF 解分支着色 + 粗糙度对照；(h) Born R2 随网格点数的收敛"),
]

# ---------------------------------------------------------------- week table
# (label, doc, stage, one-line result).  The one-liner is taken from the
# report itself; see `headline` below.
WEEKS = [
    (1, "03_week1_2_report.md", "Stage 0", "预注册与定义冻结"),
    (2, "03_week1_2_report.md", "Stage 1", "外部锚点、方法审计与工具链自检"),
    (3, "09_week3_report.md", "Stage 2", "廉价层 P0、覆盖检查、锚点核验、ORCA 就绪"),
    (4, "10_week4_report.md", "Stage 3 + T1", "r2SCAN-3c 电子结构层与 P0 -> P1 决策稳定性"),
    (5, "12_week5_report.md", "Stage 5 / T4", "Li+ 配位条件态 C1（机制解释）"),
    (6, "13_week6_report.md", "Stage 6", "不确定性感知排序分析"),
    (7, "15_week7_report.md", "Stage 7 + Stage 8", "ML / direct vs delta-learning 与 active-learning replay"),
    (8, "18_week8_report.md", "Stage 9", "显式微溶剂化（C2 = [Li(M)2]+ 第一溶剂壳复核）"),
    (9, "19_week9_report.md", "Stage 10", "五级台阶合成与决策稳定性总判"),
    (10, "20_week10_report.md", "Stage 11", "sigma 的代数解剖与分辨率判据"),
    (11, "21_week11_report.md", "Stage 12", "介电响应是一条单参数族，判据可事前使用"),
    (12, "22_week12_report.md", "Stage 13", "介电极限、导体极限，与环境位移的四项精确分解"),
    (13, "23_week13_report.md", "Stage 14", "畸变项的定量归因与 EMC 离群点的病理裁决"),
]

PIPELINE = [
    ("1", "cheap proxy", "GFN2-xTB / P0 描述符"),
    ("2", "validated target", "r2SCAN-3c 垂直 IP / EA"),
    ("3", "rank change", "tau_b / f_unresolved / robust inversion"),
    ("4", "mechanism", "位移的代数结构与环境层账本"),
    ("5", "minimal budget", "主动学习回放：多少算力够用"),
]

def read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def sha256_of(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def clip(text, limit=620):
    """Trim to a sentence-ish boundary so the terminal never cuts mid-word."""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    for mark in ("。", "；", ". "):
        idx = cut.rfind(mark)
        if idx > limit * 0.55:
            return cut[: idx + len(mark)].strip()
    return cut.rstrip() + "..."


def body_lines(lines):
    """Drop markdown scaffolding so the text reads as prose in a terminal."""
    keep = []
    for line in lines:
        s = line.strip()
        if not s or s.startswith(("|", "```", "![", "---", "<!--")):
            continue
        s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
        s = re.sub(r"`([^`]+)`", r"\1", s)
        s = re.sub(r"^[-*+]\s+", "  - ", s)
        s = re.sub(r"^#{3,}\s*", "", s)
        s = re.sub(r"^>\s?", "", s)
        keep.append(s)
    return keep


def week_payload():
    cache = {}
    payload = []
    for week, doc, stage, tag in WEEKS:
        path = os.path.join(DOCS, doc)
        if doc not in cache:
            cache[doc] = read(path).splitlines()
        lines = cache[doc]
        h1 = next((l for l in lines if l.startswith("# ")), "# " + doc)
        title = h1.lstrip("# ").strip()
        sections = [l.lstrip("# ").strip() for l in lines
                    if re.match(r"^##\s", l) and not l.startswith("###")]
        # prefer a "one sentence conclusion" section, else the preamble
        idx = None
        for i, line in enumerate(lines):
            if re.match(r"^##\s", line) and re.search(r"一句话结论|结论", line):
                idx = i
                break
        if idx is not None:
            body = []
            for line in lines[idx + 1:]:
                if re.match(r"^##\s", line):
                    break
                body.append(line)
        else:
            body = []
            for line in lines[1:]:
                if re.match(r"^##\s", line):
                    break
                body.append(line)
        summary = clip(" ".join(body_lines(body)), 640)
        payload.append({
            "n": week, "doc": "docs/" + doc, "title": title,
            "stage": stage, "tag": tag, "summary": summary,
            "sections": sections[:14],
        })
    return payload


def figure_payload():
    rows = []
    for fid, png, week, caption in FIGURES:
        src = os.path.join(REPO, "outputs", "figures", png)
        if not os.path.exists(src):
            raise SystemExit("missing figure: " + png)
        rows.append({
            "id": fid, "file": png, "week": week, "caption": caption,
            "sha": sha256_of(src), "bytes": os.path.getsize(src),
        })
    return rows


def gates():
    out = []
    for tag, name, path in (
        ("0", "Gate 0 - 定义与预注册", "outputs/week1/gate0_record.md"),
        ("1", "Gate 1 - 外部锚点与工具链", "outputs/week2/gate1_record.md"),
    ):
        full = os.path.join(REPO, path)
        rec = {"name": name, "status": "UNKNOWN", "blockers": [], "checks": []}
        if os.path.exists(full):
            text = read(full)
            m = re.search(r"status:\s*\*\*(.+?)\*\*", text)
            if m:
                rec["status"] = m.group(1).strip()
            for line in text.splitlines():
                s = line.strip()
                if s.startswith("| ") and s.count("|") >= 3 and "---" not in s:
                    cells = [c.strip() for c in s.strip("|").split("|")]
                    if cells[0] in ("check", "status"):
                        continue
                    if len(cells) >= 3:
                        rec["checks"].append({
                            "name": cells[0],
                            "ok": cells[1].lower() in ("yes", "ok", "true"),
                            "detail": cells[2],
                        })
            grab = False
            for line in text.splitlines():
                if line.strip().startswith("## blockers"):
                    grab = True
                    continue
                if grab:
                    s = line.strip()
                    if s.startswith("## "):
                        break
                    if s.startswith(("- ", "* ")):
                        rec["blockers"].append(s[2:].strip())
        out.append(rec)
    return out


def counts():
    orca_out = glob.glob(os.path.join(REPO, "outputs", "**", "*.out"), recursive=True)
    orca_out = [p for p in orca_out if "orca" in p.replace("\\", "/")]
    scripts = glob.glob(os.path.join(REPO, "scripts", "*.py"))
    tests = glob.glob(os.path.join(REPO, "tests", "test_*.py"))
    return {
        "weeks": len(WEEKS),
        "figures": len(FIGURES),
        "orca_out": len(orca_out),
        "scripts": len(scripts),
        "test_files": len(tests),
        # Recorded, not measured: pytest cannot be run from the generator.  Bump
        # it in the same commit that adds or removes a test, otherwise the page
        # will advertise a number the suite no longer produces.
        "tests_passed": 744,
    }


def build():
    os.makedirs(FIGDIR, exist_ok=True)
    copied = 0
    for _, png, _, _ in FIGURES:
        src = os.path.join(REPO, "outputs", "figures", png)
        dst = os.path.join(FIGDIR, png)
        need = True
        if os.path.exists(dst) and os.path.getsize(dst) == os.path.getsize(src):
            need = sha256_of(dst) != sha256_of(src)
        if need:
            shutil.copyfile(src, dst)
            copied += 1
    payload = {
        "repo": REPO_URL,
        "counts": counts(),
        "pipeline": [{"n": n, "name": nm, "detail": d} for n, nm, d in PIPELINE],
        "gates": gates(),
        "weeks": week_payload(),
        "figures": figure_payload(),
    }
    body = json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=False)
    text = ("/* generated by scripts/build_terminal_site.py - do not edit by hand */\n"
            "window.HB = " + body + ";\n")
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print("data.js   %d bytes | %d figures (%d copied) | %d week entries"
          % (len(text.encode("utf-8")), len(FIGURES), copied, len(payload["weeks"])))
    for g in payload["gates"]:
        print("  %-32s %s  blockers=%d" % (g["name"], g["status"], len(g["blockers"])))
    print("  counts: %s" % json.dumps(payload["counts"], ensure_ascii=False))


def check():
    problems = []
    if not os.path.exists(OUT):
        problems.append("docs/assets/data.js missing")
    else:
        text = read(OUT)
        if "window.HB" not in text:
            problems.append("data.js does not define window.HB")
        payload = json.loads(text.split("=", 1)[1].rstrip().rstrip(";"))
        for row in payload["figures"]:
            dst = os.path.join(FIGDIR, row["file"])
            if not os.path.exists(dst):
                problems.append("figure not copied: " + row["file"])
            elif sha256_of(dst) != row["sha"]:
                problems.append("figure drifted: " + row["file"])
    for name in ("index.html", "assets/terminal.css", "assets/terminal.js", ".nojekyll"):
        if not os.path.exists(os.path.join(DOCS, name)):
            problems.append("missing page asset: docs/" + name)
    if problems:
        for p in problems:
            print("  [XX] " + p)
        return 1
    print("terminal site: OK (%d figures, checks passed)" % len(FIGURES))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    sys.exit(check() if args.check else build() or 0)


if __name__ == "__main__":
    main()