# -*- coding: utf-8 -*-
"""生成《电解液溶剂氧化还原描述符的决策稳定性》结题论文 docx。
字体/字号/行距严格按 WHU 模板：正文五号宋体/Times New Roman、固定行距 15 磅、
首行缩进 21.6 磅(2 字符)；一级标题小四宋体加粗；图题小五加粗居中；表内六号；参考文献 7.5 磅悬挂缩进。
"""
import io, os, sys, json, datetime
from docx import Document
from docx.shared import Pt, Cm, Inches, RGBColor, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

ROOT = r"E:\Claude Code\电解液溶剂-HB"
REPO = os.path.join(ROOT, "电解液溶剂HB-Code")
FIGDIR = os.path.join(REPO, "outputs", "figures")
OUT = os.environ.get("PAPER_OUT") or os.path.join(ROOT, "论文", "电解液溶剂氧化还原描述符决策稳定性_结题论文.docx")

CN = "宋体"
EN = "Times New Roman"
CN_HEI = "黑体"
EN_ARIAL = "Arial"

BODY_PT = 10.5      # 五号
H1_PT = 12.0        # 小四
H2_PT = 10.5        # 五号
CAP_PT = 9.0        # 小五
TAB_PT = 7.5        # 六号
REF_PT = 7.5
LINE_PT = 15.0
INDENT_PT = 21.6    # 2 字符


def _font(run, size=None, bold=None, cn=CN, en=EN, italic=None):
    f = run.font
    if size is not None:
        f.size = Pt(size)
    if bold is not None:
        f.bold = bold
    if italic is not None:
        f.italic = italic
    f.color.rgb = RGBColor(0, 0, 0)
    rPr = run._element.get_or_add_rPr()
    rf = rPr.get_or_add_rFonts()
    rf.set(qn("w:ascii"), en)
    rf.set(qn("w:hAnsi"), en)
    rf.set(qn("w:eastAsia"), cn)
    rf.set(qn("w:cs"), en)


import re as _re
SUB_RE = _re.compile(r"_([A-Za-z0-9]+)")


def _emit(p, text, size, bold=None, cn=CN, en=EN):
    for i, seg in enumerate(text.split("**")):
        if not seg:
            continue
        b = bold if (i % 2 == 0) else True
        pos = 0
        for m in SUB_RE.finditer(seg):
            if m.start() > pos:
                r = p.add_run(seg[pos:m.start()])
                _font(r, size, bold=b, cn=cn, en=en)
            r = p.add_run(m.group(1))
            _font(r, size, bold=b, cn=cn, en=en)
            r.font.subscript = True
            pos = m.end()
        if pos < len(seg):
            r = p.add_run(seg[pos:])
            _font(r, size, bold=b, cn=cn, en=en)


def _para(doc, align=None, line=LINE_PT, indent=None, before=0.0, after=0.0):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    if align is not None:
        pf.alignment = align
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = Pt(line)
    if indent is not None:
        pf.first_line_indent = Pt(indent)
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pPr = p._element.get_or_add_pPr()
    sg = OxmlElement("w:snapToGrid")
    sg.set(qn("w:val"), "0")
    pPr.append(sg)
    return p


def body(doc, text, indent=INDENT_PT):
    p = _para(doc, WD_ALIGN_PARAGRAPH.JUSTIFY, indent=indent)
    _emit(p, text, BODY_PT)
    return p


def h1(doc, text):
    p = _para(doc, WD_ALIGN_PARAGRAPH.LEFT, before=6.0, after=2.0)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    _font(r, H1_PT, bold=True)
    return p


def h2(doc, text):
    p = _para(doc, WD_ALIGN_PARAGRAPH.LEFT, before=3.0, after=1.0)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    _font(r, H2_PT, bold=True)
    return p


def h3(doc, text):
    p = _para(doc, WD_ALIGN_PARAGRAPH.LEFT, before=2.0, after=1.0)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    _font(r, H2_PT, bold=True)
    return p


def caption(doc, text):
    p = _para(doc, WD_ALIGN_PARAGRAPH.CENTER, line=13.0, before=2.0, after=4.0)
    p.paragraph_format.keep_together = True
    _emit(p, text, CAP_PT, bold=True)
    return p


def caption_en(doc, text):
    p = _para(doc, WD_ALIGN_PARAGRAPH.CENTER, line=13.0, before=1.0, after=6.0)
    r = p.add_run(text)
    _font(r, CAP_PT, bold=False, en=EN_ARIAL, cn=CN_HEI)
    return p


def figure(doc, fname, cap, width_in=6.3):
    path = os.path.join(FIGDIR, fname)
    if not os.path.exists(path):
        raise SystemExit("missing figure: " + path)
    p = _para(doc, WD_ALIGN_PARAGRAPH.CENTER, line=15.0, before=4.0, after=2.0)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.keep_together = True
    r = p.add_run()
    r.add_picture(path, width=Inches(width_in))
    caption(doc, cap)

def _set_border(el, tag, sz=None, val="single"):
    b = OxmlElement(tag)
    if val == "none":
        b.set(qn("w:val"), "none")
        b.set(qn("w:sz"), "0")
        b.set(qn("w:space"), "0")
    else:
        b.set(qn("w:val"), "single")
        b.set(qn("w:sz"), str(sz))
        b.set(qn("w:space"), "0")
        b.set(qn("w:color"), "000000")
    el.append(b)


def _three_line(table, header_rows=1, top_sz=12, mid_sz=6, bot_sz=12):
    tbl = table._tbl
    tblPr = tbl.tblPr
    for old in tblPr.findall(qn("w:tblBorders")):
        tblPr.remove(old)
    bd = OxmlElement("w:tblBorders")
    _set_border(bd, "w:top", top_sz)
    _set_border(bd, "w:bottom", bot_sz)
    _set_border(bd, "w:left", val="none")
    _set_border(bd, "w:right", val="none")
    _set_border(bd, "w:insideH", val="none")
    _set_border(bd, "w:insideV", val="none")
    tblPr.append(bd)
    for cell in table.rows[header_rows - 1].cells:
        tcPr = cell._tc.get_or_add_tcPr()
        for old in tcPr.findall(qn("w:tcBorders")):
            tcPr.remove(old)
        cbd = OxmlElement("w:tcBorders")
        _set_border(cbd, "w:bottom", mid_sz)
        tcPr.append(cbd)


def table_3line(doc, headers, rows, tab_caption=None, tab_caption_en=None, widths=None,
                body_pt=TAB_PT, head_pt=TAB_PT):
    if tab_caption:
        p = _para(doc, WD_ALIGN_PARAGRAPH.CENTER, line=13.0, before=4.0, after=1.0)
        r = p.add_run(tab_caption)
        _font(r, CAP_PT, bold=True)
    t = doc.add_table(rows=0, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = True
    hr = t.add_row()
    for j, htxt in enumerate(headers):
        cell = hr.cells[j]
        cell.text = ""
        p = cell.paragraphs[0]
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        p.paragraph_format.line_spacing = Pt(11.0)
        p.paragraph_format.space_before = Pt(1.0)
        p.paragraph_format.space_after = Pt(1.0)
        _emit(p, htxt, head_pt, bold=True)
    for row in rows:
        tr = t.add_row()
        for j, val in enumerate(row):
            cell = tr.cells[j]
            cell.text = ""
            p = cell.paragraphs[0]
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
            p.paragraph_format.line_spacing = Pt(11.0)
            p.paragraph_format.space_before = Pt(0.5)
            p.paragraph_format.space_after = Pt(0.5)
            _emit(p, str(val), body_pt, bold=False)
    _three_line(t, 1)
    if tab_caption_en:
        p = _para(doc, WD_ALIGN_PARAGRAPH.CENTER, line=12.0, before=1.0, after=6.0)
        r = p.add_run(tab_caption_en)
        _font(r, 8.0, bold=False, en=EN_ARIAL, cn=CN_HEI)
    return t


def add_page_number_footer(section):
    p = section.footer.paragraphs[0]
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    _font(run, 9.0)
    fld1 = OxmlElement("w:fldChar"); fld1.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText"); instr.set(qn("xml:space"), "preserve"); instr.text = " PAGE "
    fld2 = OxmlElement("w:fldChar"); fld2.set(qn("w:fldCharType"), "end")
    run._element.append(fld1); run._element.append(instr); run._element.append(fld2)


def setup_document():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.left_margin = Cm(2.30)
    sec.right_margin = Cm(2.30)
    sec.top_margin = Cm(3.44)
    sec.bottom_margin = Cm(3.00)
    sec.header_distance = Cm(1.50)
    sec.footer_distance = Cm(1.75)
    # 正文默认样式（兜底）
    st = doc.styles["Normal"]
    st.font.name = EN
    st.font.size = Pt(BODY_PT)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), CN)
    # 页眉：按要求留空（不要页眉）
    hp = sec.header.paragraphs[0]
    hp.text = ""
    add_page_number_footer(sec)
    return doc

def title_block(doc):
    # 中文题目：三号(16pt) 中文宋体加粗 / 英文 Arial 加粗
    p = _para(doc, WD_ALIGN_PARAGRAPH.LEFT, line=18.0, after=2.0)
    r = p.add_run("电解液溶剂氧化还原描述符的决策稳定性：")
    _font(r, 16.0, bold=True, cn=CN, en=EN_ARIAL)
    p = _para(doc, WD_ALIGN_PARAGRAPH.LEFT, line=18.0, after=4.0)
    r = p.add_run("方法—环境—几何台阶下的排序鲁棒性与最小信息预算")
    _font(r, 16.0, bold=True, cn=CN, en=EN_ARIAL)
    # 作者
    p = _para(doc, WD_ALIGN_PARAGRAPH.LEFT, line=LINE_PT, after=0.0)
    r = p.add_run("")  # 作者姓名留白（待填）
    _font(r, 12.0, bold=False)
    # 单位：小五(9pt) 仿宋
    p = _para(doc, WD_ALIGN_PARAGRAPH.LEFT, line=LINE_PT, after=2.0)
    r = p.add_run("武汉大学 化学与分子科学学院，武汉 430072")
    _font(r, 9.0, bold=False, cn="仿宋")


def abstract_block(doc, cn_abs, cn_kw, cn_clc):
    p = _para(doc, WD_ALIGN_PARAGRAPH.JUSTIFY, line=13.5, after=0.0)
    r = p.add_run("摘要：")
    _font(r, 9.0, bold=True)
    _emit(p, cn_abs, 9.0, bold=False)
    p = _para(doc, WD_ALIGN_PARAGRAPH.JUSTIFY, line=13.5, after=0.0)
    r = p.add_run("关键词：")
    _font(r, 9.0, bold=True)
    _emit(p, cn_kw, 9.0, bold=False)
    p = _para(doc, WD_ALIGN_PARAGRAPH.LEFT, line=13.5, before=2.0, after=3.0)
    r = p.add_run("中图分类号：")
    _font(r, 9.0, bold=True)
    r = p.add_run(cn_clc)
    _font(r, 9.0, bold=False)


def en_block(doc, title, authors, affil, abstract, kw):
    p = _para(doc, WD_ALIGN_PARAGRAPH.LEFT, line=18.0, before=2.0, after=2.0)
    r = p.add_run(title)
    _font(r, 14.0, bold=True, cn=CN, en=EN_ARIAL)
    p = _para(doc, WD_ALIGN_PARAGRAPH.LEFT, line=13.0, after=0.0)
    r = p.add_run(authors)
    _font(r, 9.0, bold=False, cn=CN, en=EN_ARIAL)
    p = _para(doc, WD_ALIGN_PARAGRAPH.LEFT, line=13.0, after=3.0)
    r = p.add_run(affil)
    _font(r, 9.0, bold=False, cn=CN, en=EN_ARIAL)
    p = _para(doc, WD_ALIGN_PARAGRAPH.JUSTIFY, line=12.0, after=0.0)
    r = p.add_run("Abstract: ")
    _font(r, 9.0, bold=True, en=EN_ARIAL)
    _emit(p, abstract, 9.0, bold=False, cn=CN, en=EN_ARIAL)
    p = _para(doc, WD_ALIGN_PARAGRAPH.JUSTIFY, line=LINE_PT, after=6.0)
    r = p.add_run("Key Words: ")
    _font(r, 9.0, bold=True, en=EN_ARIAL)
    _emit(p, kw, 9.0, bold=False, cn=CN, en=EN_ARIAL)


def references(doc, items):
    p = _para(doc, WD_ALIGN_PARAGRAPH.CENTER, line=LINE_PT, before=6.0, after=2.0)
    r = p.add_run("参  考  文  献")
    _font(r, 9.0, bold=True)
    for it in items:
        p = _para(doc, WD_ALIGN_PARAGRAPH.JUSTIFY, line=12.0, before=1.0)
        p.paragraph_format.left_indent = Pt(8.5)
        p.paragraph_format.first_line_indent = Pt(-8.5)
        r = p.add_run(it)
        _font(r, REF_PT, bold=False)


def acknowledgment(doc, text):
    p = _para(doc, WD_ALIGN_PARAGRAPH.LEFT, line=LINE_PT, before=6.0, after=0.0)
    r = p.add_run("致  谢")
    _font(r, 9.0, bold=True, cn="仿宋")
    p = _para(doc, WD_ALIGN_PARAGRAPH.JUSTIFY, line=LINE_PT, indent=INDENT_PT)
    r = p.add_run(text)
    _font(r, 9.0, bold=False, cn="仿宋")

# ============================ 正文内容 ============================

TITLE_EN = ("Decision Stability of Redox Descriptors for Electrolyte Solvents: "
            "Ranking Robustness across Method, Environment and Geometry Rungs "
            "and a Minimal Information Budget")

CN_ABS = (
    "电解液溶剂的电化学稳定性窗口由溶剂的氧化/还原电位排序决定，而工程筛选普遍依赖廉价代理指标。"
    "本文不追问代理指标的绝对值，而追问更贴近决策的问题：当方法、环境与几何逐级升级时，"
    "溶剂排序是否稳定。在 18 个溶剂分子的核心集上，我们建立四个电子结构臂——GFN2-xTB 的 Koopmans "
    "量（P0）、GFN2-xTB 的 ΔSCF 量（P0′）、r2SCAN-3c 气相 ΔSCF 量（P1）与 r2SCAN-3c 加 CPCM/SMD（乙腈）的量（P2）——"
    "并与几何台阶（G1→G2）、Li+ 条件态台阶（C0→C1→C2）拼成五级物理台阶（每级在氧化、还原两轴报告，共十组指标），"
    "逐级给出 Kendall τ_b、Top-k 重叠与未解析对比例 f_unresolved。"
    "主要结果：1）值误差与排序误差解耦——GFN2-xTB ΔSCF 的绝对误差高达 4.48 eV，排序 τ_b 仍有 0.91；"
    "r2SCAN-3c 气相量把绝对误差降到 0.25 eV（约 1/18），τ_b 反而降到 0.73。2）决定排序是否被改写的是位移的离散度 std 而非幅值 |mean|："
    "跨十级台阶 ρ(std, τ_b) = −0.851，ρ(|mean|, τ_b) = −0.535，ρ(std, f_unresolved) = +0.894。"
    "3）由该规律得到闭式判据 σ_ij = |δ_i − δ_j|/√2，把分子对的可分辨性化归为无量纲条件 q_ij ≤ √2/z，"
    "可在计算前预判未解析的比例与量级（留一台阶前瞻检验 R² = 0.932），但不能在算出目标层数值前指认具体分子对。4）介电层几乎免费：位移服从 Born 形式（R² = 0.986），满足 |ΔE|·ε ≈ 2.1 eV 的幂律，"
    "ε = 200 时残余仅 19.6 meV，为氧化轴不确定度预算的 2.8%；可省的是 ε ≥ 200 的加密点，而单一连续介质计算本身不可省。5）Li+ 第一配位壳把氧化轴整体抬高 4.89 eV、"
    "并使还原轴排序反号（τ_b = −0.467），但第二壳起趋于饱和（0.38/0.54，与饱和一致）。"
    "6）针对双初猜漏解，给出无需预报的安全界：单格效应量 A_axis（配对的严格条件为 |d0| ≥ 2 A_axis，见 3.2.5 节）。靶向双腿在每轴 660 对中漏 0 次翻转，"
    "且与全双腿的 τ_b 最小值同为 1.0000。据此提出最小计算层预算：小分子集筛选时，几何台阶与 ε ≥ 200 的介电加密层可以不算。位移学习在 8 个分组中 7 个不劣于直接学习；恢复中位 τ_b ≥ 0.80 需 9–15 个昂贵标签。7）外部液相锚点的首次检验给出一个负结果：在 7 个同系列溶剂构成的 21 个分子对上 τ_b = 0.4286 < 0.9，因此本文的排序结论尚未获得独立的液相实验支持。"
    "全文结论限定在 designated computational target 内部的决策稳定性：它不构成对真实电解液体系的实验有效性声明，"
    "也不是对候选分子绝对性能的排名；把这条边界展开成的 13 条声明见 6.2 节。"
)

CN_KW = "电解液溶剂；氧化还原电位；排序稳定性；Kendall 秩相关；不确定度预算；隐式溶剂化"
CN_CLC = "O646"

EN_ABS = (
    "Electrolyte stability windows are set by the ranking of solvent redox potentials, yet practical screening relies "
    "on cheap proxies; we ask whether that ranking survives stepwise upgrades of method, environment and geometry. "
    "On a core set of 18 solvents we build four arms, P0 (GFN2-xTB Koopmans), P0\u2032 (GFN2-xTB \u0394SCF), P1 (r2SCAN-3c "
    "gas-phase \u0394SCF) and P2 (r2SCAN-3c with CPCM/SMD in acetonitrile), plus geometry and Li+ rungs (five physical rungs, both axes). Value error and ranking error are decoupled: P0\u2032 carries a 4.48 eV absolute error yet "
    "retains \u03c4_b = 0.91, whereas P1 lowers the error to 0.25 eV but shows \u03c4_b = 0.73. Ranking "
    "rewrites track the dispersion std of the shifts: \u03c1(std, \u03c4_b) = -0.851 and \u03c1(std, "
    "f_unresolved) = +0.894. This gives a closed-form criterion \u03c3_ij = |\u03b4_i - \u03b4_j|/\u221a2 and q_ij \u2264 "
    "\u221a2/z. The dielectric layer is nearly free: shifts follow a Born form (mean R\u00b2 = 0.986) with |\u0394E|\u00b7\u03b5 \u2248 "
    "2.1 eV, leaving 19.6 meV at \u03b5 = 200; only the \u03b5 \u2265 200 refinement can be omitted, not the continuum "
    "calculation. The first Li+ shell raises the oxidation axis by 4.89 eV and inverts the reduction ranking (\u03c4_b = "
    "-0.467), saturating from the second shell; reduction decisions rest on P2/C1, as gas-phase anions are unbound at "
    "P1. A prediction-free bound (|d0| \u2265 2 A_axis per pair) makes targeted reruns miss zero flips out of 660 pairs per "
    "axis. Leave-one-family-out extrapolation favours shift learning in 7 of 8 groups, and 9-15 expensive labels "
    "suffice for median \u03c4_b \u2265 0.80. The geometry rung and the \u03b5 \u2265 200 refinement need not be computed. An external "
    "solution-phase anchor test is negative (\u03c4_b = 0.4286)."
    " All conclusions are scoped to decision stability inside the designated computational target and make no claim of "
    "experimental validity for real electrolytes, nor any absolute performance ranking."
)

