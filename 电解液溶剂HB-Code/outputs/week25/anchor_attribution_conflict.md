# W25 锚点来源归属冲突记录

## 裁决（2026-10-02，status = resolved）

**冲突不成立——两条陈述是兼容的。** PI 复核 Okoshi 2015 原文全文（有网络）后确认：

- Crossref 题录没错：该文确为《Theoretical Analysis of the Oxidation Potentials of Organic Electrolyte Solvents》，*ECS Electrochem. Lett.* **4**(9) A103，是一篇 CCSD(T)/CBS/CPCM 的**理论计算论文**。
- 引入说明也没错（但措辞不够精确）：该文 **Fig. 1 明确列出 14 个溶剂的实验氧化电位**，来源标注为其 **refs 1–2**（两篇 Ue 论文，1994 那篇只是 ref 1），原值 vs SCE，由文中式(2) 换算到 Li⁺/Li 标度（E°(SCE/SHE) = 0.24 V、E(Li⁺/Li)/SHE = −3.04 V，即 +3.28 V），并声明这组参考实验值"是在相同实验条件下获得的"。

**裁决文本（可直接引用）**

> 数据主源（primary）：Ue et al.，Okoshi 2015 的 refs 1–2，LSV 实测，vs SCE，同装置同判据；转录与标度换算载体（secondary tabulation）：Okoshi et al. 2015, ECS Electrochem. Lett. 4(9) A103, Fig. 1（理论论文，但其 Fig. 1 的实验值非该文测量）。引用数字时的正确格式为"Ue et al. 实测，经 Okoshi et al. 2015 Fig. 1 转录并按其式(2) 换算至 Li⁺/Li 标度"。

**被撤回的表述**：此前"Fig. 1 重刊 Ue **1994** 实验值"的说法不精确——refs 1–2 是**两篇** Ue 论文。这个不精确正是下面 EC 归属疑点（`ec_anchor_ref_attribution.json`）的由来。

---

## 历史记录（冲突原始记录，仅存档，不再是现行解读）

## 冲突内容

| 项 | 内容 |
| --- | --- |
| 引入说明的主张 | Okoshi et al. 2015 的 Fig. 1 把 Ue 1994 的实验氧化电位统一换算到 Li⁺/Li 标度重新发表，并说明参考实验值"是在相同实验条件下获得的" |
| 本仓库的核验结果 | 2026-10-02 批次经 Crossref 核验，Okoshi 2015（*ECS Electrochem. Lett.* **4**(9), A103–A105, doi:10.1149/2.0051509eel）题录为 *Theoretical Analysis of the Oxidation Potentials of Organic Electrolyte Solvents*，属**理论计算**类工作 |
| 证据位置 | `outputs/week24_corealign/gate1_anchor_feasibility.md` 候选行 1 与其 §7 更正 1 |

两者**在本环境内无法调和**：沙箱无网络（WinError 10061），且 Okoshi 2015 与 Ue 1994 的原著 PDF 均不在 `核心文件/文献`。

## 后果与纪律

- 14 行氧化锚点与 3 行还原旁证**全部保持** `repo_verification = transcription_only`；系列归属（Ue 1994 实验 LSV，经 Okoshi 2015 转录）记录为**未经核验的主张**，不是仓库已核实的事实。
- 任何论文、报告或交付物引用这批数字时，**必须在同一句或同一条表注中**声明该冲突。
- 该冲突**不构成丢弃数据的理由**：它影响的是归属与结论强度，不影响算术——同系列排序检验（`tau_b = 0.428571`，`n_pairs = 21`）的数值不受影响，但"实验锚定"这一表述的强度被它封顶。

## 复现

本文件为人工撰写记录，不含计算。上游事实可用以下命令复核：

```powershell
.venv\Scripts\python.exe -c "import io;print([l for l in io.open(r'outputs/week24_corealign/gate1_anchor_feasibility.md',encoding='utf-8') if 'Okoshi' in l])"
```
