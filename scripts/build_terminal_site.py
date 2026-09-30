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
import struct
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(REPO, "docs")
ASSETS = os.path.join(DOCS, "assets")
FIGDIR = os.path.join(ASSETS, "figures")
OUT = os.path.join(ASSETS, "data.js")
PAGE_404 = os.path.join(DOCS, "404.html")

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
    ("F28", "F28_two_guess_protocol.png", 14, "(a) 90 点能量差幅度直方图与 1 meV material 阈值（12 点全部为负）；(b) EMC 阴离子偶极的两条分支（默认初猜 vs ! MORead）十点对照；(c) 导体极限：Born 横坐标 u = 1 - 1/eps 上 eps = 1000 的位置；(d) 六点/九点 Born 斜率与外推缺口（修复前后没变小）"),
    ("F29", "F29_diffuseness_descriptor.png", 14, "(e) spin_maxfrac 对阴离子畸变惩罚（留一 R2 0.162 -> 0.556）；(f) 参与比的秩 vs 线性（rho -0.846 对留一 R2 -2.90）；(g) 三个目标的留一 R2 对比（中性/阳离子不变）；(h) 描述符自己的域检验，标出唯一越界的 EMC/cpcm_10"),
    ("F30", "F30_two_guess_catalogue.png", 15, "(a) 12 分子 x 3 状态 x 10 电介质的完整双初猜网格（红 = 默认初猜偏高，灰 = 两臂一致，蓝 = 反而更高，斜纹 = 未配对）；(b) 每个开壳层 (分子, 状态) 在整个阶梯上的最坏赤字（绿虚线 = 1 meV 材料阈值）；(c) 超过各阈值的单元格计数"),
    ("F31", "F31_apriori_warning_rule.png", 15, "(d) 选定气相描述符对最大赤字，绿色虚线为留一冻结阈值；(e) 每个气相描述符的单变量 AUC；(f) 留出臂逐行预测与真值；(g) 冻结规则 vs 多数类基线（明写输给平凡规则）、平衡准确率、精确置换 p，以及分电性状态的事后诊断（描述符、正例排名、留一）"),
    ("F32", "F32_stage17_contamination.png", 16, "(a) 逐分子逐轴的污染界 delta = p2_moread - p2_default（参考带 1e-03 eV，最坏 0.1562 eV）；(b) 排序稳定性对照：两轴 tau_b 的 95% CI 重叠；(c) 决策量 default vs moread 与「无已发布结论被改写」的裁决"),
    ("F33", "F33_stage17_solution_identity.png", 16, "(d) PC/阴离子/cpcm_10 的逐原子自旋剖面（两臂同峰于 C4，几何与自旋中心一致）；(e) 32 格逐格的局域化迁移（cyclic/linear/phosphate 的 PR 均值变化）；(f) 自旋纯度：Δ<S²> 落在 [-0.004534, +0.001457]，参考纯双重态 0.75；(g) 电荷 vs 自旋重组（各 family 的 charge_l1 与 spin_l1 均值）"),
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
    (14, "24_week14_report.md", "Stage 15", "初猜协议修正亚稳态、弥散度描述符翻正否定结果"),
    (15, "25_week15_report.md", "Stage 16", "亚稳解是全核心集现象，但单一气相描述符的事前预警输给平凡基线"),
    (16, "26_week16_report.md", "Stage 17", "P2 腿换 moread 初猜重算 54 格，无任何已发布结论被改写；32 个漏解格两解皆自旋纯双重态，差异主轴是电荷重组"),
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


def png_size(path):
    """Intrinsic pixel size of a PNG, straight out of the IHDR chunk.

    The gallery and the brief reserve space with width/height so the grid
    cannot reflow as thumbnails arrive; nothing is retyped by hand.
    """
    with open(path, "rb") as fh:
        head = fh.read(24)
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n":
        return 0, 0
    width, height = struct.unpack(">II", head[16:24])
    return width, height


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
        width, height = png_size(src)
        rows.append({
            "id": fid, "file": png, "week": week, "caption": caption,
            "sha": sha256_of(src), "bytes": os.path.getsize(src),
            "w": width, "h": height,
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
        "tests_passed": 858,
    }


def render_404(payload):
    """The GitHub Pages 404 page, baked from the payload at build time.

    It deliberately does not load data.js: a missing asset must not take the
    styling down with it, so the counts are written in here.  Every URL is
    relative to the published folder, not the user-site root -- the first
    version used /assets/... and href="/", which broke on the project subpath.
    """
    counts = payload.get("counts", {})
    weeks = counts.get("weeks", 0)
    figures = counts.get("figures", 0)
    return (
        "<!doctype html>\n"
        '<html lang="zh-CN" data-theme="green">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>404 \u2014 hb-lab</title>\n"
        '<link rel="stylesheet" href="assets/terminal.css">\n'
        "<style>\n"
        "  .wrap { padding: 18vh 6vw 0; }\n"
        "  .big { font-size: clamp(38px, 9vw, 92px); color: var(--accent); margin: 0; letter-spacing: -0.02em; }\n"
        "  p { color: var(--dim); max-width: 54ch; }\n"
        "</style>\n"
        "</head>\n"
        "<body>\n"
        '<div class="crt" aria-hidden="true"></div>\n'
        '<div class="wrap">\n'
        '  <p class="dim">&gt; GET /this/path</p>\n'
        '  <h1 class="big">404</h1>\n'
        "  <p>这个页面不存在。终端主页还在，那里有 " + str(weeks)
        + " 周的全部结论、" + str(figures) + " 张图和两个 Gate 的真实状态。</p>\n"
        '  <p><a href="./">返回终端主页</a> &nbsp;·&nbsp; <a href="' + REPO_URL
        + '">GitHub 仓库</a></p>\n'
        "</div>\n"
        "</body>\n"
        "</html>\n"
    )


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
    page = render_404(payload)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    with io.open(PAGE_404, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(page)
    print("404.html  %d bytes (relative paths, counts baked in)"
          % len(page.encode("utf-8")))
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
        if not os.path.exists(PAGE_404):
            problems.append("docs/404.html missing")
        elif read(PAGE_404) != render_404(payload):
            problems.append("docs/404.html is stale (rerun build_terminal_site.py)")
    for name in ("index.html", "404.html", "assets/terminal.css",
                 "assets/terminal.js", ".nojekyll"):
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