EN_KW = ("electrolyte solvent; redox potential; ranking stability; Kendall rank correlation; uncertainty budget; "
         "implicit solvation")

def write_intro(doc):
    h1(doc, "1  引言")
    body(doc, "锂离子电池的电解液需要在负极还原、正极氧化的电位窗口内保持电化学惰性，"
              "因此溶剂的氧化电位与还原电位直接决定了电解液可用窗口的宽度。"
              "实验上逐个测定溶剂分子的气相或液相氧化还原电位代价高，且结果受电极界面与浓度影响，"
              "难以先于合成覆盖可用的化学空间，这就使虚拟筛选成为电解液配方开发中的常规环节[4]。"
              "工程实践中筛选普遍依赖廉价代理指标：以 HOMO/LUMO 能级的负值近似电离能（IP）与电子亲和能（EA）"
              "（即 Koopmans 图像），或以半经验紧束缚方法、经验规则乃至机器学习模型给出稳定性排序[8,11]。")
    body(doc, "对这一做法已有大量方法学讨论。Peljo 与 Girault 指出，用轨道能级之差定义稳定窗口"
              "与真实氧化还原电位可偏离数 eV，应当使用电位本身而非能级差[5]；"
              "Marenich 等系统评述了由自由能差换算液相电位的热力学循环与隐式溶剂协议[3]；"
              "Itkis 等表明团簇—连续介质模型给出的 Li+ 溶剂化自由能存在明显的模型歧义[6]；"
              "Borodin[1] 以及 Cheng 等[13]的综述则指出，键合到 Li+ 上的阴离子与溶剂数目会改变电解液的还原与氧化稳定性，"
              "即溶剂分子并非孤立存在。这些工作共同说明：廉价代理的绝对值并不可靠。")
    body(doc, "然而筛选任务的输出并不是数值，而是排序。一个绝对误差达到 1 eV 的代理，"
              "完全可能在若干候选中给出与高精度方法一致的次序；反之，一个绝对误差只有 0.25 eV 的方法，"
              "也可能因为误差在分子间分布不均而改写排序。因此，评价一个代理指标能否用于筛选，"
              "需要看排序误差而不是数值误差。本文把两者明确分离，并把"
              "**排序在逐级升级计算条件时是否保持**定义为决策稳定性。")
    body(doc, "要在真实体系中度量决策稳定性，最大的障碍是变量混杂：把一个体系从半经验升级到色散校正泛函，"
              "同时改变基组、几何、溶剂化与显式配位环境，就无法判断排序变化由哪一项引起。"
              "本文的做法是把升级路径拆成互不重叠的台阶，每一级只允许一个变量改变，"
              "从而把方法误差、环境误差与几何误差分离开来，并逐级给出排序统计量。"
              "此外，我们把每一级的位移看作一个随机场：若位移是分子的共同平移，排序不变；"
              "只有当位移在不同分子间**离散**时，排序才会被改写。这一图景最终给出一条可在计算前使用的闭式判据。")
    body(doc, "本文的组织如下：第 2 节给出分子集、三层电子结构臂与台阶设计、决策量、不确定度预算与特征成本分级的定义；"
              "第 3 节按台阶逐级报告结果，并给出位移离散度判据、介电层标度、两条求解路径的漏解靶向策略、"
              "Li+ 配位饱和的证据，以及留一家族出外推下的直接学习与位移学习对比和恢复排序所需的最小昂贵标签预算；"
              "第 4 节归纳最小计算层预算，第 5 节把全文结论对照预注册方案作分支认领、判据自查与创新边界声明。")

def write_methods(doc):
    h1(doc, "2  计算方法与决策量定义")
    h2(doc, "2.1  分子集与化学空间")
    body(doc, "核心集包含 18 个溶剂分子（记为 C01–C18），覆盖 8 个结构家族：链状碳酸酯 3 个"
              "（DMC、EMC、DEC）、环状碳酸酯 4 个（EC、PC、FEC、VC）、醚 3 个（DME、DOL、TEGDME）、"
              "酯 3 个（GBL、EA、MA）、砜 1 个（SL）、亚砜 1 个（DMSO）、腈 2 个（AN、SN）与磷酸酯 1 个（TMP）。"
              "扩展池另含 40 个分子，把家族扩展到亚硫酸酯、磺内酯与硅氧烷，用于检查结论是否依赖于核心集的选取（其敏感性分析与预算演示见 3.6.2 节）。"
              "全部分子的标签、家族与供体数取自受控词表（见 2.6 节的可审计性说明）。"
              "核心方案要求 chemical-space metadata 为多轴而非单一 family：除 data/metadata/core_set.csv 的 14 列外，"
              "我们把 formal_charge、conformer_count、Li_motif_count、state_identity_status、reactivity_status 与 qc_status 六项"
              "从各台阶产物逐行抽出，汇成 data/metadata/core_set_metadata_ext.csv（逐字段来源与覆盖率见表注与该文件的 source_refs 列）。"
              "凡在仓库内找不到可靠来源者一律记为 not_available_in_repo，不做任何推算；这些字段只描述计算与状态身份，不是物理可观测量。")
    figure(doc, "F0_project_pipeline.png",
           "图 1  项目五段式流水线：廉价代理（P0）→ 经验证目标（P1）→ 环境目标（P2）→ 条件态物种（C1）→ 决策稳定性（Top-k / 稳健翻转）", 6.3)
    body(doc, "为把方法层级、条件态层级与外部参考层的关系一次说清，图 2 把它们画成一张二维层级图："
              "纵轴是方法层级（P0 → P1 → P2），横轴是条件态层级（C0 → C1 → C2），"
              "外部参考层（R_gas / R_sol / R_env）不参与计算层级、单列在右侧。"
              "图中标出本项目实际计算过的格点（实心）与未计算的留白格，避免把“可定义”误读成“已计算”。")
    figure(doc, "F54_two_axis_hierarchy.png",
           "图 2  方法层级 × 条件态层级与外部参考层：纵轴为方法层级（P0 → P1 → P2），横轴为条件态层级（C0 → C1 → C2），右侧单列外部参考层（R_gas / R_sol / R_env）；实心格为本项目实际计算过的组合，留白格为未计算。", 5.5)
    figure(doc, "F1_chemical_space_coverage.png",
           "图 3  core 集与 broad 池的化学空间覆盖：左为各结构家族的分子数对比，右为供体原子数分布", 6.3)
    h2(doc, "2.2  三层电子结构臂与唯一变量台阶设计")
    body(doc, "我们建立三层电子结构臂（P0、P1、P2；另设一个 GFN2-xTB ΔSCF 对照臂 P0′ 用于 3.1.1 节的方法审计），每层给出同一批分子的 IP 与 EA：P0 为 GFN2-xTB 6.7.1pre 在气相给出的"
              "Koopmans 量（p_ox = −ε_HOMO，p_red = +ε_LUMO）；P1 为 ORCA 6.1.1 在 r2SCAN-3c 水平、气相下用"
              "ΔSCF 三点法（中性、阳离子、阴离子）给出的垂直量；P2 在 P1 基础上加入 CPCM 隐式溶剂模型并以"
              "SMD 参数化（乙腈，ε = 35.688）。三层的唯一差异被严格控制：P0→P1 只改变电子结构方法，"
              "P1→P2 只改变环境。")
    body(doc, "在此基础上，我们把所有升级路径统一成五级物理台阶（P0→P1、P1→P2、G1→G2、C0→C1、C1→C2），每级只允许一个变量改变；每一级都分别在氧化轴与还原轴上统计，全文共十组台阶—轴指标（表 3）："
              "P0→P1（方法）、P1→P2（环境）、G1→G2（几何，把 GFN2-xTB 优化几何换成 r2SCAN-3c 的 Opt+Freq 驻点，"
              "12 分子审计子集）、C0→C1（自由分子 → 1:1 Li+ 配位条件态 [LiM]+，10 分子）、"
              "C1→C2（[LiM]+ → 1:2 微溶剂化簇 [Li(M)2]+，10 分子）。"
              "每一级同时报告氧化轴与还原轴的位移均值、位移标准差、Kendall 秩相关 τ_b、Top-k 清单重叠与未解析对比例。"
              "需要强调，C0→C1 与 C1→C2 是**条件态**的比较（M 与 [LiM]+ 是两个不同的化学物种），"
              "而不是同一可观测量在两个精度下的比较，因此其 τ_b 只用于说明配位如何改写排序，不能解释为精度改善。")
    body(doc, "术语约定：本文把这条阶梯上的每一级统称为 designated computational target（指定计算目标）——它由计算定义冻结，"
              "逐级升级只改变被指定的物理内容，并不使任何一级自动获得额外的有效性；把用于外部核对的序列统称为 "
              "designated reference model（指定参考模型）——它给出外部参考条件与条件匹配的对照，其自身的有效性需另行独立复核。"
              "全文按这两个术语书写，不使用任何“已验证目标”式的表述。")

    h2(doc, "2.3  电子结构计算细节")
    body(doc, "GFN2-xTB 计算使用 xtb 6.7.1pre，几何在同一水平下优化并作为 G1 几何供全部层级共享；"
              "ORCA 计算使用 r2SCAN-3c 复合方法，其中 r2SCAN 为 meta-GGA 泛函，配合 def2-mTZVPP 基组与"
              "D4 色散校正与 gCP 几何 counterpoise（BSSE）校正[10]，并启用 RIJCOSX 加速。上述各级计算分别由 ORCA 6.1.1[14,15]、GFN2-xTB[9]、r2SCAN-3c[16]（基于 r2SCAN 泛函[17]）、SMD[12] 与 CPCM[18] 实现。低能构象空间由 RDKit ETKDGv3 嵌入（每分子 24 个初始构象、种子固定）加 MMFF 预优化、再经 GFN2-xTB 弛豫得到的构象系综给出；CREST[7] 一类的 metadynamics 搜索未在本工作中使用，该引用只作方法学对照。所有 ΔSCF 结果均取自三态单点计算，"
              "自洽场收敛与会话级检查由 ORCA 的输出文件直接读取；气相阴离子不束缚的情形以带负电荷态的"
              "正 HOMO 能量判据标记，核心集在 P1 下有 18/18 个阴离子不束缚，说明 P1 的气相 EA 只是有限基组下的伪束缚量、只在趋势上有意义，"
              "其数值不能当作物理 EA 引用；据此本文规定：还原轴的决策结论只以 P2/C1 为载体，P0→P1 的还原轴对比仅作完备性展示（见 3.2.1 节）。")
    body(doc, "为检查基组对 EA 的影响，我们做了同泛函三基组对照（含弥散函数）：加弥散会把气相 EA "
              "系统性下拉 0.34–1.60 eV（4 个分子 × 3 组基组，共 24 个作业），但没有一个分子发生符号翻转，"
              "说明弥散主要改变的是 EA 的绝对标度而不是稳定性次序。")
    body(doc, "配位台阶一律使用同配体、同化学计量的相对量（配体交换能差 ΔΔG_bind），以避开 "
              "Li+ + M → [LiM]+ 这一缔合步骤的平动熵与缔合熵假象[8]；本文不对缩合相缔合熵做显式建模，"
              "该引用只作方法学依据。")
    h2(doc, "2.4  决策量定义")
    body(doc, "为把氧化与还原放进同一套单调框架，定义两个决策量：氧化轴 p_ox = (E_cation − E_neutral)，"
              "还原轴 p_red = −(E_anion − E_neutral)（即 −EA）。两者都是越大越稳定，即越大越有利于拓宽稳定窗口。"
              "排序统计量用 Kendall τ_b 度量升级前后同一批分子次序的一致性（τ_b = +1 表示次序完全保持，"
              "−1 表示完全反转）；用 Top-k 清单重叠（k 取分子数的 10%、20%、30%，并对应固定的绝对 k）"
              "度量筛选清单是否变化；用 f_unresolved 度量“在当前不确定度下无法分辨先后”的分子对比例；"
              "用 f_robust_inv 度量在双方都可分辨时仍发生反转的对比例。本文把 τ_b 与 f_unresolved 并列报告，"
              "因为单独看 τ_b 会把“靠得很近、其实尚未分辨”的稳定误读为真稳定。"
              "需要明确边界：p_ox 与 p_red 只是**完整物种**的一电子热力学 proxy，既不含分解反应网络与动力学，"
              "也不含电极界面与 EDL 效应，因此本文不声称给出完整的电化学稳定窗口；全文的“决策”始终指候选分子的稳定性次序。")
    h2(doc, "2.5  不确定度预算与 σ 的闭式")
    body(doc, "每一级台阶的判据都需要一个容差。本文把容差固化为不确定度预算 δ_m，"
              "其合成规则为：δ_m = max(构象系综的 90 分位展宽, 跨方法位移的离散度, 0.05 eV 下限)。"
              "据此在 P1 层得到氧化轴 δ_m = 0.700245 eV、还原轴 δ_m = 2.074299 eV，两者都以方法项为主导。为界定被略去的 0 K 电子能近似，另取 8 个代表分子（覆盖 7 个家族）在 GFN2-xTB 级做热修正抽样：ΔG 型热修正的离散度为氧化 0.058 eV、还原 0.078 eV，最大绝对量 0.26 / 0.32 eV，均低于对应 δ_m，故热修正不改变任何稳健判定（带电态 Hessian 取在中性 G1 几何上，含 2 个虚频，该值只作量级上界）。"
              "分子对层面的不确定度由位移差给出：若分子 i 与 j 的位移分别为 δ_i 与 δ_j，"
              "则 σ_ij = |δ_i − δ_j|/√2，该式在第 3.4.1 节由代数与数值双重验证。")
    h2(doc, "2.6  预注册与可审计性")
    body(doc, "为避免事后挑选，判据、容差与阈值在计算前写入配置并冻结（预注册配置与科学定义配置两个"
              "配置文件标记为 frozen），任何修改都需要登记修正记录。全部数值结果由脚本从 ORCA 输出与中间产物"
              "自动渲染，并可用 --check 逐字节复核；文档与图表均可追溯到具体的产物路径。"
              "本文涉及的并行化设置、初猜策略与收敛判据同样随产物落盘，以保证结论可复现。外部标定分两级：气相 IP 锚点（12 分子）用于第 3.1.1 节的绝对值与排序核对；液相锚点登记了一个预注册的 within-series 排序一致性判据（要求 ≥ 18 个同系列分子对且 τ_b ≥ 0.9）。预注册阶段该判据没有合格数据（n_pairs = 0）；随后的可行性审计把 ≥ 18 对还原为“同源序列至少覆盖 7 个核心集分子”，再逐篇核查本地 13 篇文献；结果 18 个核心集分子中有 17 个曾在文献里被提到，但只有 4 个能取到可引数值、且分属 3 个不同上游来源，最长的同源序列只覆盖 1 个核心集分子（0 对）。因此缺口是一份在同一装置或同一判据下覆盖 ≥ 7 个核心集溶剂的电位表，而不是再多几个单点值。本文完成前，一份据称满足该条件的外部氧化锚点表被引入，该判据因此第一次可以评估：n_pairs = 21 达标，而 τ_b = 0.4286 < 0.9，判决为排序不一致（见 3.1.2 节）。该批数据的性质必须与数字同句声明：它是外部提供的转录值，两条上游原著都不在本地文献库、本环境亦无网络，故入库行标记为 transcription_only，仓库没有对任何一行做过独立复核；0.1 V 是引入说明所报的系列重复性，不是来源给出的不确定度。该系列的上游归属需要写明：数据主源是 Ue 等人在 Okoshi et al. 2015 的参考文献 1–2 中报告的 LSV 实测值（vs SCE，同装置同判据）；Okoshi et al. 2015（ECS Electrochem. Lett. 4(9) A103）本身是一篇理论计算论文，但其 Fig. 1 转录的正是这组实验值，并按其式(2) 换算至 Li⁺/Li 标度。因此本批数字的正确引用格式是“Ue 等实测，经 Okoshi et al. 2015 Fig. 1 转录并按其式(2) 换算至 Li⁺/Li 标度”。据此，Gate 1 的现状是：排序层判据已评估但未闭合，绝对标定层仍未封闭。")

    h2(doc, "2.7  特征成本分级与机器学习协议")
    body(doc, "为避免用“接近目标层成本”的特征去证明“低成本预测”，我们把全部特征按可得时机分成三档，"
              "并要求所有机器学习表格都标注特征成本档。X0 档在提交任何昂贵计算之前即可获得；"
              "X1 档需要自由分子 DFT 已知后才可得；X2 档必须做完 Li 配合物 DFT 才能得到，"
              "因此只作机制解释、绝不进入任何特征集——这是硬性纪律而非经验选择，"
              "否则等于先花掉昂贵计算、再声称可以省掉它。")
    table_3line(doc,
                ["成本档", "特征", "何时可得", "允许用途"],
                [["X0（12 项）",
                  "分子量、重原子数、供体原子数、可旋转键数、TPSA、成环、含氟；p0_ox、p0_red、HOMO–LUMO 间隙、偶极、极化率",
                  "提交昂贵计算之前", "可作预测特征与主动学习采集依据"],
                 ["X1（6 项）",
                  "p1_ox、p1_red、p2_ox、p2_red、env_Δox、env_Δred",
                  "自由分子 DFT 已知之后", "可预测条件态响应；不得据此宣称无需 C1"],
                 ["X2（4 项）",
                  "ΔΔG_bind、Li–X 最短距离、Li 接触数、motif 是否切换",
                  "Li 配合物 DFT 之后", "仅机制解释；严禁进入特征集"]],
                "表 1  特征成本分级（X0 / X1 / X2）与允许用途（取自 outputs/week7/feature_manifest.json 的 feature_cost_levels 与 x2_policy）",
                "Table 1  Feature cost levels")
    body(doc, "预测协议如下：三种数据划分——随机（random，插值上界）、按家族分组（group）与留一家族出（LOFO，外推）；"
              "模型沿复杂度阶梯 constant → ridge → KRR → GPR → RF → GBDT；两种学习形状——直接学习（direct）"
              "与位移学习（shift，即 Δ-learning：先学参考层到目标层的位移 Δ，再加回参考层）。"
              "所有标准化、超参数选择与特征筛选均在每折的训练数据内部完成。"
              "除 MAE 与 R² 外一律并报决策量（τ_b、Top-k 重叠、Jaccard 与 selection regret）。"
              "需要提醒的是 n/p 结构：X0 只有 12 个特征而核心集 N = 18（条件态 N = 10），"
              "这一比例正是必须以 LOFO 外推为主、而不能只报随机划分 R² 的原因。")

