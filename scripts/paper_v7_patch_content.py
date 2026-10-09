# -*- coding: utf-8 -*-
"""【一次性溯源脚本】按 outputs/week35/paper_build_handoff.json 的 required_edits 给论文正文补内容。

它已经执行过一次；对 v7 源码重复执行会因锚点不唯一而报错，因此只作改动溯源保留。
"""
import io, sys

PATH = r"E:\Claude Code\电解液溶剂-HB\论文\build_paper_docx.py"

P_DESIGNATED = '''    body(doc, "术语约定：本文把这条阶梯上的每一级统称为 designated computational target（指定计算目标）——它由计算定义冻结，"
              "逐级升级只改变被指定的物理内容，并不使任何一级自动获得额外的有效性；把用于外部核对的序列统称为 "
              "designated reference model（指定参考模型）——它给出外部参考条件与条件匹配的对照，其自身的有效性需另行独立复核。"
              "全文按这两个术语书写，不使用任何“已验证目标”式的表述。")
'''

P_SIGMA = '''    body(doc, "这条零值必须连同它的定义一起读，否则会被读成经验发现。本文的稳健翻转判据完整定义为：以两支冻结估计臂逐对求 "
              "σ_ij = |ΔP_A(i, j) − ΔP_B(i, j)| / √2——分母 √2 来自两支臂的逐分子不确定度按等权合成，"
              "逐分子样本标准差取 ddof = 1；分子对 (i, j) 被判为解析，当且仅当 |ΔP_ij| ≥ z·σ_ij 且 |ΔP_ij| > 0；"
              "ROBUST_INVERSION 要求两侧同时解析且位移符号相反。因此 f_robust_inv 的分母不是全部分子对，"
              "而是“两侧都解析”的子集 N_resolved_both：在本文 8 个冻结块（4 级台阶 × 2 轴）上，z = 1 时它为 "
              "83、44、125、94、84、40（对／153 对）与 30、4（对／45 对），z = 1.96 时进一步缩到 61、33、102、67、60、32 与 24、4。"
              "分母随判据收紧而缩小这一点，必须与零值同时报告。")
    body(doc, "两个定理界定了这个零值的位置。定理 T6a（反转不可能）：在等权双支臂判据下，稳健反转只在 z ≤ 1/√2 时才有可能，"
              "而本文冻结的两档 z（1.0 与 1.96）都大于该阈值（z* = 0.7071067811865475）。因此 f_robust_inv ≡ 0 是一个**定义性**结果，"
              "是闭式判据的代数推论，而不是关于本体系的经验发现。定理 T6b（不可认证的分歧）：在每一个冻结块、每一档 z 上，"
              "双方解析子集内的反向分子对数都是 0（max_n_discordant_both = 0）——这条两支臂流程从不认证任何分歧。"
              "把 f_robust_inv = 0 读成“本体系没有排序反转”，是把定义性结果误读为经验结论；本文的实际结论要弱得多、也稳得多："
              "现有双支臂证据**不能识别**排序是否反转。两条定理的完整表述、逐块计数与验证见补充材料 S2。")
'''

P_G11 = '''    body(doc, "这批数据的性质还必须与数字分开声明：within-series 表的 14 行氧化锚点 provenance 全部为 transcription-only，"
              "未回溯到原始测量；两篇上游原著均不在本地文献库、本环境亦无网络，仓库没有对任何一行做过独立复核。"
              "因此这 14 行只作为 designated reference model 提供外部参考条件，不构成本文的实验验证证据。"
              "同时说明本文的计算范围：全文零新增电子结构计算，所有结论只对仓库中已有的冻结数据成立。")
'''

P_G08 = '''    body(doc, "这一节还有一条定义域层次的边界必须写明：C1 的还原态身份一旦按 Li-centered 与 molecule-centered 分层统计，"
              "主排序样本就塌到 n = 1——还原轴在 C1 条件下已经无定义。这不是误差变大，而是被测量的对象变了："
              "[LiM]+ 的还原中心是 Li 而不是溶剂分子。本文据此规定还原轴的决策结论只以 P2/C1 为载体，"
              "任何建立在 C1 还原轴上的排序数字都不作独立证据使用。")
'''

P_G09 = '''    body(doc, "本节结论必须连同它的反例一起读。上面的配对 bootstrap 是按（任务·特征集·轴）分组、同模型同划分统计的；"
              "若改用冻结的逐格最优模型表（每一格在 direct 与 shift 两种形状上各自取中位 τ_b 最优的模型，见 "
              "outputs/week32/delta_vs_direct.csv），同样 8 个分组里只有 6 个的 τ_b 更好，两个反例是 C|X0|reduction "
              "与 C|X0+X1|reduction。两种口径的模型选择规则与分母不同，不能互相替代；无论取哪一种，本节能支持的都是"
              "“位移学习是更稳妥的默认选择”，而不是“位移学习普遍更优”。")
'''

