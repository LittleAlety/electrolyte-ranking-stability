# Stage 1 — 方法审计与外部锚点 (方法审计协议)

对应 v2 第 7.1 节(先做 method audit,再冻结 production protocol)、第 15 节(外部 reference anchors)、
第 19 节 Stage 1 及 **Gate 1**。

> 原则: **method sensitivity ≠ method accuracy**。
> 前者只比较不同合理方法之间的离散度(用来估计 \sigma_{ij});
> 后者必须依赖外部 reference(实验或更高层计算)。

---

## 1. 审计目的

1. 估计**方法不确定度** \sigma_{ij},作为 v2 §9.1 判定 pair 是否 `unresolved` 的尺度。
2. 确认 production protocol(几何 + 单点)对典型体系**没有系统性失败**。
3. 用外部锚点区分「model-to-model 排序保持」与「是否更接近真实可观测量」。

---

## 2. 审计分子集 (8–10 个)

从 core set 中选取,覆盖:

| 维度 | 覆盖要求 |
| --- | --- |
| family | 线性碳酸酯、环状碳酸酯、醚、酯、砜/亚砜、腈、磷酸酯 各 ≥1 |
| 柔性 | 至少 2 个高柔性分子(DEC、TEGDME 类)作构象敏感性探针 |
| 电子结构 | 至少 2 个易还原(高 LUMO 密度)与 2 个易氧化(高 HOMO)对照 |
| 阴离子 | 至少 3 个会形成阴离子的还原产物,专门检查 diffuse/束缚态 |
| 氟化 | 至少 1 个氟代(FEC 或类似) |

---

## 3. 审计分支 (arms)

### A. 泛函敏感性 (method sensitivity)
- 主候选: `r2SCAN-3c`(composite,r2SCAN + D4 + def2-mTZVPP 类)。
- 对照: 至少一个 range-separated hybrid,例如 `ωB97X-D4`(或同族),triple-ζ 基组。
- 目的: 给出同一 observables 在不同合理泛函下的离散度。

### B. 基组 / diffuse 处理
- 至少两个级别: 无 diffuse 与加 diffuse 变体(如 ma-def2 / aug- 类)。
- 阴离子**单独**建立 diffuse protocol(v2 §7.3)。检查项:
  - diffuse augmentation;
  - SOMO 空间扩展;
  - electron detachment stability;
  - SCF 解是否为伪束缚态。
- 气相阴离子不稳定 → 标记 `unbound_anion`,**不强行**生成气相绝热还原排序。

### C. 连续介质敏感性(两类必须分开,v2 §8.3)
- **A. Fixed-solvent continuum benchmark**: 用一个被 continuum 模型明确参数化、且与外部锚点数据兼容的固定参考溶剂(建议: 全部候选同一设定)。给 $P_2$。
- **B. Dielectric-only sensitivity**: 用 CPCM/COSMO 类模型分别取 $\epsilon = 5, 10, 20, 40$。
- **禁止**把 SMD 的 solvent-specific 非静电参数与「只改介电常数」混为同一操作。

### D. 外部锚点
- 气相: IP / EA(实验优先)。
- 溶液: 氧化 / 还原电位(实验,标注参考电极与溶剂)。

---

## 4. 输出与判据

> **实测状态:** xTB 臂已跑出结果,见 `docs/04_stage1_xtb_audit_result.md`;
r2SCAN-3c 臂仍待 ORCA。

### 4.1 每个 arm 记录
- absolute error vs 锚点(有锚点的物种);
- 同一 observables 的 **rank stability**(Spearman \rho、Kendall \tau_b);
- 离散度 → \sigma_{ij} 估计(供 `uncertainty.py: bootstrap / quantify_method_sigma`)。

### 4.2 Gate 1 判据(全部满足才可启动批量计算)
1. state identity 对典型体系无系统性失败(无大量 `unbound_anion`/`motif_switch` 误判);
2. SCF 稳定(无反常的伪束缚态解);
3. 气相锚点上无显著系统偏差(趋势方向正确);
4. 溶液趋势与锚点方向一致;
5. production protocol 已**显式冻结**并写入 provenance(见 `provenance.py`)。

> 若 ORCA 尚未就绪,Gate 1 记作「**待真实二进制**」,Week 3 之前不启动真实批量计算;
> dry-run 路径仍可先把流水线跑通。

---

## 5. 与 `config/prereg.yaml` 的关系

\sigma_{ij} 的**用法**(z 值、\delta_m 上限)属于预注册内容,须在查看完整排序结果**之前**冻结,
不得事后为提高「显著翻转」数量而放宽阈值。