def _r_01(doc):
    h3(doc, "3.1.1  值误差与排序误差的解耦")
    body(doc, "表 2 给出三层臂对 12 个气相锚点的误差与排序一致性（锚点优先取实验测定值）。"
              "P0 的平均绝对误差（MAE）为 1.3774 eV，最大误差 2.0023 eV，但它给出的排序 τ_b 仍有 0.6061；"
              "P1 把 MAE 压到 0.251 eV（误差降低约 5.5 倍），τ_b 反而只有 0.727；"
              "GFN2-xTB 的 ΔSCF 量在绝对标度上最差（MAE 4.4811 eV），排序却最好（τ_b 0.9111）。"
              "这一组反直觉的组合说明：绝对精度与排序保真度在本体系里是两个近似独立的量，"
              "用 MAE 评价代理指标的可用性会得到误导性的结论。")
    body(doc, "由于 12 个锚点上的 τ_b 本身噪声不小，我们对 P0′ 与 P1 的 Δτ_b 做配对 bootstrap（对分子有放回重抽 2×10⁴ 次）：两臂点估计 0.911 与 0.727，Δτ_b = 0.184，95% 区间 [−0.177, 0.607]，P(Δτ_b > 0) = 0.839；"
              "把两臂匹配到同一 10 分子集后 Δτ_b = 0.133，区间 [−0.195, 0.550]。也就是说，“误差小约 18 倍、排序反而更差”这一解耦方向是稳定的（约 84% 的重抽同向），"
              "但以 12 个锚点在 95% 水平上尚不能把该差值证成非零，故本文把它作为方向性证据而非显著差。")
    table_3line(doc,
                ["层", "方法", "MAE/eV", "偏置/eV", "最大误差/eV", "τ_b"],
                [["P0", "GFN2-xTB Koopmans", "1.377", "+1.279", "2.002", "0.606"],
                 ["P0′", "GFN2-xTB ΔSCF", "4.481", "—", "—", "0.911"],
                 ["P1", "r2SCAN-3c 气相 ΔSCF", "0.251", "—", "—", "0.727"]],
                "表 2  三层电子结构臂对 12 个气相锚点的绝对误差与排序一致性（N = 12；τ_b 在 N = 10 子集上的抽样标准差约 0.126，故小于约 0.13 的 τ_b 差异不宜单独解读）",
                "Table 1  Absolute errors and ranking consistency of the three arms against 12 gas-phase anchors")
    figure(doc, "F3_value_error_vs_rank_error.png",
           "图 4  值误差与排序误差的分离：各层的绝对误差（横轴）与排序一致性（纵轴）", 6.2)


def _r_02(doc):
    h3(doc, "3.2.1  方法台阶：P0→P1")
    body(doc, "把整批分子从 P0 升级到 P1，氧化轴位移均值为 −1.5496 eV、标准差 0.7352 eV，"
              "排序统计量 τ_b = 0.673（Top-20% 重叠 0.500）；还原轴位移均值 +7.5919 eV、标准差 2.2088 eV，"
              "τ_b = 0.595。氧化轴的位移主要是一个共同平移，所以尽管数值被大幅修正，次序大体保留；"
              "还原轴则相反：位移均值很大、离散度也很大，未解析对比例升到 0.621。"
              "图 5(a) 把每个分子的 IP 在三层臂上对照，可以看到 P0 与 P1 在整体抬升的同时，"
              "分子之间的间距被重新洗牌。")
    body(doc, "还原轴还有一个定性上更重要的问题。Koopmans 图像把 EA 等同于 −ε_LUMO，"
              "但 P1 的 18 个分子气相阴离子全部不束缚，说明 P1 的垂直 EA 是有限基组下的伪束缚量，所加电子并不真正处于束缚态，"
              "此时轨道能级描述的已经不是同一个物理量。图 5(b) 显示的位次迁移因此不能只当作数值误差看待，"
              "而是模型适用域的问题——这也解释了为什么还原轴的 τ_b 在方法台阶上不算最低，"
              "却在条件态台阶上直接反号（见 3.3.1 节）。由此本文明确规定：还原轴的决策结论只以 P2/C1 为载体，P0→P1 的还原轴对比仅作完备性展示。图 4 中 GFN2-xTB ΔSCF 垂直 EA 那个看似完美的点（MAE 2.92 eV、τ_b = 1.000）只由 2 个气相锚点支撑，属于伪束缚下的伪相关，不能单独作为可分辨性证据。")
    figure(doc, "F4_rank_migration_p0_to_p1.png",
           "图 5  氧化轴 P0→P1 的位次迁移：(a) 逐分子 IP 的三臂对照（平移）；(b) 位次迁移（重排）", 6.3)
    figure(doc, "F5_reduction_axis_koopmans_vs_dscf.png",
           "图 6  还原轴的定性失效：(a) Koopmans EA 与真实 EA 的关系；(b) 还原轴位次迁移", 6.3)


def _r_03(doc):
    h3(doc, "3.2.2  环境台阶：P1→P2")
    body(doc, "在 P1 上加入隐式溶剂（SMD 乙腈）构成 P2，氧化轴位移均值 −2.3934 eV、标准差 0.3018 eV，"
              "τ_b 升到 0.895（Top-20% 重叠 0.750）；还原轴位移均值 −2.1731 eV、标准差 0.3205 eV，τ_b = 0.673。"
              "与 3.2.1 节相比，环境台阶的位移均值也很大，但离散度只有方法台阶的一半到三分之一，"
              "因此排序几乎不动。这一对照第一次把“幅值大但排序稳”与“幅值大且排序乱”区分开来："
              "决定排序的是位移的**离散度**。")
    body(doc, "把环境位移拆成介电项与畸变项可以看到它的结构：氧化轴位移 −2.4489 eV 由介电项 −2.5328 eV "
              "与畸变项 +0.0839 eV 组成，畸变抵消介电的比例为 0.031；还原轴 +2.2065 eV 由 +2.5632 eV 与 −0.3567 eV 组成，"
              "抵消比例 0.124。即溶剂化的净效应几乎完全由介电屏蔽贡献，几何畸变只是一个小修正，"
              "这为 3.2.4 节“介电层几乎免费”的判断提供了物理依据（并见该节对“可省的只是 ε ≥ 200 加密点”的限定）。")
    figure(doc, "F8_environment_layer_p1_to_p2.png",
           "图 7  环境层位移：(a) 逐分子气相→溶剂的位移（IP 与 EA）；(b) 逐对间距与不确定带", 6.3)
    figure(doc, "F10_cpcm_eps_scan.png",
           "图 8  裸 CPCM 介电常数扫描：ΔIP/ΔEA 的快速衰减曲线与 σ_env、τ_b 的变化", 6.3)


def _r_04(doc):
    h3(doc, "3.2.3  几何台阶：G1→G2")
    body(doc, "把 GFN2-xTB 几何换成 r2SCAN-3c 的 Opt+Freq 驻点（12 分子审计子集），"
              "氧化轴位移均值仅 −0.0023 eV、标准差 0.0516 eV，τ_b = 0.939、Top-10% 与 Top-20% 重叠均为 1.000；"
              "还原轴位移均值 −0.1178 eV、标准差 0.0798 eV，τ_b = 0.848。"
              "几何台阶是十级台阶里位移最小的两级之一，其排序影响也最小。"
              "一个实用含义是：在小分子集筛选中，用半经验优化几何替代色散校正泛函的重优化，"
              "不会改变稳定性排序。")


def _r_05(doc):
    h3(doc, "3.3.1  条件态台阶：Li+ 配位如何改写排序")
    body(doc, "真实电解液中溶剂分子被 Li+ 配位。自由分子 M 与 1:1 配位态 [LiM]+ 的比较给出位移均值"
              "氧化 +4.8872 eV、标准差 0.5946 eV，τ_b = 0.689；还原轴位移均值 −6.5782 eV、标准差 0.8323 eV，"
              "τ_b = −0.4667，即**次序反号**，未解析对比例高达 0.800。"
              "反号的原因由态身份分析给出：在 11/12 个体系里，还原时电子落在 Li+ 上而不是溶剂分子上，"
              "还原轴所描述的物理量已经改变。这与 Yang 等在计算与机器学习上观察到的“Li+ 配位抬高电位、且对氧化与还原电位的影响方向相反”一致[2]。")
    body(doc, "继续增加配位（C1→C2，1:1 → 1:2），氧化轴位移均值 −1.6999 eV、标准差 0.2594 eV、τ_b = 0.867，"
              "还原轴 +1.1986 eV、标准差 0.3350 eV、τ_b = 0.289。"
              "氧化轴在两步配位中都保持较高的次序一致性，说明“第一壳配位抬高氧化稳定性”这一效应"
              "在所有分子上大致同向；还原轴则在两步中都失去次序。"
              "需要再次强调，这两步是条件态之间的比较，τ_b 的低值说明的是配位改写了化学，"
              "而不是某个方法的精度不够。")
    body(doc, "这一节还有一条定义域层次的边界必须写明：C1 的还原态身份一旦按 Li-centered 与 molecule-centered 分层统计，"
              "主排序样本就塌到 n = 1——还原轴在 C1 条件下已经无定义。这不是误差变大，而是被测量的对象变了："
              "[LiM]+ 的还原中心是 Li 而不是溶剂分子。本文据此规定还原轴的决策结论只以 P2/C1 为载体，"
              "任何建立在 C1 还原轴上的排序数字都不作独立证据使用。")

    figure(doc, "F12_li_coordination_c1.png",
           "图 9  Li+ 配位条件态 C1：逐分子 dIP/dEA、台阶 σ 对比、配体交换与决策量", 6.3)


def _r_06(doc):
    h3(doc, "3.4.1  位移离散度判据与 σ 的闭式")
    body(doc, "表 3 汇总了十级台阶的位移与决策量。把十级台阶放在一起看，两个相关系数给出了本节的核心结论："
              "位移离散度与排序一致性显著负相关，ρ(std, τ_b) = −0.8511；而位移幅值与排序一致性只有弱相关，"
              "ρ(|mean|, τ_b) = −0.5350；位移离散度与未解析对比例高度正相关，ρ(std, f_unresolved) = +0.8936。"
              "换言之，**决定排序是否被改写的是位移的离散度，不是位移的大小**。用 bootstrap 给出这些相关的不确定度（2×10⁴ 次重抽）：ρ(std, τ_b) = −0.851 [−0.987, −0.424]，ρ(std, f_unresolved) = +0.894 [+0.440, 1.000]，而 ρ(|mean|, τ_b) = −0.535 的区间 [−0.961, 0.245] 跨越 0——即“幅值不重要”这一侧在 n = 10 下并未被数据证成，只能说它明显弱于离散度。剔除态身份改变的 C0→C1 还原轴后 ρ(std, τ_b) = −0.829（9 点），再剔除两条条件态台阶后为 −0.943（6 点），方向与量级都不变，说明主结论不由该异常点支撑。需要声明：10 个台阶点并不独立（同一台阶两轴共享分子、相邻台阶复用分子），上述区间只作样本内稳定性检查，不作总体推断。")
    table_3line(doc,
                ["台阶", "唯一变量", "轴", "位移均值/eV", "位移 std/eV", "τ_b", "f_unresolved"],
                [["P0→P1", "方法", "氧化", "−1.550", "0.735", "0.673", "0.157"],
                 ["P0→P1", "方法", "还原", "+7.592", "2.209", "0.595", "0.621"],
                 ["P1→P2", "环境", "氧化", "−2.393", "0.302", "0.895", "0.111"],
                 ["P1→P2", "环境", "还原", "−2.173", "0.321", "0.673", "0.222"],
                 ["G1→G2", "几何", "氧化", "−0.002", "0.052", "0.939", "0.030"],
                 ["G1→G2", "几何", "还原", "−0.118", "0.080", "0.848", "0.061"],
                 ["C0→C1", "条件态", "氧化", "+4.887", "0.595", "0.689", "0.200"],
                 ["C0→C1", "条件态", "还原", "−6.578", "0.832", "−0.467", "0.800"],
                 ["C1→C2", "第二壳", "氧化", "−1.700", "0.259", "0.867", "0.089"],
                 ["C1→C2", "第二壳", "还原", "+1.199", "0.335", "0.289", "0.356"]],
                "表 3  十级台阶的位移与决策稳定性指标（唯一变量逐级隔离；位移与 τ_b 为各台阶原生 N：P0→P1 氧化 N = 18，条件态 N = 10；图 10 使用 common-10 子集，同台阶 τ_b 略有差异，如 P0→P1 还原 0.595（N = 18）对 0.600（N = 10））",
                "Table 2  Shifts and decision-stability metrics of the ten-rung ladder")
    table_3line(doc,
                ["台阶", "轴", "τ_b", "f_unres(z=1)", "f_robust_inv(z=1)", "f_robust_inv(z=1.96)", "J_10%", "J_20%", "J_30%"],
                [["P0→P1", "氧化", "0.733", "0.133", "0.000", "0.000", "0.0", "0.0", "0.5"],
                 ["P0→P1", "还原", "0.600", "0.733", "0.000", "0.000", "0.0", "1.0", "0.5"],
                 ["P1→P2", "氧化", "0.911", "0.111", "0.000", "0.000", "1.0", "1.0", "0.5"],
                 ["P1→P2", "还原", "0.778", "0.200", "0.000", "0.000", "0.0", "1.0", "0.5"],
                 ["G1→G2", "氧化", "0.956", "0.022", "0.000", "0.000", "1.0", "1.0", "1.0"],
                 ["G1→G2", "还原", "0.867", "0.067", "0.000", "0.000", "1.0", "1.0", "0.5"],
                 ["C0→C1", "氧化", "0.689", "0.200", "0.000", "0.000", "1.0", "1.0", "0.5"],
                 ["C0→C1", "还原", "−0.467", "0.800", "0.000", "0.000", "0.0", "0.0", "0.2"],
                 ["C1→C2", "氧化", "0.867", "0.089", "0.000", "0.000", "1.0", "1.0", "1.0"],
                 ["C1→C2", "还原", "0.289", "0.356", "0.000", "0.000", "0.0", "0.0", "0.5"]],
                "表 4  十级台阶的稳健翻转比例与 Top-k Jaccard（common-10 子集，N = 10、45 对；J_10/J_30 由同一冻结逐分子值按 k = 1/2/3 重算，原生只存 J_20）",
                "Table 4  Robust-inversion fraction and Top-k Jaccard")
    body(doc, "表 4 补上了此前只定义、未报告的三个量。稳健翻转比例 f_robust_inv 在五个台阶 × 两条轴 × 两种分子池、"
              "z = 1 与 z = 1.96 两档合计 40 个数中**全部为 0**：本文没有在任何一级台阶上抓到超出方法不确定度的排序翻转。"
              "这与闭式判据自洽——σ_ij 要么大到让分子对直接落入 unresolved，要么小到不足以翻转次序，"
              "中间那段“已分辨却仍翻转”的窗口在本文数据里是空的。")
    body(doc, "这条零值必须连同它的定义一起读，否则会被读成经验发现。本文的稳健翻转判据完整定义为：以两支冻结估计臂逐对求 "
              "σ_ij = |ΔP_A(i, j) − ΔP_B(i, j)| / √2——分母 √2 来自两支臂的逐分子不确定度按等权合成，"
              "逐分子样本标准差取 ddof = 1；分子对 (i, j) 被判为解析，当且仅当 |ΔP_ij| ≥ z·σ_ij 且 |ΔP_ij| > 0；"
              "稳健翻转（robust inversion）要求两侧同时解析且位移符号相反。因此 f_robust_inv 的分母不是全部分子对，"
              "而是“两侧都解析”的子集 N_resolved_both：在本文 8 个冻结块（4 级台阶 × 2 轴）上，z = 1 时它为 "
              "83、44、125、94、84、40（对／153 对）与 30、4（对／45 对），z = 1.96 时进一步缩到 61、33、102、67、60、32 与 24、4。"
              "分母随判据收紧而缩小这一点，必须与零值同时报告。")
    body(doc, "两个定理界定了这个零值的位置。定理 T6a（反转不可能）：在等权双支臂判据下，稳健反转只在 z ≤ 1/√2 时才有可能，"
              "而本文冻结的两档 z（1.0 与 1.96）都大于该阈值（z* = 0.7071067811865475）。因此 f_robust_inv ≡ 0 是一个**定义性**结果，"
              "是闭式判据的代数推论，而不是关于本体系的经验发现。定理 T6b（不可认证的分歧）：在每一个冻结块、每一档 z 上，"
              "双方解析子集内的反向分子对数都是 0（max_n_discordant_both = 0）——这条两支臂流程从不认证任何分歧。"
              "把 f_robust_inv = 0 读成“本体系没有排序反转”，是把定义性结果误读为经验结论；本文的实际结论要弱得多、也稳得多："
              "现有双支臂证据**不能识别**排序是否反转。两条定理的完整表述、逐块计数与验证见补充材料 S2。")

    body(doc, "概率化逐对排序 p_ij = P(P_i > P_j) 给出同一结论的更细视角。按 §9.4 的 p_ij > 0.9 判 i > j、p_ij < 0.1 判 i < j、"
              "其间判 unresolved，其等价 z = Φ⁻¹(0.9) = 1.282；在该口径下 p_ij 导出的 unresolved 比例与闭式 f_unresolved "
              "逐点相等（偏差小于 10⁻¹⁵）。最值得注意的仍是 C0→C1 还原轴：45 对中 33 对发生符号翻转，"
              "而这 33 对**全部**落在 unresolved 区内（p 导出的 unresolved 比例为 0.822）。"
              "也就是说这条轴的换序不是“分辨清楚之后仍然翻转”，而是“根本还没分辨”——这正是分支 G 所描述的情形。"
              "口径必须同时声明：若改用逐分子方差和 σ_ij² = (δ_i² + δ_j²)/2 的定义，同一台阶的 unresolved 比例会升到 0.95–1.00；"
              "本文一律采用 σ_ij = |δ_i − δ_j|/√2。")
    body(doc, "这一图景可以写成闭式。若两个分子的位移分别为 δ_i 与 δ_j，则它们在决策量上的差异不确定度为 "
              "σ_ij = |δ_i − δ_j|/√2。我们对该式做了四项检验：逐对值与逐步重算的最大偏差为 1.1×10⁻¹⁵ eV；"
              "逐对值的方均根恰好等于逐分子样本标准差（最大相对误差 2.7×10⁻¹⁶）；"
              "对全体位移叠加任意刚性偏移后 σ 与 τ_b、f_unresolved 完全不变（最大变化 0.0）；"
              "以及未解析对比例可由 f_unresolved(z) = Pr(q_ij > √2/z) 精确给出。"
              "其中 q_ij 是位移相对目标轴的割线斜率。该判据把“两个分子能否被分辨”化归为一个无量纲条件 "
              "q_ij ≤ √2/z：z = 1 时阈值 1.4142，z = 1.96 时阈值 0.7215。")
    body(doc, "闭式判据也解释了两个此前的反例。P0→P1 还原轴的位移散布是全部台阶中最大的（std = 2.25 eV），"
              "但位移几乎平行于目标轴，所以分辨率下降而排序基本保住（τ_b = 0.600）；"
              "C1→C2 还原轴的 std 只有 0.335 eV，却因为该级的还原中心是 Li 而非溶剂分子（态身份改变），"
              "排序被改写（τ_b = 0.289）——纯离散度模型按定义看不见态身份的改变，这是判据的适用边界。"
              "最后，考虑到核心集只有 18 个分子，我们做了子抽样稳定性检查：在 N = 10 的子集上重抽 2000 次，"
              "τ_b 的抽样标准差为 0.1264，说明十级台阶之间的 τ_b 差异必须大于约 0.13 才有意义。")
    body(doc, "闭式判据能否用于**事前预判**，我们按预注册流程做了一次样本外检验：预警规则在 Week 10 冻结、留出分子集在 Week 13 指定，"
              "两者都没有参与阈值选择，预测文件在任何结果被计算前先落盘并取 SHA256（见产物清单）。"
              "留出集上带符号规则命中 3/4，朴素规则 2/4；两次落空都发生在还原轴（位移几乎平行于目标轴、或态身份改变的情形），"
              "与判据的适用边界一致。这说明闭式判据可用于“先算哪些对、先花哪笔钱”的排序，但它不是万能分类器；"
              "第 3.4.1 节末尾的敏感性也表明，判据的证据目前主要是解剖式的（代数恒等 + 同数据回代），其前瞻性只在这一次留出检验上被初步支持。")
    body(doc, "为把这条证据再推一步，我们补做了一次台阶级留一检验（leave-one-rung-out）：每次用其余 9 级台阶拟合"
              "“位移分布 → 决策损伤”的映射，事前预测被留出的一级，再对照实测。结论必须分层陈述。一方面，"
              "位移对目标轴的割线斜率 |b| 对未解析比例的迁移很稳：10 折平均绝对误差 0.052，预测-实测 R² = 0.932，"
              "方向命中 9/10。另一方面，位移离散度 std 对 τ_b 的**数值**迁移会失效：MAE = 0.483，数值命中 1/10，"
              "最大误差集中在还原轴的两个杠杆点（P0→P1 与 C0→C1），因为 std 跨 0.05–2.25 eV、变化 44 倍。"
              "但同一关系的**序数方向**依然稳健：按训练折中位数分侧，“离散度越大排序越差”在 10/10 折上命中，"
              "且丢弃任一级后 ρ(std, τ_b) 仍落在 [−0.912, −0.795]。还有一条边界必须写明：各台阶的未解析对集合"
              "几乎不共享成员（45 组两两 Jaccard 中位 0、31 组完全无重叠），所以“哪些分子对不可分辨”是台阶属性"
              "而不是分子对属性——判据事前能够预判的是未解析的**比例与量级**，不是在算出目标层之前指认具体的分子对。"
              "逐折结果与退化依据见 outputs/week24_corealign/loro.md；把口径从 18 分子整体下到**逐家族**后的 τ_b 与未解析比例见 3.2.6 节。")
    figure(doc, "F19_stage10_ladder.png",
           "图 10  五级台阶合成与决策稳定性总判：位移离散度（横轴）对排序一致性（纵轴），标注各台阶", 6.2)
    figure(doc, "F20_sigma_anatomy.png",
           "图 11  σ 的代数解剖：闭式 σ_ij = |δ_i−δ_j|/√2 与临界斜率 √2/z 的几何含义；面板 (d) 的 9 个预警子各做一次 AUC 检验，最小精确置换 p = 0.0083，大于 Bonferroni 阈值 0.05/9 = 0.0056（Holm 步降同样不显著），故该面板只作提示性证据，不支撑单点显著性主张", 6.3)