P_G0610 = '''    body(doc, "本节的两条适用边界必须与曲线同读。其一，家族留出口径下的主动学习曲线**不可用**：冻结的 replay 只在池内做插值，"
              "一旦把整个家族留出，池内可用于插值的邻居随之消失，曲线不再有定义；因此本文所有预算数字都是**池内插值**口径，"
              "不能读成跨家族外推的预算。其二，本节的成功标准是内部操作性标准——中位 τ_b ≥ 0.80、Top-20% 清单重叠完整、"
              "selection regret ≤ 池内目标量程的 5%，且要求在 ≥ 80% 的重复中成立——它来自本文自己的决策口径，未经任何外部校准；"
              "因此“恢复中位 τ_b ≥ 0.80 需要 9–15 个昂贵标签”这句话只在同一口径内成立，不能外推为真实筛选所需的 DFT 数量。")
'''

P_CN_ABS = '''    "全文结论限定在 designated computational target 内部的决策稳定性：它不构成对真实电解液体系的实验有效性声明，"
    "也不是对候选分子绝对性能的排名；把这条边界展开成的 13 条声明见 6.2 节。"'''

P_EN_ABS = '''    " All conclusions are scoped to decision stability inside the designated computational target and make no claim of "
    "experimental validity for real electrolytes, nor any absolute performance ranking."'''

P_CONCL = '''    body(doc, "适用范围需要在这里再声明一次：本文的全部结论限定在 designated computational target 内部的决策稳定性——"
              "即“换一层物理，候选的排序与选择是否改变”。它不是对候选分子真实电化学性能的排名，也不是对任何真实电解液配方的推荐。"
              "这条边界展开成的 13 条声明、14 个主文数字的溯源与 Gate 1 的现状，一并列在第 6 节。")
'''

NEW_SECTIONS = '''BOUNDARY_ROWS = [
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
    ["L09", "P1v 与 P1a 的 ROBUST_INVERSION 分子对数", "2", "outputs/phase2_p1a/p1v_vs_p1a.json"],
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
'''


def patch(text, anchor, insert, name):
    n = text.count(anchor)
    if n != 1:
        raise SystemExit("ANCHOR %s occurs %d times, expected 1" % (name, n))
    return text.replace(anchor, anchor + "\n" + insert)


def patch_before(text, anchor, insert, name):
    n = text.count(anchor)
    if n != 1:
        raise SystemExit("ANCHOR %s occurs %d times, expected 1" % (name, n))
    return text.replace(anchor, insert + "\n" + anchor)


def main():
    raw = io.open(PATH, encoding="utf-8").read()

    raw = patch(raw,
                '              "而不是同一可观测量在两个精度下的比较，因此其 τ_b 只用于说明配位如何改写排序，不能解释为精度改善。")',
                P_DESIGNATED, "designated-terms-2.2")

    raw = patch(raw,
                '              "中间那段“已分辨却仍翻转”的窗口在本文数据里是空的。")',
                P_SIGMA, "sigma-T6-3.4.1")

    raw = patch(raw,
                '              "把 Gate 1 写成“已闭合”会超出数据能支持的范围。")',
                P_G11, "G11-3.1.2")

    raw = patch(raw,
                '              "而不是某个方法的精度不够。")',
                P_G08, "G08-3.3.1")

    raw = patch(raw,
                '              "不足以对复杂模型的泛化能力下强结论。")',
                P_G09, "G09-3.5.1")

    raw = patch(raw,
                '              "因此本节以 18 分子池（12–15 个标签）为主口径，10 分子池只作对照。")',
                P_G0610, "G06-G10-3.6.3")

    raw = patch(raw,
                '= 0.4286)."',
                P_EN_ABS, "en-abstract-scope")

    raw = patch(raw,
                '\u5c1a\u672a\u83b7\u5f97\u72ec\u7acb\u7684\u6db2\u76f8\u5b9e\u9a8c\u652f\u6301\u3002"',
                P_CN_ABS, "cn-abstract-scope")

    raw = patch_before(raw, "def write_core_alignment(doc):", P_CONCL, "conclusion-scope")

    raw = patch_before(raw, "def main():", NEW_SECTIONS, "new-sections")

    old = "    write_core_alignment(doc)\n    acknowledgment(doc, ACK_TEXT)"
    if old not in raw:
        raise SystemExit("main() call block not found")
    raw = raw.replace(old,
                      "    write_core_alignment(doc)\n    write_boundaries(doc)\n"
                      "    write_supplementary(doc)\n    acknowledgment(doc, ACK_TEXT)")

    io.open(PATH, "w", encoding="utf-8", newline="\n").write(raw)
    print("patched, bytes:", len(raw.encode("utf-8")))


main()