def _r_07(doc):
    h3(doc, "3.2.4  介电层为什么几乎免费")
    body(doc, "环境层的位移几乎完全由介电屏蔽贡献（见 3.2.2 节），因此值得单独追问：把隐式溶剂的介电常数"
              "一路提高到导体极限，还需要多少计算量？我们在 6 个介电点（ε = 5、10、20、40、80、200）上对 36 个"
              "（分子，电荷态）组合考察离导体极限的距离；加上作为 ε → 1 端点的气相点，即图 12(a) 的“七级阶梯”，"
              "更密的 10 点网格见 3.2.5 节。结果显示这不是简单的饱和，而是接近严格的 1/ε 幂律："
              "|ΔE|·ε 在 2057–2178 meV 之间基本恒定，即前因子约 2.1 eV。"
              "该律把“离导体极限还差多少”变成可以提前估算的量。")
    body(doc, "作为实用精度，ε = 200 时的逐分子残余最大为 19.62 meV（PC/阴离子）、平均 10.81 meV；"
              "从 ε = 200 提到 1000 只再走 11.3 meV。与冻结的决策容差相比，这只有氧化轴 δ_m 的 2.80%、"
              "还原轴的 0.95%，小 1–2 个数量级。因此介电层并非严格免费，但残差已经远小于排序论证所关心的尺度，"
              "在实用精度上“介电层免费”成立——但必须限定：可省的是 ε ≥ 200 的加密点，单一连续介质计算（P2）本身不可省，因为气相阴离子不束缚（见 2.3、3.2.1 节）。此外，Born 形式的线性轮廓对 24 条曲线的平均 R² 为 0.9861，"
              "显著优于 Onsager 形式的 0.8779，两参数族 δ = S(ε−1)/(ε+k) 给出的 k = 0.078 ± 0.100。")
    figure(doc, "F24_dielectric_limit.png",
           "图 12  介电极限：(a) 七级阶梯（气相 + ε = 5、10、20、40、80、200）对 u = 1−1/ε；(b) 三个模型的 R²；(c) 外推误差；(d) ε = 200 距导体极限", 6.3)


def _r_08(doc):
    h3(doc, "3.2.5  自洽场多解：漏解的代价与靶向双腿策略")
    body(doc, "开壳层与带电荷态的分子在自洽场求解中可能出现多个自洽解。若只用一个默认初猜，"
              "可能落到能量偏高的亚稳态，从而给决策量引入一个系统性缺陷。我们把默认初猜与"
              "读取前一步轨道的初猜（moread）配对比较，在 12 分子 × 3 态 × 10 个介电点（ε = 5、7、10、14、20、28、"
              "40、80、200、1000，比 3.2.4 节的 6 点网格更密）共 360 个格子上普查："
              "其中决策量真正用到的 material 格为每轴 120 个、共 240 个，其余为中性参考格；全部 360 格中 328 格两臂一致、32 格 moread 更低、0 格更高，最大缺陷 −0.285961 eV。"
              "另在 Stage 16 的 90 格抽样中，12 格差异超过 1 meV 且全部为负；普查与抽样是同一现象在两个网格上的观察——普查给出上界 A_axis 的来源，抽样给出典型尺度，两者不矛盾。就方向而言，漏解总是让默认臂偏低（就稳定性而言偏高）。")
    body(doc, "一个直接的做法是对全部格子都跑两条臂，但代价翻倍。我们证明了一条不需要任何预报的安全定理："
              "若两个格子的决策量分别为 d0（默认臂）与 d1（更优臂），翻转要求 |d0 − d1| = |d0| + |d1| > |d0|，"
              "而 |d0 − d1| 不超过单格最大效应量 A_axis。严格地说，一对分子的间距同时受两个格子的扰动，所以可证的单常数上界是 2 A_axis（氧化 0.3045 eV、还原 0.5719 eV），即 |d0| ≥ 2 A_axis 才保证不翻转；这一严格界会保护几乎全部格子（120/120，节约为 0）。实测把 A 取到 pair 级（max|e_i − e_j|，两轴分别为 0.1523 与 0.2860 eV，与单格值仅差约 3×10⁻⁵ eV）时，|d0| ≥ A_axis 的靶向在 660 对上零漏翻转，且保持 28.3% / 3.3% 的节约。因此本文区分两句：定理给出的是严格的单常数界 2 A_axis，靶向节约是这一目录上实测的 pair 级结果。"
              "实测 A_axis = 0.152252 eV（氧化，最坏格 TMP@ε = 5）与 0.285963 eV（还原，最坏格 EMC@ε = 1000），"
              "分别只有冻结 δ_m 的 21.7% 与 13.8%。以该阈值做靶向，在每轴 660 对中抓住全部 19 次（氧化）"
              "与 21 次（还原）真实翻转，漏 0；靶向双腿与全双腿相比，10 个介电点上的 τ_b 全部为 1.0000，"
              "Top-1/2/4 清单重叠也全为 1.000。作为对照，什么都不做的单腿协议 τ_b 最小值掉到 0.9394（氧化）"
              "与 0.8788（还原），说明漏解确实会改写排序，不能忽略。")
    table_3line(doc,
                ["轴", "A_axis/eV", "最坏格", "靶向/全部", "节约", "漏掉的翻转", "单腿 τ_b 最小值"],
                [["氧化", "0.152252", "TMP@ε=5", "86/120", "28.3%", "0", "0.9394"],
                 ["还原", "0.285963", "EMC@ε=1000", "116/120", "3.3%", "0", "0.8788"]],
                "表 5  漏解靶向双腿策略的安全性与代价（每轴 120 格、660 对）",
                "Table 3  Safety and cost of targeted two-guess reruns against missed solutions")
    body(doc, "不过，安全并不等于省钱：由于 12 个分子 × 10 个介电点构成的分布本来就很密，"
              "以 A_axis 为阈值需要保护 86/120（氧化）与 116/120（还原）的格子，只省 28.3% 与 3.3%。"
              "真正显著省钱的是只保护 Top-k 清单边界的弱化变体：半宽取 A_axis 时，"
              "k = 1/2 只需保护 10 与 20 个格子，省 91.7% 与 83.3%（k = 4 时省 66.7% 与 53.3%）；"
              "代价是不再保护清单内部的次序，而这通常正是筛选任务可以接受的弱化。")
    body(doc, "我们同时检查了“事前预报哪个格子会漏解”的可行性，结论是否定的：用气相描述符"
              "（small-gap value）在发现集上做留一交叉验证的准确率为 0.7083，低于多数类基线 0.7917；"
              "留出臂（6 个未参与建模的分子）准确率 0.750，但真阳性为 0；两特征 logistic 模型的"
              "留一 AUC 为 0.821，也不优于单变量。这两次预报失败恰好正当化了上面那条不依赖预报的靶向策略："
              "与其预测哪里出错，不如用一个可证的上界把出错的影响框住。")
    figure(doc, "F45_targeted_two_guess.png",
           "图 13  漏解靶向双腿：效应量 A_axis 与阈值的关系、协议校验以及 Top-k 变体的节约比例", 6.3)


def _r_09(doc):
    h3(doc, "3.3.2  配位饱和的证据")
    body(doc, "如果 Li+ 第一壳配位确实抬高了氧化稳定性，那么继续增加配体时这一抬高应当逐步减弱。"
              "我们以 EC 为代表分子、在 GFN2-xTB 水平补出第三个配位点：n = 0→3 的氧化位移依次为 "
              "0.000、3.897、2.015、1.292 eV，还原位移依次为 0.000、6.291、5.672、5.336 eV。"
              "增量 dd(2→1) 为氧化 −1.882、还原 −0.619 eV，dd(3→2) 为氧化 −0.723、还原 −0.336 eV，"
              "两轴都与前一步同号且绝对值更小（比值 0.384 与 0.543）。这一形状与次线性、与饱和一致相容，"
              "但三个点定不出渐近线，因此只能表述为“与饱和一致”而不是“证明了饱和”。")
    body(doc, "我们还做了跨层级的无量纲对照：只比较比值 dd(2→1)/dd(1→0)，r2SCAN-3c 给出氧化 −0.4080、"
              "还原 −0.2386（12 个配位基元），GFN2-xTB 给出氧化 −0.4829、还原 −0.0984（1 个分子）。"
              "氧化轴的两层形状比接近，还原轴不接近——这与 3.3.1 节的态身份结论一致："
              "两个层级的引擎对“电子落在哪”的判断不必一致，因此还原轴的跨层级对照只能作为提示。"
              "需要强调，跨层级的绝对数值一律不得并列（两层的 IP/EA 相差 eV 量级）。")
    figure(doc, "F46_shell3_saturation.png",
           "图 14  第三个配位点：(a) n = 0→3 的位移阶梯；(b) 增量 dd 的衰减；(c) 跨层级无量纲形状比对照", 6.3)


def _r_10(doc):
    h3(doc, "3.3.3  几何盆地判据的失效边界：从 RMSD 到势垒")
    body(doc, "前文用 RMSD 一刀切（0.02 Å）判断两段几何是否同一盆地。为复核这一代理量，"
              "我们在 3 个关键格子上用 ORCA 6.1.1 的 regular NEB 精修（端点直接取 Stage 19 两条臂的弛豫终点）："
              "EC/阳离子/ε = 5 的峰高仅 0.000141 eV（比 1 kT 小约 182 倍），EC/阳离子/ε = 20 为 5.3×10⁻⁵ eV，"
              "TEGDME/阴离子/ε = 20 为 0.679 eV（直线插值高估 97.4 倍）。三格中 2 格与 RMSD 判决一致、1 格冲突："
              "EC/阳离子/ε = 5 的端点位移 0.100 Å 已越过 0.02 Å 阈值，但沿 0.319 Å 的路径摊开后并没有势垒，"
              "两端点其实是同一盆地。这说明 RMSD 作为盆地代理在 0.02–0.10 Å 带内会误判，"
              "更合适的判据是把峰高与 kT（及 δ_m）比较，这与全文的 δ 框架自洽。"
              "限制：regular NEB 非 climbing-image，峰高偏乐观；本轮只精修 3 格（抽样）；端点不重新优化。")
    figure(doc, "F44_neb_refinement.png",
           "图 15  几何盆地判据的失效边界：三个格子的 NEB 能量剖面与峰高，以及与 RMSD 判决的一致/冲突", 6.3)


def _r_11(doc):
    h3(doc, "3.6.1  最小计算层预算")
    body(doc, "把上述结果合起来，可以对“小分子集筛选到底需要算哪些层”给出一个定量的回答。这里的“预算”指**该算哪些计算层**；它与“需要买多少昂贵标签”是两件不同的事，后者见 3.6.3 节。"
              "第一，几何台阶的位移 std 只有 0.05–0.08 eV、τ_b ≥ 0.848，且未解析对比例 ≤ 0.06，"
              "因此在排序目的下可以省略色散校正泛函的几何重优化，直接复用半经验几何。"
              "第二，介电层在 ε ≥ 200 之后的残余已降到 20 meV 以下，是氧化轴不确定度预算的 2.8%，"
              "因此 ε ≥ 200 的介电加密点对排序没有贡献、可以省略（单一连续介质计算本身不可省）。"
              "第三，位移离散度判据 q_ij ≤ √2/z 可以在花钱之前算出哪些分子对本来就不可能被分辨，"
              "从而把这些分子对从“需要更高精度”的清单里剔除。第四，若必须处理自洽场多解，"
              "用 A_axis 定理做靶向可以保证零漏翻转，而若只关心入选清单，Top-k 变体在 k = 1/2 时分别可省 91.7% 与 83.3% 的重算量（k 越大越接近全双腿）。"
              "综合起来，一个以排序为目标的筛选工作流只需要：一个半经验层用于覆盖化学空间，"
              "一个色散校正泛函层用于给出可信次序，一条可证的漏解上界用于约束多解风险，"
              "而几何重优化与 ε ≥ 200 的介电加密层可以不算。")
    body(doc, "本节回答“该算哪些层”、3.6.3 节回答“该买多少标签”，两者互不相加；"
              "把它们与前面的判定串成一条自上而下的路径，即图 19。")


def _r_12(doc):
    h3(doc, "3.6.2  broad pool 的实际演示：最小信息预算省下多少")
    body(doc, "前面的最小信息预算是在核心集上得出的。为检查它是否只是核心集的产物，并给出一次真实的预算节省，"
              "我们把判据放到 40 个扩展分子上。broad 池只有 P0 层，没有 P1/P2，因此逐分子位移由核心集标定的廉价预测器外推"
              "（氧化用家族平均位移、还原用 P0 的线性回归，均按留一交叉验证选优），残差 σ_r ≈ 0.49 eV；"
              "随后用闭式 σ_ij = |δ_i − δ_j|/√2 与 q_ij ≤ √2/z 做蒙特卡洛（4000 次）判定。结果："
              "氧化轴 37.4% 的分子对在提交前就不可分辨、目标层仍有 19.5% 不可分辨；还原轴目标层不可分辨比例高达 76.0%。"
              "若把“值得升级”定义为某 Top-k 清单的会员概率落在 (0.1, 0.9) 内，则按主判据（两轴并集、保护 Top-10% 清单、z = 1）"
              "只需升级 21/40 个分子、省 47.5%；把保护范围放宽到 Top-10/20/30% 的保守口径则需升级 38/40、只省 5.0%。"
              "敏感性：z = 1.96 时主判据节省 50.0%；用 |core| = 12–18 的子集重标定，主判据节省稳定在 47.5%–60%，"
              "说明预算节省不依赖核心集选取，而保守口径对核心集敏感。限制：broad 池没有 P1/P2，位移靠外推，"
              "故该演示只作排序级的预算估计，不外推绝对值。")
    figure(doc, "F47_broadpool_budget.png",
           "图 16  broad pool 的最小信息预算演示：不可分辨对比例、值得升级子集与两条口径下的预算节省，以及核心集子集重标定的敏感性", 6.3)


def _r_13(doc):
    h3(doc, "3.5.1  直接学习与位移学习：留一家族出外推下的判决")
    body(doc, "前十二节把升级路径当作已知的位移逐级解剖；本节换一个角度，检查这些位移能否在只看廉价特征的条件下"
              "被预测，以及直接学习与位移学习哪一种更可靠。数据为 288 组结果：三种划分 × 两种形状 × 六个模型 × "
              "多个（任务·特征集·轴）组合。按 τ_b 中位数选模型，并做同模型、同划分的配对比较"
              "（分子层配对 bootstrap，2000 次重抽）。")
    body(doc, "结论是方向性的、而非一边倒的。在 LOFO 外推下，8 个分组中有 7 个的配对 Δτ_b 为正，"
              "其中 3 个分组的区间不含 0：方法台阶（M·X0）两轴分别提升 Δτ_b = +1.342 [0.793, 1.713] 与 "
              "+1.222 [0.670, 1.600]，环境台阶（E·X0+P1）氧化轴提升 +0.389 [0.110, 0.722]；"
              "最强的单格是方法台阶氧化轴上的常数模型，τ_b 由 −0.725 升到 0.595。"
              "但 24 个（划分·轴·特征集）组合中有 19 个的配对区间跨 0，即大多数格子上两者不可区分，"
              "因此只能说位移学习是更稳妥的默认选择，不能说它普遍更优。唯一为负的分组落在 C0→C1 还原轴"
              "（Δτ_b = −0.143），正是 3.3.1 节判定的态身份改变台阶——还原态 11/12 为 Li 中心或混合还原，"
              "在那里位移已不再是同一可观测量之间的差，位移学习随之失效，与核心方案关于该情形应转向"
              "态分类与条件回归的预期一致。")
    table_3line(doc,
                ["任务·特征集·轴", "形状", "最优模型", "τ_b [95% CI]", "MAE/eV", "R20%/eV"],
                [["M·X0·氧化", "direct", "krr", "0.294 [−0.145, 0.681]", "0.849", "1.087"],
                 ["M·X0·氧化", "Δ(shift)", "constant", "0.595 [0.219, 0.859]", "0.527", "0.656"],
                 ["M·X0·还原", "direct", "rf", "0.359 [−0.021, 0.639]", "0.398", "0.870"],
                 ["M·X0·还原", "Δ(shift)", "constant", "0.556 [0.221, 0.826]", "2.130", "0.263"],
                 ["E·X0+P1·氧化", "direct", "ridge", "0.843 [0.667, 0.986]", "0.328", "0.027"],
                 ["E·X0+P1·氧化", "Δ(shift)", "rf", "0.922 [0.786, 1.000]", "0.206", "0.027"],
                 ["E·X0+P1·还原", "direct", "rf", "0.686 [0.427, 0.887]", "0.270", "0.044"],
                 ["E·X0+P1·还原", "Δ(shift)", "krr", "0.739 [0.566, 0.876]", "0.243", "0.012"]],
                "表 6  留一家族出外推下按 τ_b 中位数选出的最优模型（N：M/E = 18，C = 10；R20% 为 selection regret，越小越好）",
                "Table 6  Best models under leave-one-family-out")
    body(doc, "第二点与全文主轴一致：以 MAE 或 R² 选模型不等于以决策质量选模型。在 48 个块内对六个模型同时按 MAE "
              "与 selection regret 排序，ρ(τ_b, R_20%) = −0.647、ρ(R², R_20%) = −0.428，而 ρ(MAE, R_20%) = +0.388；"
              "720 个模型两两比较中有 186 对（25.8%）出现“MAE 更优但 regret 更差”的反转。")
    body(doc, "第三，关于“随机划分会高估可迁移性”这一常见担忧，数据把它精确化了：随机划分高估的是**值误差指标**，"
              "而非排序指标。在直接学习形状下，随机划分的 R² 中位数比留一家族出高 0.182（8 格中 6 格为正），"
              "MAE 中位数低 0.069 eV（8 格中 5 格为正）；但同一模型在三档划分下的 τ_b 差距很小且方向不定"
              "（16 格中 7 格为正、中位差 −0.007）。这正是全文“值误差与排序误差解耦”的又一体现："
              "只看随机划分的 R² 会高估模型，但起决定作用的排序并不随之改善。仍需提醒这是 n = 18 的小样本结论，"
              "且随机划分本身只作插值基线，不构成可迁移性证据。")
    body(doc, "两处口径提醒必须与表 6 同时读。其一，C 任务只有 10 个分子带 C1 标签，其余 8 个核心分子在 Stage 7 中记为 "
              "dropped_molecules——那是“缺 C1 标签”，不是“被丢弃的样本”。其二，表 6 中 M·X0·氧化轴 Δ(shift) 的 τ_b = 0.595 "
              "与表 3 中 P0→P1 还原轴的 0.595 只是数值巧合：前者是交叉验证预测排序与原子真值的次序一致性，"
              "后者是台阶级排序一致性，两者不可互引。")
    figure(doc, "F48_ml_direct_vs_shift.png",
           "图 17  直接学习与位移学习：(a) 留一家族出下两种形状的最优模型及 95% 区间；(b) 同模型同划分的配对 Δτ_b 及其 95% 区间，按随机/分组/留一家族出分档", 6.3)
    body(doc, "限制必须与数字同时引用：LOFO 与 group 各只有 1 次留出通过，其区间来自分子层配对 bootstrap 而非重复种子，"
              "只有随机划分有 5 个固定种子的重复；M/E 的 n = 18、C 的 n = 10，故本节只作机制性论证，"
              "不足以对复杂模型的泛化能力下强结论。")
    body(doc, "本节结论必须连同它的反例一起读。上面的配对 bootstrap 是按（任务·特征集·轴）分组、同模型同划分统计的；"
              "若改用冻结的逐格最优模型表（每一格在 direct 与 shift 两种形状上各自取中位 τ_b 最优的模型，见 "
              "outputs/week32/delta_vs_direct.csv），同样 8 个分组里只有 6 个的 τ_b 更好，两个反例是 C|X0|reduction "
              "与 C|X0+X1|reduction。两种口径的模型选择规则与分母不同，不能互相替代；无论取哪一种，本节能支持的都是"
              "“位移学习是更稳妥的默认选择”，而不是“位移学习普遍更优”。")



def _r_14(doc):
    h3(doc, "3.6.3  最小昂贵标签预算：主动学习重放")
    body(doc, "3.6.1 节回答的是“该算哪些计算层”；本节回答一个与之正交的问题：若层已定，恢复一个可信排序最少需要买多少个昂贵标签。"
              "做法是回溯式重放——把已有的完整目标标签暂时隐藏，从 4 个初始种子出发、每轮只揭示 1 个候选，"
              "共重复 20 组冻结种子；采集函数比较随机、多样性、不确定度与排序感知四种"
              "（排序感知按 p_i = P(i 进入 Top-k) 的二元熵采集），并严格限制采集只能使用 X0 特征。")
    body(doc, "以中位 τ_b 首次达到 ≥ 0.80 为“恢复排序”的判据，并排除 n_T = n 的构造性端点：10 个分子的小池两轴均需 9 个标签；"
              "18 个分子的池需要 12–15 个（最省一档为 12）。按标签效率排序为 不确定度 ≈ 多样性 ≳ 排序感知 > 随机，"
              "但这一排序只是提示性的：18 组对比的 τ_b 与 selection regret 区间两两重叠，"
              "因此不能写成“某采集函数显著更优”。更值得注意的是，排序感知采集并没有稳定胜出"
              "（对随机略正、对不确定度与多样性多为负），这与该方法通常被宣传的优势不符，我们如实保留这一负面结果。")
    table_3line(doc,
                ["池（分子数）", "random", "diversity", "uncertainty", "ranking_aware"],
                [["C·氧化（10）", "9", "8", "8", "9"],
                 ["C·还原（10）", "9", "9", "9", "9"],
                 ["E·氧化（18）", "15", "14", "12", "13"],
                 ["E·还原（18）", "14", "13", "13", "13"],
                 ["M·氧化（18）", "13", "13", "12", "13"],
                 ["M·还原（18）", "13", "13", "13", "13"]],
                "表 7  中位 τ_b 首次达到 ≥ 0.80 所需的昂贵标签数 n_T（20 组冻结种子的中位数；已排除 n_T = n 的构造性端点）",
                "Table 7  Expensive-label budget to reach median \u03c4_b \u2265 0.80")
    figure(doc, "F17_stage8_active_learning.png",
           "图 18  最小昂贵标签预算：n_T → Kendall τ_b 的四条采集曲线（20 组种子的中位数与 2.5/97.5 分位带，虚线为 τ_b = 0.80）", 6.3)
    body(doc, "两个限制必须与数字同时引用：其一，池只有 18（条件态 10）个分子，τ_b 在 N = 10 子集上的抽样标准差约 0.13，"
              "故 1–2 个标签的差别在噪声范围内，本节结论不得外推为真实 DFT 预算；"
              "其二，“已知标签用真值、未标注用模型预测”的排序规则使 n_T = n 时 τ_b 恒为 1，这是构造性端点而非成绩，"
              "已在全部统计中剔除。其三，10 分子池所需 8–9 个标签距该构造性端点只差 1–2 步，池越小这种空洞性越强，"
              "因此本节以 18 分子池（12–15 个标签）为主口径，10 分子池只作对照。")
    body(doc, "本节的两条适用边界必须与曲线同读。其一，家族留出口径下的主动学习曲线**不可用**：冻结的 replay 只在池内做插值，"
              "一旦把整个家族留出，池内可用于插值的邻居随之消失，曲线不再有定义；因此本文所有预算数字都是**池内插值**口径，"
              "不能读成跨家族外推的预算。其二，本节的成功标准是内部操作性标准——中位 τ_b ≥ 0.80、Top-20% 清单重叠完整、"
              "selection regret ≤ 池内目标量程的 5%，且要求在 ≥ 80% 的重复中成立——它来自本文自己的决策口径，未经任何外部校准；"
              "因此“恢复中位 τ_b ≥ 0.80 需要 9–15 个昂贵标签”这句话只在同一口径内成立，不能外推为真实筛选所需的 DFT 数量。")

    figure(doc, "F51_minimal_budget_flowchart.png",
           "图 19  最小信息预算决策流程图：把 3.6.1 节的“该算哪些计算层”与 3.6.3 节的“该买多少昂贵标签”"
           "合成一条自上而下的判定路径（框内小字给出每个数字的来源文件与字段；两条预算互不相加）", 6.3)


def _r_15(doc):
    h3(doc, "3.1.2  溶液相锚点：Gate 1 排序层判据的首次评估")
    body(doc, "本节报告一次预注册的负结果。本文此前各节的排序比较都发生在模型之间、或模型与气相锚点之间，"
              "本节第一次把排序放到一条外部液相锚点序列上检验。预注册的判据是 within-series 排序一致性："
              "只允许在同一实验系列内部成对比较，要求可用分子对 n_pairs ≥ 18 且 Kendall τ_b ≥ 0.9（2.6 节）；"
              "此前该判据没有合格数据、无法评估，本节引入的氧化锚点系列使它第一次可评。")
    body(doc, "该系列的条件是玻碳工作电极、SCE 参比（KCl 琼脂盐桥隔离）、0.65 mol·dm⁻³ Et₄NBF₄ 支持电解质、"
              "5 mV·s⁻¹ 线性扫描与 25 °C，起始电位统一定义为电流密度超过 1 mA·cm⁻² 的电位，"
              "再经 +3.28 V 的标度偏移换算到 Li⁺/Li 标度。表内 14 行中有 7 行落在本文核心集内"
              "（EMC 7.0、PC 6.9、MA 6.7、SL 6.6、EC 6.5、DOL 5.5、DMSO 4.8 V），"
              "其余 7 行在核心集之外，判据脚本按设计跳过——而“跳过”不等于“通过”。"
              "7 个核心集分子给出 C(7,2) = 21 对，刚好越过 n_pairs ≥ 18 的门槛。")
    body(doc, "结果不支持该判据：τ_b = 0.4286，远低于 0.9，判决为排序不一致。换模型臂也不改变结论——"
              "同一 21 对上 P0 为 0.5238、P2 为 0.5238。三臂两两之间的差异都不超过 2 个不一致对，在 n = 7 的锚点集上统计上不可区分：这里只能说注册口径 P1 的数值最低，而不能说它构成显著劣势，更不能反过来说 P0 优于 P1。"
              "不一致的分布相当集中：6 个不一致对中有 4 个涉及 EC。实验把 EC 排在 7 个分子的第 5 位，"
              "三臂却一致把 EC 排在第 1 位，因此这不是某一臂的噪声，而是本文所用描述符族的一个系统性盲点。"
              "将 EC 单列后其余 6 个分子的 τ_b 为 0.7333，但该数值不能读作“剔除后通过”：它仍低于 0.9，"
              "且剔除后可用分子对只剩 C(6,2) = 15，低于预注册的 n_pairs ≥ 18，"
              "因此该变体在冻结判据下的判决是“对数不足、不可判定”，而不是“通过”。"
              "本节由此给出两句结论而不是一句：判据未通过（以注册的 7 分子、21 对为准），"
              "且未通过的主要来源是一个条件可疑的锚点。")
    body(doc, "EC 这一行本身带有一处可以独立于本次结果而提出的疑点：该系列主源的溶剂选择判据是熔点低于 30 °C，"
              "而 EC 的熔点为 36.4 °C，按此判据本不应进入其 20 溶剂表；因此该表的 EC 值很可能取自同组的另一篇实测工作，"
              "其装置、判据、支持电解质与温度是否与主源完全一致，需要核对原文才能确认。"
              "这一点使 EC 的处置由“看完结果后再剔除”变为“按独立的文献判据做锚点质量分层”——我们据熔点规则把 EC 标为条件待核实的锚点，"
              "而不是因为它拉低了 τ_b；但两种处置在结论上都不改变 Gate 1 的状态：分层后的 0.7333 仍低于 0.9，且只有 15 对、低于预注册下限。")
    body(doc, "为区分“判据确实不一致”与“锚点重复性造成的偶然低值”，把引入说明所报的 0.1 V 系列重复性"
              "作为锚点噪声注入实验端（正态，2×10⁴ 次重抽样）：τ_b 的 95% 区间为 [0.3333, 0.6190]，"
              "均值 ± 标准差为 0.4518 ± 0.0900，区间整体落在阈值之下；20000 次中 τ_b ≥ 0.9 只出现 1 次，"
              "即 P(τ_b ≥ 0.9) = 5.0×10⁻⁵。观测值 0.4286 位于该分布的中心附近（P(τ_b ≥ 观测值) = 0.797），"
              "说明低值不是重复性噪声造成的偶然结果。对 7 个分子的全部 7! = 5040 种排列做精确置换检验，"
              "单尾 p = 0.1194——它说明连“与实验序正相关”都未达到常规显著性水平。对这个结果有两种并列的解释，本节不偏取其一："
              "(a) 热力学代理量与动力学起始电位在机制上确实脱节；(b) n = 7 且其中含一个条件可疑锚点，检验功效本就有限。"
              "只写 (a) 是过度解读，只写 (b) 是开脱。可以确定的是：判据没有被这批数据支持，而不是“擦着阈值”。")
    body(doc, "本节结论有两条边界必须同时写明。其一，该系列是纯溶剂 + 鎓盐体系、不含 Li⁺，"
              "因此它只对应本文的 C0 梯级，C1/C2 的排序结论不能用它裁决。"
              "其二，1 mA·cm⁻² 的起始电位是动力学量，而本文的 ΔSCF 量是热力学量，两者只在排序层可桥接；"
              "驱动负结果的 EC 恰是最需要警惕的一行——它与相邻行的间距落在所报重复性带内，"
              "而该系列自身已知存在 N/S 孤对电子驱动的提前氧化这一类动力学例外模式。")
    body(doc, "还原轴的处境与此不同：可用的同系列证据只有 3 个物种（3 对），远低于 n_pairs ≥ 18，"
              "因此它不是“判负”而是不可判定——证据不足与排序不一致是两件事，"
              "把两者并成一个结论会高估本文对还原轴的检验强度。此外这 3 行并非同装置序列，"
              "其判据是首圈 dQ/dV 峰位而非线性扫描起始电位，只能作旁证；"
              "而 P1 下气相阴离子 18/18 不束缚（2.3、3.2.1 节），还原轴的决策结论本就只以 P2/C1 为载体，"
              "对还原轴做锚点对照只具完备性意义。")
    figure(doc, "F52_gate1_ordering.png",
           "图 20  溶液相氧化锚点的排序检验：(a) 实验位次与注册臂 P1 位次的对照（EC 由实验第 5 位被排到第 1 位）；"
           "(b) 两组位次的斜率图，6 个不一致对表现为交叉线；(c) 锚点噪声下 τ_b 的 bootstrap 分布与 0.9 阈值；"
           "(d) 逐分子剔除后的 τ_b 敏感性（EC 升幅最大）", 6.3)
    body(doc, "本节的诚实边界集中在数据的来源形态上，必须与全部数字同句引用：这批值是外部提供的转录值，"
              "两条上游原著都不在本地文献库、本环境亦无网络，仓库没有对任何一行做过独立复核"
              "（入库行标记 transcription_only），0.1 V 是引入说明所报的系列重复性而非来源给出的不确定度；"
              "此外本项目此前经 Crossref 核验到的 Okoshi 2015 题录属“理论分析”类工作，"
              "与引入说明中“该文重刊 Ue 1994 实验值”的表述不一致，本环境无法裁定。"
              "因此本节结论的强度是：一次可复算、口径已锁死的判据评估，而不是一次经原始文献复核的实验裁决。"
              "把 Gate 1 写成“已闭合”会超出数据能支持的范围。")
    body(doc, "这批数据的性质还必须与数字分开声明：within-series 表的 14 行氧化锚点 provenance 全部为 transcription-only，"
              "未回溯到原始测量；两篇上游原著均不在本地文献库、本环境亦无网络，仓库没有对任何一行做过独立复核。"
              "因此这 14 行只作为 designated reference model 提供外部参考条件，不构成本文的实验验证证据。"
              "同时说明本文的计算范围：全文零新增电子结构计算，所有结论只对仓库中已有的冻结数据成立。")



def _r_16(doc):
    h3(doc, "3.2.6  逐家族口径：family-resolved 与 cross-family 统计")
    body(doc, "前面各节的排序统计都建立在 18 个分子的整体口径上。核心方案另有一项硬性要求：Stage 6 必须给出 family-resolved 与 cross-family 统计，"
              "且每个家族的统计量都要带置信区间、不得读作显著性。本节把这个口径补上，数据全部由已冻结的五级台阶逐分子产物重算，"
              "零新增电子结构计算；重算值与原产物逐项比对的最大绝对偏差为 1.1×10⁻¹⁶，即本节数字与 3.4.1 节同源。")
    body(doc, "家族划分取 8 个结构家族（环状碳酸酯 4、链状碳酸酯 3、酯 3、醚 3、腈 2、砜 1、亚砜 1、磷酸酯 1）。"
              "把 population、台阶、轴与家族四种因素组合起来共 160 格，但**家族内 τ_b 只在家族分子数 ≥ 3 时才有定义**："
              "结果只有 16 格可估计，144 格记为不可估计——其中 104 格来自单分子家族（砜、亚砜、磷酸酯），40 格来自只有一对的腈类。"
              "更值得注意的是：common-10 子集的全部 80 格都不可估计（每个家族在该子集里最多只剩 2 个分子），"
              "因此本节的 family-resolved 结论只能建立在 native-18 上，这一点必须与数字同时读。")
    body(doc, "可估计的 16 格全部落在方法台阶（P0→P1）与环境台阶（P1→P2）：几何台阶与两条配位台阶的逐分子覆盖本就不足 18 个分子，"
              "分到家族后没有一个家族能凑够 3 个。在这 16 格里，12 格的家族内 τ_b = 1.000，"
              "4 格偏离：P0→P1 氧化轴的酯类为 0.333，P0→P1 还原轴的醚类为 0.333、链状碳酸酯为 −0.333，P1→P2 还原轴的醚类为 −0.333。"
              "两个方向性特征值得记录：其一，**4 格偏离里有 3 格落在还原轴**，而氧化轴在 P1→P2 上四个家族全部保持 1.000；"
              "其二，链状碳酸酯在 P0→P1 还原轴上的 −0.333 是全表唯一的负值。这与 3.2.1 节的整体结论一致——还原轴在方法台阶上被改写得更彻底。"
              "家族内的未解析比例同样不均匀：腈类在两条氧化台阶上 f_unresolved = 1.000（两个分子始终不可分辨），而醚类在 P1→P2 还原轴上"
              "未解析比例为 1.000、家族内 τ_b 却为 −0.333，说明“不可分辨”与“次序被改写”是两种不同的失败模式。")
    figure(doc, "F53_family_resolved.png",
           "图 21  逐家族口径的排序统计：(a) 各家族在五个台阶、两条轴上的家族内 τ_b（空心点标 not_estimable，仅 native-18 的 16 格可估计）；"
           "(b) 家族内未解析比例 f_unresolved 的对照；带 bootstrap 区间", 6.3)
    body(doc, "本节的边界必须写死：家族内只有 3–4 个分子，bootstrap 95% 区间普遍张到 [−1.000, 1.000]（有效重抽样约 4400–4900/5000），"
              "因此**任何单一家族的 τ_b 都不能被称作显著**，本节只报告方向与不一致的落点，不据此下强度结论。"
              "另外两点口径说明：其一，`outputs/week24_corealign/loro_folds.csv` 的留出标签是台阶而非家族（它是留一台阶出回归的产物、不带家族维度），"
              "故未被本节使用；其二，本节的 f_unresolved 沿用冻结的 pair tolerance 口径（z = 1.0，既有产物未施加 δ_m，故 tolerance = 0），"
              "并另报 z = 1.96 的敏感性列。本节不改变前面任何一条判决，只是把“整体口径成立”这一结论在逐家族层面标注出它的适用边界。")


def _r_17(doc):
    h3(doc, "3.3.4  配位位移与描述符标签的关系（§24 Figure 5 的补全）")
    body(doc, "本节补上核心方案 §24 Figure 5 的 ΔΔG_coord—描述符维度。3.6 与 3.1.2 节已确认：在全部（台阶 × 轴）组合上 f_robust_inv 全为 0，"
              "本文从未观测到一次真正的稳健翻转。因此本节不声称发现“配位诱导反转”，只回答两个更基础的问题——配位位移有多大、它与分子内哪些描述符标签同向。"
              "口径取具有 C1（Li+ 配位条件态）的 10 个分子（AN、DMC、DME、DMSO、DOL、EC、GBL、SL、SN、TMP），主 motif 10 个；"
              "位移取自 week5 的 C1 逐分子产物，与 3.3.1 节 C0→C1 台阶逐分子一致：氧化轴位移 dIP 均值 +4.887 eV、还原轴位移 −dEA 均值 −6.578 eV，"
              "逐分子重算与冻结 ladder 的偏差为 0。")
    body(doc, "7 个描述符 × 2 条轴共 14 条秩相关全部用精确置换检验（n = 10，10! = 3 628 800 种排列逐一枚举），不用正态近似。"
              "氧化轴上，tpsa（拓扑极性表面积）ρ = −0.890（p = 0.0011）、donor_count ρ = −0.794（p = 0.0077）、"
              "heteroatom_count ρ = −0.702（p = 0.028）、n_heavy ρ = −0.666（p = 0.039）达到常规 0.05 水平；"
              "mw ρ = −0.564（p = 0.096）、li_contacts_n ρ = +0.426（p = 0.257）、rotatable_bonds ρ = −0.255（p = 0.483）不显著。"
              "还原轴上 14 条无一达到 0.05，最强的一条是 tpsa ρ = −0.457（p = 0.185）。方向一致：杂原子越多、极性表面积越大、分子越重，"
              "配位后氧化轴位移越小，即配位对该分子的“抬升”越弱。")
    body(doc, "这里必须沿用与 3.4.1 节相同的纪律。3.4.1 节有 9 个预警子做 AUC 检验，Bonferroni 校正后不再显著；本节 14 条相关同样未作多重比较校正。"
              "若按 14 条做 Bonferroni（α ≈ 0.0036），只有 tpsa 一条仍在界内，donor_count 及以下都会被校正排除。"
              "因此本节把这些一律读作探索性提示，不得称显著；且 tpsa、donor_count、heteroatom_count、n_heavy 在 n = 10 内彼此高度共线，"
              "单凭 ρ 无法分辨究竟是哪一个描述符在起作用。")
    body(doc, "分层维度按“两组各 ≥ 4 个分子才给精确置换 p”的规则处理：14 个维度中只有 3 条可估计，"
              "其余 44 条（family、role、donor_element、donor_count 及部分 tag 组合）因至少一组 n < 4 记 not_estimable。"
              "可估计的 3 条都在氧化轴上：配位齿数（单齿 6 vs 双齿/多齿 4，均值差 −0.603 eV，p = 0.124）、"
              "态身份（molecule_centered_redox 6 vs no_intact_minimum_found 4，−0.698 eV，p = 0.071）、"
              "环状 vs 链状（4 vs 6，+0.316 eV，p = 0.476）——p 值全部未过常规阈值，只作方向记录。"
              "齿数还有一处口径必须写清：图上的单齿/双齿取自 C1 主 motif 的实际 Li 接触数（n_Li），而 core_set.csv 的 donor_atoms 给的是 donor 类型、"
              "donor_count 给的是杂原子总数，三者不是一回事；DOL、SL 几何上 n_Li = 2 却未打 chelating tag，属于 tag 口径与几何口径的已知不一致。")
    body(doc, "两条不可得边界要写明：其一，ESP 描述符在仓库内不存在（not_available_in_repo），本节不报；"
              "其二，flexible、fluorinated、unsaturated 三个 tag 只出现在 C1 子集之外的分子上（TEGDME、FEC、VC），本子集内不可检验，"
              "柔性维度改用 rotatable_bonds 作数值代理。综合起来，本节给出的是 §24 Figure 5 的“语义维度”，"
              "其“inversion 机制”仍无实测证据；表 14 相应记为“位移—标签维度已补、机制结论未观测”。本节不改动前面任何一条判决。")
    figure(doc, "F55_coord_descriptor_tags.png",
           "图 22  配位位移与描述符标签的关系（§24 Figure 5 的补全）：(a) 逐分子两轴配位位移 dIP 与 dEA，右侧标 Li 接触数 n_Li、donor 杂原子数 d 与二价阳离子态身份；"
           "(b) 7 个描述符 × 2 条轴的 Spearman ρ（格内为精确置换 p，n = 10 全枚举）；(c) 按配位齿数 / donor 元素 / donor_count / 态身份分层的中位数与四分位距；"
           "(d) dIP 与 tpsa、donor_count 的散点。n = 10 且未作多重比较校正，全部读作提示性证据、不得称显著", 6.3)


def write_results(doc):
    h1(doc, "3  结果与讨论")
    h2(doc, "3.1  模型层级与外部参考边界")
    body(doc, '本节回答两个前置问题：研究对象是什么，以及目标有多可信。它对应工作包 WP1 与 WP7，主要图件为主图 1（三层研究框架 P/C/reference）与主图 2（外部锚点与方法 / 不确定度审计）。后面五节的所有判决都建立在这一边界之上：内部可复现不等于对实验有效。')
    _r_01(doc)
    _r_15(doc)

    h2(doc, "3.2  电子结构与介质物理如何改变排序")
    body(doc, '本节回答“哪些物理改变排序”，对应 WP2（主图 3）。它按台阶逐级报告电子结构层（P0→P1、G1→G2）、连续介质层（P1→P2、介电极限）与自洽场求解所引入的位移与决策量，并给出逐家族口径。')
    _r_02(doc)
    _r_03(doc)
    _r_04(doc)
    _r_07(doc)
    _r_08(doc)
    _r_16(doc)

    h2(doc, "3.3  Li+ 配位条件态与还原态身份")
    body(doc, '本节回答“为什么发生变化”，对应 WP3（主图 5）：Li+ 配位条件态如何改写排序、还原态身份如何分层、配位是否饱和，以及配位位移与分子内描述符标签的关系。')
    _r_05(doc)
    _r_09(doc)
    _r_10(doc)
    _r_17(doc)

    h2(doc, "3.4  不确定度感知的材料筛选")
    body(doc, '本节回答“哪些变化影响选择”，对应 WP4（主图 4）：把位移离散度变成一个可判定的不确定度预算与稳健翻转判据，并给出分辨率（unresolved）、Top-k 清单与 selection regret 的决策口径。')
    _r_06(doc)

    h2(doc, "3.5  模型位移与配位修正的可预测性")
    body(doc, '本节回答“能否廉价预测修正”，对应 WP5（主图 6）：在留一家族出（LOFO）外推下比较直接学习与位移学习，并同时报告预测误差与实际筛选决策指标。')
    _r_13(doc)

    h2(doc, "3.6  最小昂贵信息预算")
    body(doc, '本节回答“最少需要多少昂贵信息”，对应 WP6（主图 7）：最小计算层预算、broad pool 的实际演示与四策略主动学习重放。')
    _r_11(doc)
    _r_12(doc)
    _r_14(doc)


def write_conclusion(doc):
    h1(doc, "4  结语")
    body(doc, "本文把“廉价代理能否用于电解液溶剂筛选”这一问题从数值误差转写为排序稳定性，"
              "并用唯一变量台阶实验把它量化。主要结论有三点。")
    body(doc, "第一，值误差与排序误差是近似独立的两个量。最尖锐的一对是 GFN2-xTB ΔSCF 与 r2SCAN-3c 气相量："
              "前者绝对误差高达 4.48 eV、排序 τ_b 却有 0.91，后者把绝对误差降到 0.25 eV（约 1/18）、τ_b 却降到 0.73；"
              "Koopmans 量是另一组对照（绝对误差 1.38 eV，τ_b 0.61）。"
              "误差小约十八倍的模型并没有换来更好的次序，评价代理指标的可用性必须看排序，不能看 MAE。")
    body(doc, "第二，改写排序的不是位移的大小而是位移的离散度。跨十级台阶，"
              "ρ(std, τ_b) = −0.851 而 ρ(|mean|, τ_b) = −0.535，ρ(std, f_unresolved) = +0.894。"
              "由此得到闭式判据 σ_ij = |δ_i − δ_j|/√2 与无量纲条件 q_ij ≤ √2/z，"
              "使分子对的可分辨性可以在计算之前预判；其适用边界是态身份必须不变，"
              "C1→C2 还原轴的异常正来自态身份改变。")
    body(doc, "第三，几个“昂贵层”在排序意义上是可省的：几何台阶 std ≈ 0.05–0.08 eV、τ_b ≥ 0.85；"
              "介电层的加密服从 |ΔE|·ε ≈ 2.1 eV 的幂律，ε = 200 时残余仅 19.6 meV（氧化轴 δ_m 的 2.8%），可省的是 ε ≥ 200 的加密点而非连续介质本身；"
              "第一配位壳之后的位移次线性衰减（比值 0.38/0.54，与饱和一致）；"
              "而自洽场多解可以由单格效应量 A_axis 框住（配对严格条件 |d0| ≥ 2 A_axis），靶向后零漏翻转。"
              "把这几条合起来即得到小分子集筛选的最小信息预算。")
    body(doc, "本工作的局限主要在于样本规模、外部标定与判据的证据形态。核心集只有 18 个分子，"
              "τ_b 在 N = 10 子集上的抽样标准差约 0.126，故相邻台阶的小差异不宜过度解读；十个台阶点在统计上并不独立（同一台阶两条轴共享分子），第 3.4.1 节因此同时报告 bootstrap 区间与剔除条件态台阶后的敏感性（见 3.4.1 节）。"
              "液相锚点缺少可复核的重复测量，Gate 1 的绝对标定尚未封闭，只以预注册的 within-series 排序判据降级保留；该判据在本文完成前首次可评一次（n_pairs = 21），结果为 τ_b = 0.4286 < 0.9（3.1.2 节），故状态是“已评估但未闭合”，而不是已经关上；热修正只做了 8 分子的量级抽样，几何盆地判据由 3 个格子的 NEB 精修复核（发现 RMSD 一刀切在 0.02–0.10 Å 带内会误判）；"
              "Li+ 条件态与配位饱和的结论分别在 10 分子与单一代表分子上得到，"
              "其普适性需要更大的配位基元库来检验；真实电解液中的溶剂化结构、物种分布与配位壳层竞争"
              "不在本文范围[11]。这些正是后续工作的方向。")

    body(doc, "适用范围需要在这里再声明一次：本文的全部结论限定在 designated computational target 内部的决策稳定性——"
              "即“换一层物理，候选的排序与选择是否改变”。它不是对候选分子真实电化学性能的排名，也不是对任何真实电解液配方的推荐。"
              "这条边界展开成的 13 条声明、14 个主文数字的溯源与 Gate 1 的现状，一并列在第 6 节。")

def write_core_alignment(doc):
    h1(doc, "5  与预注册方案的对照")
    body(doc, "为避免“事后讲述”，本节把全文结论对照计算前冻结的核心方案，逐项认领判决、核对最小成果判据，"
              "并明确划定本文不声称的范围。所有判决与数值均转自项目已冻结的产物，未新增任何电子结构计算。")
    h2(doc, "5.1  分支认领")
    body(doc, "核心方案预先列出七种可能结局（A–G）。本文的落点是 **B、D、E 三个分支**，并部分触发 G；"
              "A、C、F 被如实否定。认领如下。")
    table_3line(doc,
                ["分支", "判据", "本文判决", "关键证据"],
                [["A 廉价 proxy 已足够", "τ_b(P0, P2) 高、未解析对少、Top-k 重叠高", "NOT SUPPORTED",
                  "P0→P2 氧化轴 τ_b = 0.673、Top-10% 重叠 0.000、f_unresolved = 0.229"],
                 ["B 位移大而排序稳", "位移大但 robust inversion 少，环境只引入整体/家族偏移", "SUPPORTED",
                  "P1→P2 氧化轴位移均值 −2.393 eV、std 0.302 eV、τ_b = 0.895、f_robust_inv = 0.000"],
                 ["C 结构集中的 robust inversion", "出现少量且结构集中的 robust inversion", "NOT OBSERVED",
                  "五台阶 × 两轴 × 两口径共 20 个组合，f_robust_inv 全为 0.000"],
                 ["D 配位引发态身份改变", "[LiM]0 出现 Li 中心/混合还原、断键或 motif 切换", "OBSERVED",
                  "还原态 12 个中 11 个为 Li 中心或混合还原；氧化态 8/12 分子中心、4/12 未找到完整极小点"],
                 ["E 位移学习优于直接学习", "留一家族出外推下 Δ-learning 不劣于 direct", "SUPPORTED（7/8，3 个区间不含 0）",
                  "M·X0 两轴 Δτ_b = +1.342 / +1.222，E·X0+P1 氧化轴 +0.389；例外为 C0→C1 还原轴（−0.143）"],
                 ["F 位移无法由廉价特征学出", "Δ 无法由廉价特征学出", "NOT SUPPORTED",
                  "8 个分组中 7 个 Δτ_b > 0；真正学不动的只有 C0→C1 还原轴（与分支 D 同一根轴）"],
                 ["G 大部分分子对不可判定", "大部分分子对 unresolved，应输出等价类或分层集合", "PARTIALLY SUPPORTED",
                  "C0→C1 还原轴 τ_b = −0.467、f_unresolved = 0.800；P0→P1 还原轴 f_unresolved = 0.733"]],
                "表 8  核心方案情形 A–G 的分支认领（判决与数值转自 outputs/week9/stage10_ladder.json 的 verdicts 字段）",
                "Table 8  Branch claim against the preregistered scenarios A-G")
    body(doc, "有一点必须并读：分支 C 未被观测（f_robust_inv 全为 0）**不等于**排序处处可靠——"
              "真正未解析的是还原轴的 C0→C1（τ_b = −0.467、f_unresolved = 0.800），即分支 G 所描述的情形。"
              "把“没有稳健翻转”误读为“排序稳定”，正是本文反复提醒的那类错误。"
              "反过来，分支 B 则指出一条可省算力的路径：环境台阶是“大位移 + 小离散”，"
              "故可先测试家族依赖的整体修正 P2 = P1 + b_f 是否已经够用，而不必逐分子重算环境层。")
    h2(doc, "5.2  最小成果判据自查")
    body(doc, "核心方案定义了 11 条最小成果判据。逐条核对结果为 10 条 PASS（其中第 7 条为 PASS (negative)，"
              "即“未观测到 robust inversion”本身即为结论）、1 条 PARTIAL。")
    table_3line(doc,
                ["编号", "条目", "状态", "本文落点"],
                [["1", "metadata 严格、化学空间平衡的 core set（18 分子）", "PASS", "2.1"],
                 ["2", "broad cheap pool（40 分子廉价层）", "PASS", "2.1、3.12"],
                 ["3", "P0 / P1 / P2 的一致定义", "PASS", "2.2、2.4"],
                 ["4", "C1 Li+ 配位条件态分析", "PASS", "3.5"],
                 ["5", "外部气相/液相锚点", "PARTIAL", "2.3、3.15；液相锚点排序层已评估但未闭合"],
                 ["6", "不确定性感知的排序比较", "PASS", "2.4、3.1、3.6"],
                 ["7", "稳健翻转的机制分析", "PASS (negative)", "3.5、3.6"],
                 ["8", "随机 / 分组 / 留一家族出三种拆分", "PASS", "3.13"],
                 ["9", "直接学习 vs 位移学习", "PASS", "3.13"],
                 ["10", "特征成本感知的主动学习重放", "PASS", "3.14"],
                 ["11", "昂贵标签预算 vs 决策精度曲线", "PASS", "3.11、3.12、3.14"]],
                "表 9  最小成果判据自查（11 条；判决转自 outputs/week9/stage10_ladder.json 的 minimum_outcome_checklist）",
                "Table 9  Self-audit against the minimum-outcome checklist")
    body(doc, "唯一的 PARTIAL 是第 5 条外部锚点：气相锚点已闭合，液相锚点此前 31 行均为估读值（method = est），无法构成可复核的重复测量，因此 Gate 1 长期以“排序层降级、绝对标定未封闭”的形式保留，预注册的 within-series 判据（要求 ≥ 18 个同系列分子对且 τ_b ≥ 0.9）一度 n_pairs = 0。可行性审计先把这个门槛量化了：≥ 18 对等价于同源序列至少覆盖 7 个核心集分子，而本地文献中最长的同源序列只覆盖 1 个（0 对）。本文完成前引入的一批外部氧化锚点首次使该判据可评，结果为 n_pairs = 21、τ_b = 0.4286 < 0.9，判决排序不一致（3.1.2 节）；而该批数据是外部转录值、其两篇上游原著均不在库、仓库未做独立复核，其中 Okoshi 2015 的题录与引入说明的表述还存在本环境无法裁定的冲突。因此第 5 条仍记为 PARTIAL：它的状态由“无数据”变为“已评估且不一致”，而不是由“未闭合”变为“已闭合”。本文不掩饰这一点，也不把它当作已经关上的门；把溶液相锚点补成可独立复核的 within-series 排序对照，仍是下一阶段优先级最高的外部工作。"
              "此外必须写明预注册阈值在本次锚点规模下的操作特性：n_pairs = 21 时要达到 τ_b ≥ 0.9，需要 C − D ≥ 18.9，"
              "即最多容忍 1 个不一致对；这个 0.9 是为更大的锚点集设计的，在 7 个分子的系列上几乎不可能通过。"
              "它不改变本次判决——bootstrap 给出 P(τ_b ≥ 0.9) = 5.0×10⁻⁵，说明不一致是真实的——"
              "但它必须与判决同时披露，以免把“门槛偏严”误读成“数据支持判据”。")
    h2(doc, "5.3  创新边界：本文不声称什么")
    body(doc, "本文不以 ranking/selection 本身为创新——廉价代理的排序评价已有先例[4]；"
              "也不以“Li+ 配位会改变 redox”为创新——该现象已有计算与机器学习研究[2]。"
              "本文的增量有三：其一，决策可靠性，把 τ_b 与 f_unresolved、f_robust_inv 并列，"
              "区分“值不准”与“分不出”两类误差；其二，要求排序反转必须超出方法不确定度才被承认，"
              "本工作中全部台阶的稳健翻转比例均为 0；其三，最小信息预算，把“复现一个经验证的目标排序”"
              "折算成可提前估算的计算层与昂贵标签数。")
    body(doc, "同样明确的是本文不声称的范围：给出完整的电化学稳定窗口（本文只处理完整物种的一电子热力学代理量，"
              "不含分解网络、动力学与电极界面，见 2.4 节）；完成液相绝对标定（Gate 1 未闭合：其排序层判据已评估但不一致，绝对标定层仍缺，见 3.15 与 5.2 节）；"
              "给出真实配位环境分布或界面结构（属后续阶段）。把这些边界写成明文，"
              "是为了让“未做”与“做错”区分开来。")
    body(doc, "与“不声称什么”相对的，是核心方案 §25.2 要求的“真正新增内容”。本文逐条落点如下："
              "free/coordination 两个状态在概念上严格分离（2.2、3.3.1 节）；检查电子局域与态身份（3.3.1 节、5.6 节表 12）；"
              "robust inversion 必须超过方法不确定度才被承认（2.4、3.4.1 节）；随机插值与留一家族出外推分开报告（3.5.1 节）；"
              "特征成本记账，防止用接近目标层成本的特征证明“低成本预测”（2.7 节）；"
              "外部锚点把 model-to-model 保序与 experimentally anchored accuracy 分开（3.1.1、3.1.2 节）；"
              "主动学习直接针对材料决策，而不是只压低性质 MAE（3.6.3 节）。核心方案 §26 的四条科学意义同样各有落点："
              "从性质预测转向决策可靠性（3.1.1、3.4.1 节）；定量定义“足够的物理真实性”（3.6.1 节最小计算层预算）；"
              "把不确定性本身纳入筛选（2.4、3.4.1 节）；让 negative result 有价值（3.2.5 节漏解、3.1.2 节液相锚点、5.1 节分支 C）。"
              "这两组对应此前只散见正文，在此集中登记，便于与核心方案逐条核对。")
    h2(doc, "5.4  方法依据对照")
    body(doc, "最后把本文使用的方法与阅读清单的第二部分逐条对照，标明哪些是真正用到的、"
              "哪些只作方法学背景——避免用“读过”冒充“用过”。")
    table_3line(doc,
                ["方法学依据", "使用情况", "本文中的落点"],
                [["SMD / CPCM 隐式溶剂化", "已使用", "2.3、3.3（P2 环境臂，乙腈 ε = 35.688）"],
                 ["缩合相缔合熵处理", "仅背景：以配体交换相对量规避平动熵假象", "2.3、2.4"],
                 ["qRRHO 热化学", "仅背景：热修正用谐近似 RRHO，未做准 RRHO 插值", "2.5"],
                 ["GFN2-xTB", "已使用", "2.2、2.3、3.9"],
                 ["方法审计：两种合理 DFT functional 的敏感性", "部分使用：以 GFN2-xTB ↔ r2SCAN-3c 的跨引擎对照与 P0′ ΔSCF 臂替代，未引入第二个 DFT 泛函", "3.1、5.10 节表 16"],
                 ["方法审计：≥2 基组 / 弥散变体", "已使用：T5 弥散对照（r2SCAN 同泛函，def2-mTZVPP / def2-TZVPP / def2-TZVPD 三级；4 分子 × 中性/阴离子）", "2.3、5.10 节表 16"],
                 ["CREST 构象搜索", "仅背景：实际用 RDKit ETKDGv3 + MMFF + GFN2-xTB 弛豫", "2.3"],
                 ["电解液物种分布 / MD", "仅背景：只做单一 [LiM]+ 条件态", "3.5、后续阶段"],
                 ["溶剂化结构", "间接使用：[Li(M)2]+ 微溶剂化簇", "3.5、3.9"],
                 ["高斯过程回归", "已使用", "3.13"],
                 ["主动学习", "已使用", "3.14"],
                 ["多保真学习", "仅背景：位移学习形式相同，但环境扰动不是数值保真度校正", "2.7、3.13"],
                 ["bootstrap", "已使用", "2.5、3.6、3.13"]],
                "表 10  方法依据与阅读清单 Part II 的对照（标记取自项目对真实使用证据的核查）",
                "Table 10  Method provenance against reading-list Part II")
    h2(doc, "5.5  阶段映射：从预注册 Stage 到本文台阶")
    body(doc, "项目内部的阶段编号（Stage 0–9）与本文的台阶编号是两套语言，外部读者无法自动对应。"
              "表 11 给出逐条映射，全部经产物与文档双向确证。")
    table_3line(doc,
                ["Stage", "实际计算内容", "对应本文台阶"],
                [["0", "冻结目标量方向、Top-k 比例、δ 规则与参考配体", "不产生台阶（定义冻结层）"],
                 ["1", "12 分子方法审计与外部气相锚点", "方法审计（不产生台阶）"],
                 ["2", "broad cheap pool 的 P0 廉价层", "P0 起点臂"],
                 ["3", "核心集 r2SCAN-3c 气相垂直量（P1）与几何台阶", "P0→P1、G1→G2"],
                 ["4", "固定背景连续介质（CPCM/SMD，乙腈）", "P1→P2"],
                 ["5", "Li+ 配位条件态 [LiM]+", "C0→C1"],
                 ["6", "不确定性感知的排序分析（表 3、表 4）", "不产生新台阶（统计层）"],
                 ["7", "特征成本分级、模型阶梯、三拆分、直接 vs 位移学习", "不产生台阶（3.5.1 节）"],
                 ["8", "主动学习重放、四采集函数", "不产生台阶（3.6.3 节）"],
                 ["9", "[Li(M)2]+ 显式微溶剂化壳层", "C1→C2"]],
                "表 11  预注册 Stage 0–9 与本文台阶的映射（10 条全部经产物与文档双向确证）",
                "Table 11  Mapping from preregistered stages to the rungs used here")
    h2(doc, "5.6  异常状态台账")
    body(doc, "审稿人核对数字时最先要的是“哪些计算没成功、失败率多少”。表 12 汇总全部真实存在的 QC 字段，"
              "只统计产物里确实记录的项，未做任何估算。")
    table_3line(doc,
                ["状态/异常", "发生数/总数", "发生率", "本文处置"],
                [["字面 scf_failed（P1 核心）", "0/54", "0%", "与 3.2.5 节的“多解/漏解”是两件事，不矛盾"],
                 ["自洽场多解：默认初猜漏解", "32/360", "8.9%", "3.2.5 节全量报告（328 一致、32 更低、0 更高，最大 −0.286 eV）"],
                 ["自洽场多解：第二解弛豫后仍更低", "5/37", "13.5%", "本节新增披露"],
                 ["自洽场多解：跨引擎（xTB）仍更低", "15/37", "40.5%", "本节新增披露（跨方法存活率明显更高）"],
                 ["漏解引起的分子对翻转", "19/660（氧化）、21/660（还原）", "2.9% / 3.2%", "3.2.5 节表 5；靶向后漏 0"],
                 ["气相阴离子不束缚（unbound_anion）", "18/18", "100%", "2.3、3.2.1 节；还原轴结论只以 P2/C1 为载体"],
                 ["配位 motif 改变（motif_switch）", "32/46", "69.6%", "本节新增披露（配位枚举阶段）"],
                 ["优化后失去完整极小点", "C1 态身份 4/12；C1 扫描 4/92；枚举 1/46", "33.3% / 4.3% / 2.2%", "与 3.3.1 节态身份分析同源，本节补出计数"],
                 ["驻点存在虚频", "T2 几何 2/12；C1 条件态 1/10", "16.7% / 10.0%", "EC 的 [LiEC]+ 在 −80.4 cm⁻¹ 有虚频，其 C0→C1 位移属鞍点测量，已写入局限"],
                 ["几何优化失败 / 作业执行失败", "1/92", "1.1%", "SL/m1 双阳离子 ORCA 超时，已如实计入"],
                 ["态身份冲突 / 自旋污染 / 电子数不一致", "0/92、0/54、0/92", "0%", "三项全为 0"],
                 ["P2 弛豫覆盖的过程警示", "1/1", "100%", "非计数型异常：严格 P2 臂的弛豫覆盖为 0，已登记"],
                 ["交付层自动断言", "372/372", "100%", "含文件 SHA256 与现场取数核对，0 条失败"],
                 ["外部锚点未经仓库独立复核", "14/14（氧化）、3/3（还原旁证）", "100%",
                  "3.1.2 节；全部为转录值（transcription_only），原著不在库且本环境无网络，另有一处与 Crossref 核验不一致的归属表述"]],
                "表 12  异常状态台账（只统计产物中真实存在的 QC 字段）",
                "Table 12  QC/exception ledger")
    body(doc, "表 12 中有 14 项在早先的文稿里从未出现，其中包括与本文解释直接相关者："
              "气相阴离子不束缚是 18/18 的结构性事实（正因如此，还原轴的决策结论只能以 P2/C1 为载体）；"
              "而 C1 条件态存在 1/10 的虚频、以及 4/12 的“优化后失去完整极小点”，"
              "说明 C0→C1 的还原定位移在部分分子上量的是鞍点而非极小点——这与 3.3.1 节判定的态身份改变"
              "是同一现象的两个侧面，也是我们把该台阶的 τ_b 只用于说明“配位改写排序”、"
              "而不解释为精度改善的原因。把这些计数补出来，是为了让读者不必从原始日志里自行发现它们。")
    h2(doc, "5.7  第一阶段明确不做的四件事")
    body(doc, "把“没做”写成明文，比让它留在读者心里更好。以下四项在第一阶段明确不做，理由是核心方案自己写明的边界纪律，"
              "而不是能力不足。")
    table_3line(doc,
                ["条款", "是否做", "为什么不做"],
                [["真实配位 species population（p_s）", "否",
                  "只做 1:1 条件态与同配体、同化学计量的 1:2 校核；核心方案自己写明 population 属 Phase II/III，不得用强制 1:1 配合物冒充"],
                 ["多目标 Pareto / 综合电解液分数", "否",
                  "核心方案禁止构造 S = Σw_iP_i 一类武断综合分数；本文并列报告氧化/还原两轴，结合能差只作机制描述符，不设为最大化目标"],
                 ["阈值型决策误差", "否（记为不适用）",
                  "该量只在阈值来自外部设计要求或事先定义的工程标准时才有意义，且不允许看完数据后选阈值；本文无此外部阈值来源"],
                 ["电极界面 / EDL 参考层（R_env）", "否",
                  "属 Phase IV；项目锚点目录中没有 R_env 数值，本文对 Yang 等的界面趋势只作定性对照"]],
                "表 13  第一阶段明确不做的四项及其理由",
                "Table 13  Four items deliberately out of scope in Phase I")
    h2(doc, "5.8  核心方案建议图的对照")
    body(doc, "核心方案 §24 建议了 7 张核心图。本文按实际证据链把它们展成 22 张；表 14 给出逐条对照，"
              "说明每条建议落在本文何处、以及为何拆分或合并。对照的目的不是图数一致，"
              "而是保证核心方案提出的每一个证据维度都有对应的可视化，且每张图都能追溯到具体产物。")
    table_3line(doc,
                ["核心方案 §24 建议", "本文对应图", "拆分/合并说明"],
                [["Figure 1：Two-axis model hierarchy + reference layer", "图 1、图 2、图 3",
                  "图 1 给出方法—环境—几何的流水线（一维路径），图 2 给出二维层级（方法层级 × 条件态层级）与独立的外部参考层；core/broad 的化学空间覆盖见图 3"],
                 ["Figure 2：External validation and uncertainty audit", "图 4、图 7、图 10、图 20",
                  "外部锚点的值误差—排序误差分离在图 4，环境层位移与不确定带在图 7，十级台阶总判在图 10，液相锚点排序检验在图 20"],
                 ["Figure 3：Uncertainty-aware rank stability matrix", "图 10、图 11",
                  "稳定性矩阵的统计内容在图 10；其闭式来源、临界斜率与分辨率几何在图 11"],
                 ["Figure 4：Robust rank-flow map", "图 5、图 6",
                  "本条按 negative result 登记：20 个（台阶 × 轴 × 口径）组合上 f_robust_inv 全为 0，本文未观测到任何可画的超阈值稳健翻转，故以未过滤的两轴位次迁移（图 5 氧化轴、图 6 还原轴）作语义替代，并在 5.1 节分支 C 与 5.10 节表 16 如实登记；图 6 的 Koopmans 还原轴是定性失效，不作为机制发现"],
                 ["Figure 5：Mechanisms of coordination-induced inversion", "图 9、图 14、图 22",
                  "图 9 给 C0→C1 的态身份与决策量，图 14 给第三个配位点的饱和证据，图 22 给配位位移与分子内描述符标签的相关与分层（3.3.4 节）"],
                 ["Figure 6：Direct vs Δ-learning under extrapolation", "图 17",
                  "按预注册要求同时给出随机/分组/留一家族出三种拆分与配对 Δτ_b 区间"],
                 ["Figure 7：Minimal expensive-information budget", "图 13、图 16、图 18、图 19",
                  "拆成三层预算：图 13 为漏解靶向的重算量，图 16 为 broad 池的升级子集，图 18 为昂贵标签数，图 19 把三类预算合成一条决策路径"]],
                "表 14  核心方案 §24 建议的 7 张核心图与本文配图的对照（本文共 22 张图）",
                "Table 14  Mapping from the seven recommended core figures to those delivered here")


    h2(doc, "5.9  与核心方案规模的显式偏差")
    body(doc, "核心方案在若干处给出了期望规模。本文的实际规模在多个维度上低于这些期望，"
              "而这些偏差此前只分散在各周报告里，论文正文没有集中登记；审稿人核对规模时需要一个单一入口。"
              "本节把全部偏差逐条列出，并把“主动取舍”与“真实未闭合”两类分开标注，表中每行的实得值都可回溯到具体产物。")
    table_3line(doc,
                ["核心方案期望（行号按 v2）", "本文实得", "性质与依据"],
                [["§5.1 core paired set 建议 N ≈ 60–100（L350–354）", "18",
                  "主动取舍：按 family 覆盖选取 18 个分子（其中 2–3 个为机理对照），记录见 config/scientific_definitions.yaml:269 与 data/metadata/core_set.csv"],
                 ["§5.1 broad cheap pool 建议 N ≈ 300–1000（L356–366）", "40",
                  "主动取舍：廉价层用于化学空间覆盖与预算演示，40 个分子覆盖 8 个家族并外扩至亚硫酸酯、磺内酯与硅氧烷（data/metadata/broad_pool.csv）"],
                 ["§13.3 基本统计力需要 60–100 core points（L915–919）", "18",
                  "主动取舍 + 显式补救：不以大样本统计力为目标，凡小样本排序结论一律给出 bootstrap 区间、精确置换检验与留一家族出（3.4.1、3.5.1、3.1.2 节）"],
                 ["§15.2 溶液锚点建议同系列 10–20 个分子（L1010–1021）", "7（核心集）/ 14（全表）",
                  "部分满足：本文完成前引入的氧化锚点系列覆盖 7 个核心集分子，恰好越过预注册 n_pairs ≥ 18 的门槛但未达 10–20 上限，且属未经仓库独立复核的转录值；其中 EC 一行按熔点判据标为条件待核实（3.1.2 节）"],
                 ["§7.3 单点建议 range-separated hybrid（如 ωB97X-D4）与阴离子专用 diffuse protocol（L525–536）", "未做",
                  "主动取舍：全程使用 r2SCAN-3c 单点；阴离子是否束缚改以 unbound_anion 判据直接检验（气相 18/18 不束缚），未引入 diffuse 基组协议"],
                 ["§29 执行时间框架建议 8–12 周（L1690–1718）", "25 周",
                  "主动扩张：范围在 Gate 1 可行性审计、漏解靶向、热修正抽样与 NEB 精修等处扩展；扩出的部分均单独报告，不以时间达标为目标"],
                 ["§21 计算预算与执行规模：要求任务数公式与 CPU-core-hours 口径（L1305–1340）", "作业数可核，机时不可核",
                   "部分满足：已发布计算作业工件 1657 个（ORCA 1485 + xTB 172，排除 scratch/smoke）可逐目录回溯；但仓库未记录 CPU-time 与 nprocs × wall，故 §21 要求的 median / 90 百分位 CPU-core-hours 记为 not_available_in_repo（台账见 docs/44）"],
                 ["§19 Gate 1：态身份 / SCF / 气相锚点 / 溶液趋势均无系统性失败（L1160–1162）", "未闭合",
                  "真实未闭合：前三项通过；溶液趋势一项在排序层首次可评即判不一致（τ_b = 0.4286，3.1.2 节），绝对标定层仍缺（5.2 节）"]],
                "表 15  与核心方案期望规模的显式偏差（实得值均可回溯到具体产物；主动取舍与真实未闭合分开标注）",
                "Table 15  Explicit deviations from the core-plan expected scale")
    body(doc, "把这张表放在这里的理由与 5.3、5.7 两节相同：核心方案的期望规模是它自己的设计选择，而不是本文的验收标准；"
              "但如果不显式登记，读者只能从周报里自行拼出这些偏差，那既不透明，也会让“结论是否依赖于核心集选取”这个问题停留在猜测层面。"
              "需要强调，八行里只有最后一行是真实未闭合的科学判据，其余七行都是主动取舍或部分满足；两类必须分开读，"
              "否则会低估本文已经闭合的部分、也会高估本文已经完成的范围。")
    h2(doc, "5.10  核心方案结构性要求的落点")
    body(doc, "前四节把判决、判据与方法依据逐条对表。核心方案另有四条不属“规模”而属“结构性”的要求——方法审计的维度、"
              "显式微溶剂化的定位、后续升级路线以及可追溯数据结构。它们此前散在各周报告里，表 16 给出单一入口；"
              "其中 §28 的推荐目录与仓库实际层级不同构，表 17 给出等价映射。")
    table_3line(doc,
                ["核心方案要求（§ + 行号）", "本文落点", "判定与说明"],
                [["§7.1 method audit：约 8–10 benchmark，含两种合理 DFT functional、≥2 基组/弥散变体、continuum 敏感性、气相锚点与溶液锚点（L479–503）",
                  "2.3、3.1、5.10 节；表 10",
                  "部分满足：审计分子集 12 个；continuum 以 CPCM（ε = 5/10/20/40）与固定 SMD 溶剂两级覆盖；气相锚点 12 分子闭合；基组维度由 T5 弥散对照（r2SCAN 同泛函，def2-mTZVPP / def2-TZVPP / def2-TZVPD，4 分子 × 中性/阴离子）满足；但“两种 DFT functional”未引入第二个 DFT 泛函，改以 GFN2-xTB ↔ r2SCAN-3c 的跨引擎对照与 P0′ ΔSCF 臂替代（已在表 15 登记）"],
                 ["§17.1 显式微溶剂化只做 targeted check：约 8–12 个候选，覆盖 ranking-stable / robust inversion / high-uncertainty / 各家族代表，且只用相同化学计量（L1076–1085）",
                  "3.3.2 节、3.3.1 节；outputs/week8/stage9_*",
                  "部分满足：实得 11 个分子 × 12 个配位基元，化学计量只有 1:2 的 [Li(M)2]+ 一种；8 个结构家族全部有代表（满足“各家族代表”一类）；high-uncertainty 一类由 1:1→1:2 的 f_unresolved 上升指认（primary_m1 氧化轴 0.133→0.267）；robust inversion 一类为空——全项目 f_robust_inv = 0，无分子属于该类，属现象未观测而非抽样遗漏；未构造其它化学计量"],
                 ["§27 后续升级路线 Phase II（真实配位 population）/ III（显式液体采样）/ IV（电极界面与 EDL）（L1612–1645）",
                  "5.7 节表 13",
                  "已满足（声明式登记）：表 13 第 1 行同时覆盖 Phase II 与 Phase III（配位 population 属 II、MD/AIMD/MLFF 属 III），第 4 行 R_env 对应 Phase IV；本文只交付 Phase I"],
                 ["§28 推荐目录骨架与 11 项可追溯字段（L1647–1688）",
                  "2.6 节；config/scientific_definitions.yaml 的 provenance_requirements；表 17",
                  "部分满足：11 项可追溯字段与 14 项机器可读记录已冻结在科学定义配置；推荐目录与仓库实际层级不同构，等价映射见表 17"]],
                "表 16  核心方案结构性要求（方法审计 / 微溶剂化定位 / 后续路线 / 数据结构）与本文落点",
                "Table 16  Structural requirements of the core plan and their landing points here")
    body(doc, "把这几条与规模偏差分开列的原因，是它们的性质不同：规模偏差（表 15）回答“做了多大”，"
              "结构性要求（表 16）回答“做的方式是否与冻结方案一致”。四条里两条部分满足（审计的泛函维度、微溶剂化化学计量），"
              "两条为声明式登记；没有任何一条改变了正文的判决。")
    body(doc, "§28 的推荐目录是为“每个最终数值都可按图索骥”设计的。本文没有照搬它的物理层级，"
              "但保持了等价的可追溯性：表 17 把推荐骨架的每个槽位映射到仓库实际路径，并注明该槽位由哪个阶段的产物承载。")
    table_3line(doc,
                ["§28 推荐骨架", "仓库实际路径", "承载阶段/说明"],
                [["metadata/", "data/metadata/", "core_set.csv、broad_pool.csv；v2 §5.2 的六项扩展字段在 core_set_metadata_ext.csv（2.1 节）"],
                 ["structures/（neutral、charged、li_motifs）", "structures/（conformers、li_motifs、microsolvation）", "G1 几何与配位基元、微溶剂化壳层"],
                 ["P0_cheap_proxy/", "outputs/week3/、outputs/week4/p0_core_set.csv", "Stage 2 broad 池与 core 的 P0 层"],
                 ["P1_gas_dft/", "outputs/week4/（p1_core_set*、p1_decision_stability*）", "Stage 3 气相 r2SCAN-3c 垂直量"],
                 ["P2_fixed_continuum/", "outputs/week4/（p2_*）、outputs/week22/dielectric_limit.json", "Stage 4 固定背景连续介质与介电扫描"],
                 ["C1_li_conditional/", "outputs/week5/（c1_*）", "Stage 5 [LiM]+ 条件态"],
                 ["C2_microsolvation_optional/", "outputs/week8/（stage9_*）", "Stage 9 [Li(M)2]+ 微溶剂化校核"],
                 ["external_reference/（gas、solution）", "data/anchors/（gas_phase_anchors.csv、solution_redox_anchors.csv、ue1994_okoshi2015_oxidation.csv）", "3.1.1、3.1.2 节的外部锚点"],
                 ["analysis/uncertainty/", "src/electrolyte_ranking/uncertainty.py；outputs/week4/（delta_m）", "δ_m 与 σ 的推导"],
                 ["analysis/ranking/、analysis/inversion/", "src/electrolyte_ranking/ranking.py；outputs/week9/stage10_ladder.json", "排序与稳健翻转判据"],
                 ["analysis/delta_learning/、analysis/active_learning/", "outputs/week7/（stage7_ml、stage8_al）；outputs/week24_corealign/（ml_direct_vs_shift）", "3.5.1、3.6.3 节"],
                 ["results/", "outputs/figures/、docs/、成果输出/", "图件 manifest、周报告与交付镜像"]],
                "表 17  核心方案 §28 推荐目录骨架与本文仓库实际路径的等价映射",
                "Table 17  Mapping of the core-plan §28 directory skeleton to the actual repository layout")
    body(doc, "映射的原则是不新增第二套真源：上表每一行都指向仓库中既有的、已冻结或被 --check 覆盖的产物，"
              "而不是为对齐目录而另建副本。11 项可追溯字段（molecule / motif ID、几何、电荷与自旋、软件与版本、"
              "方法与基组、溶剂模型、温度与标准态、原始输出、QC 状态、态身份标签）逐作业落盘，"
              "由 src/electrolyte_ranking/provenance.py 与各周交付的 --check 断言共同保证。")

ACK_TEXT = (
    "感谢课题组在计算资源与讨论上的支持。本工作中的电子结构计算使用 ORCA 与 xtb 完成，"
    "数据处理、判据验证与图表由项目内脚本自动生成并归档。"
)

REFS = [
    "[1] Borodin, O. Curr. Opin. Electrochem. 2019, 13, 86–93.",
    "[2] Yang, D.; Zhang, P.; Xiong, Y.; Wang, T.; Wang, Q.; Zhang, C.; Wang, L.; Lu, S.; Liu, T. C.; Qi, S.; et al. Mater. Today Energy 2025, 54, 102121.",
    "[3] Marenich, A. V.; Ho, J.; Coote, M. L.; Cramer, C. J.; Truhlar, D. G. Phys. Chem. Chem. Phys. 2014, 16 (29), 15068–15106.",
    "[4] Husch, T.; Yilmazer, N. D.; Balducci, A.; Korth, M. Phys. Chem. Chem. Phys. 2015, 17 (5), 3394–3401.",
    "[5] Peljo, P.; Girault, H. H. Energy Environ. Sci. 2018, 11 (9), 2306–2309.",
    "[6] Itkis, D.; Cavallo, L.; Yashina, L. V.; Minenkov, Y. Phys. Chem. Chem. Phys. 2021, 23 (30), 16077–16088.",
    "[7] Pracht, P.; Grimme, S.; Bannwarth, C.; Bohle, F.; Ehlert, S.; Feldmann, G.; Gorges, J.; Müller, M.; Neudecker, T.; Plett, C.; et al. J. Chem. Phys. 2024, 160 (11), 114110.",
    "[8] Rebollar-Zepeda, A.; Carreon-Gonzalez, M.; Muñoz-Rugeles, L.; Alvarez-Idaboy, J. R. J. Chem. Theory Comput. 2026, 22 (13), 6367–6376.",
    "[9] Bannwarth, C.; Ehlert, S.; Grimme, S. J. Chem. Theory Comput. 2019, 15 (3), 1652–1671.",
    "[10] Grimme, S. Chem. Eur. J. 2012, 18 (32), 9955–9964.",
    "[11] Yao, N.; Chen, X.; Fu, Z.-H.; Zhang, Q. Chem. Rev. 2022, 122 (12), 10970–11021.",
    "[12] Marenich, A. V.; Cramer, C. J.; Truhlar, D. G. J. Phys. Chem. B 2009, 113 (18), 6378–6396.",
    "[13] Cheng, H.; Sun, Q.; Li, L.; Zou, Y.; Wang, Y.; Cai, T.; Zhao, F.; Liu, G.; Ma, Z.; Wahyudi, W.; et al. ACS Energy Lett. 2022, 7 (1), 490–513.",
    "[14] Neese, F.; Wennmohs, F.; Becker, U.; Riplinger, C. J. Chem. Phys. 2020, 152 (22), 224108.",
    "[15] Neese, F. WIREs Comput. Mol. Sci. 2022, 12 (5), e1606.",
    "[16] Grimme, S.; Hansen, A.; Ehlert, S.; Mewes, J.-M. J. Chem. Phys. 2021, 154, 064103.",
    "[17] Furness, J. W.; Kaplan, A. D.; Ning, J.; Perdew, J. P.; Sun, J. J. Phys. Chem. Lett. 2020, 11, 8208–8215.",
    "[18] Barone, V.; Cossi, M. J. Phys. Chem. A 1998, 102, 1995–2001.",
]


BOUNDARY_ROWS = [
    ["G01", "Gate 1 = NOT CLOSED 且 NOT CLOSABLE（ordering_disagrees，τ_b = 0.4286）：排序层判据已评估但未闭合，"
            "绝对标定层仍未封闭，本文既不跳过它、也不把它强行关闭。", "3.1.2 / 5.2 / 6.2"],
    ["G02", "NOT CLOSABLE ≠ NO SUCH DATA EXIST ANYWHERE：这是一个可被证伪的负结果，而不是“数据不存在”；"
            "补一份同装置同判据、覆盖 ≥ 7 个核心集溶剂的电位表仍然是优先级最高的外部工作。", "3.1.2 / 5.2 / 6.2"],
    ["G03", "本文的全部结论限定在 designated computational target 内部的决策稳定性，不构成对真实电解液体系的实验有效性声明。",
            "摘要 / 4 结语 / 6.2"],
    ["G04", "f_robust_inv = 0 是**定义性**结果（定理 T6a/T6b），不是经验发现；报告它时必须同时给出 σ 约定与分母。",
            "3.4.1 / 6.2 / S2"],
    ["G05", "自指性：现有数据无法独立估计两支臂的互不确定度，因此不得把“零反转”读成经验结论——它只说明现有证据不能识别反转。",
            "3.4.1 / 6.2"],
    ["G06", "family-held-out 的主动学习曲线**不可用**（冻结 replay 只有池内插值），所有预算数字都是池内口径。", "3.6.3 / 6.2"],
    ["G07", "池内端点 τ_b = 1.0 是构造性自检端点，不是成绩；已在全部统计中剔除。", "3.6.3 / 6.2"],
    ["G08", "C1 还原态身份分层后主排序样本塌到 n = 1（还原轴在 C1 下无定义），这不是误差而是定义域变化。", "3.3.1 / 6.2"],
    ["G09", "位移学习的 6/8（冻结逐格口径）不是“普遍更好”，两个反例必须列出。", "3.5.1 / 6.2"],
    ["G10", "主动学习的成功标准是内部操作性标准，未经外部校准，不能外推为真实筛选所需的高成本计算数量。", "3.6.3 / 6.2"],
    ["G11", "within-series 表的 14 行锚点 provenance 全部为 transcription-only，未回溯到原始测量。", "3.1.2 / 6.2"],
    ["G12", "核心集只有 18 个分子（条件态 10 个），20 次重复的 2.5/97.5 百分位本身很粗，小样本结论不得外推。", "2.1 / 3.6.3 / 6.2"],
    ["G13", "全程零新增电子结构计算：不新增 ORCA/xTB 作业，结论只对已有冻结数据成立。", "2.3 / 3.1.2 / 6.2"],
]

LINEAGE_ROWS = [
    ["L01", "Gate 1 排序一致性 Kendall τ_b", "0.4286", "outputs/week25/series_rel_ordering_check.json"],
    ["L02", "Gate 1 within-series 可用分子对数", "21", "outputs/week25/series_rel_ordering_check.json"],
    ["L03", "Gate 1 一致 / 不一致分子对数", "15 / 6", "outputs/week25/series_rel_ordering_check.json"],
    ["L04", "溶液相 anchor 仍为估读值（est）的行数", "31", "outputs/week2/solution_anchor_audit.json"],
    ["L05", "P0→P1v 氧化轴 τ_b", "0.6732", "outputs/gate1/gate1_dual_track.json"],
    ["L06", "P0→P1v 氧化轴 UNRESOLVED 分子对数", "70", "outputs/gate1/gate1_dual_track.json"],
    ["L07", "P1v 与 P1a 绝热阶梯的分子数", "12", "outputs/phase2_p1a/p1v_vs_p1a.json"],
    ["L08", "P1v 与 P1a 的 τ_b", "0.7879", "outputs/phase2_p1a/p1v_vs_p1a.json"],
    ["L09", "P1v 与 P1a 的稳健翻转（robust inversion）分子对数", "2", "outputs/phase2_p1a/p1v_vs_p1a.json"],
    ["L10", "反转不可能阈值 z* = 1/√2", "0.7071068", "outputs/week27/estimator_circularity.json"],
    ["L11", "双方解析子集内的最大反向分子对数（T6b）", "0", "outputs/week27/estimator_circularity.json"],
    ["L12", "WP5 与 Stage 7 对账的 OOF 预测行数", "288", "outputs/week32/wp5_delta_learning.json"],
    ["L13", "主动学习曲线的单元格数", "296", "outputs/week7/stage8_al_results.json"],
    ["L14", "主动学习逐 repeat 记录数", "5920", "outputs/week7/stage8_al_results.json"],
    ["L15", "WP2 主表行数", "299", "outputs/week29/wp2_physics_response.json"],
    ["L16", "WP4 主表行数", "918", "outputs/week31/wp4_decision_identifiability.json"],
]


def write_boundaries(doc):
    h1(doc, "6  结论边界、数字溯源与局限")
    body(doc, "本文把负结果与适用边界放在与结果同等的位置。本节先给出主文 14 个关键数字的溯源，再逐条写出 13 条结论边界，"
              "最后复述 Gate 1 的现状。任何一条边界都不是附注：它们与对应的数字同权，删掉数字或删掉边界都会使结论失效。")
    h2(doc, "6.1  主文关键数字的溯源")
    body(doc, "下表把主文中出现的关键数字逐条指回仓库中冻结的产物。完整记录（含每个来源文件的 sha256 与复现命令）"
              "见 outputs/week35/paper_number_lineage.csv，共 16 条；下表列出其中进入主文正文的 14 条。")
    table_3line(doc,
                ["编号", "量", "值", "来源（仓库路径）"],
                LINEAGE_ROWS,
                "表 18  主文关键数字的溯源（sha256 与复现命令见 outputs/week35/paper_number_lineage.csv）",
                "Table 18  Provenance of the key numbers in the main text")
    h2(doc, "6.2  结论边界与局限（13 条）")
    body(doc, "以下 13 条是本文必须写出的边界。它们的顺序不对应重要性，但每一条都限定了某个结论的适用范围；"
              "其中 G01、G02、G04、G05、G11 直接决定读者能否正确复现本文的判断。")
    table_3line(doc,
                ["编号", "边界声明", "落点"],
                BOUNDARY_ROWS,
                "表 19  本文必须写出的 13 条结论边界",
                "Table 19  The thirteen boundary statements the paper must state")
    h2(doc, "6.3  Gate 1 的现状")
    body(doc, "Gate 1 的现状是 **NOT CLOSED 且 NOT CLOSABLE**：8 条预注册关闭条件中有 3 条未达成，"
              "决定性的一条是 within-series 排序一致性 τ_b = 0.4286 < 0.90（要求 ≥ 0.9）。"
              "同时必须一起发布措辞边界：NOT CLOSABLE 不等于 NO SUCH DATA EXIST ANYWHERE——"
              "它是可被证伪的负结果，而不是“不存在这样的数据”。此外，没有任何一行 anchor 被删除："
              "31 行估读值仍然是估读值，它们不因为“不一致”而被移除。全程零新增电子结构计算、零阈值改动、零数据剔除。")


def write_supplementary(doc):
    h1(doc, "7  补充材料")
    body(doc, "本节收容两项方法审计图件与两条定义性定理。它们不进主图，但主文的结论 G04、G05 与 3.4.1 节依赖它们，"
              "因此必须随文发表。")
    h2(doc, "7.1  S2.1  指标稳健性与排序可识别性")
    body(doc, "该图检验“排序结论对决策口径是否稳健”：在政策带宽度、并列处理规则（f_tie）、可分辨的层数以及近临界分子对"
              "四个方向上来回移动口径，观察 τ_b 与未解析比例是否随之翻转。它与主图 2（外部锚点与方法/不确定度审计）"
              "共同支撑“目标有多可信”这一问。")
    figure(doc, "F57_metric_robustness.png",
           "图 23  指标稳健性与排序可识别性（补充材料 S2.1）：政策带 / f_tie / 可分层层数 / 近临界分子对四个方向的口径敏感性，"
           "对应主图 2 的局部面板", 6.3)
    h2(doc, "7.2  S2.2  模型层独立性 / 信息增益审计")
    body(doc, "该图回答一个方法学质疑：那些台阶会不会只是同一信号的再编码。它并排给出位移的离散度、相邻台阶之间的 |Pearson| "
              "以及逐级 τ_b，用来证明“阶梯是分解”而不是“同一信号换了名字”。这是主图 2 中方法审计面板的支撑推导。")
    figure(doc, "F58_layer_independence.png",
           "图 24  模型层独立性与信息增益审计（补充材料 S2.2）：位移离散度、台阶间 |Pearson| 与逐级 τ_b，"
           "支撑主图 2 的方法审计面板", 6.3)
    h2(doc, "7.3  S2.3  定理 T6a：反转不可能")
    body(doc, "定理 T6a。设两支估计臂给出同一分子对 (i, j) 的两个位移量，且各自的不确定度按等权合成，"
              "则稳健反转只在 z ≤ 1/√2 时才可能发生。证明是代数性的：反向判定的条件要求 |ΔP_ij| ≥ z·σ_ij 在两个臂上同时成立，"
              "而 σ_ij = |ΔP_A(i, j) − ΔP_B(i, j)| / √2；把两式相除，可解出 z 的上界恰为 1/√2（0.7071067811865475）。"
              "本文冻结的两档灵敏度 z = 1.0 与 1.96 都大于该上界，因此 f_robust_inv ≡ 0 是这条不等式的推论。"
              "逐块验证显示冻结数据中不存在任何 z 允许反转的格子。")
    h2(doc, "7.4  S2.4  定理 T6b：不可认证的分歧")
    body(doc, "定理 T6b。在上述判据下，双方都解析的子集中反向分子对数恒为 0——本文的流程从不认证任何分歧。"
              "8 个冻结块（4 级台阶 × 2 轴）上，双方解析子集在 z = 1 时为 83、44、125、94、84、40（／153）与 30、4（／45），"
              "在 z = 1.96 时为 61、33、102、67、60、32（／153）与 24、4（／45）；无论分母取哪一个，反向分子对数都是 0"
              "（max_n_discordant_both = 0）。这正是 G05 说“不得把零反转读成经验结论”的原因：该流水线在设计上就无法认证分歧，"
              "它的零值是定义性的。")
    body(doc, "两条定理的逐块计数、代数验证（σ 恒等式最大偏差 8.9×10⁻¹⁶ eV 与 4.4×10⁻¹⁶ eV）以及 8 个块的完整台账，"
              "见 outputs/week27/estimator_circularity.json。")

def main():
    doc = setup_document()
    title_block(doc)
    abstract_block(doc, CN_ABS, CN_KW, CN_CLC)
    en_block(doc, TITLE_EN, "", "College of Chemistry and Molecular Sciences, Wuhan University, Wuhan 430072, China",
             EN_ABS, EN_KW)
    write_intro(doc)
    write_methods(doc)
    write_results(doc)
    write_conclusion(doc)
    write_core_alignment(doc)
    write_boundaries(doc)
    write_supplementary(doc)
    acknowledgment(doc, ACK_TEXT)
    references(doc, REFS)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    doc.save(OUT)
    print("saved:", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()
