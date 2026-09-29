# delta_m 组装（Stage 6 输入，候选值，尚未写入预注册）

## 规则原文（`config/prereg.yaml` pair_comparison.delta_m）

> `meaning`: 与方法不确定度无关的固定 pair tolerance，兜底阈值，单位 kJ/mol
> `per_objective`: oxidation 与 reduction 各自独立确定，不允许共用一个未经检验的值
> `source_rule`: (1) 外部 anchor 自身的实验离散度 → (2) method audit 中同一分子不同 method / conformer 的 target quantity 离散度 → (3) `delta_default`
> `delta_default`: 2.0 kJ/mol（0.0207 eV）
> `units_policy`: dP_ij 与 delta_m 必须使用同一单位（默认 kJ/mol）

## 执行计划 docx §6.2 的合成规则

`delta_m = max(构象系综 90 分位展宽, 方法审计 inter-method 展宽, 0.05 eV 下限)`

## 证据可用性

- source_rule (1)：**不可用**（no species carries a replicate measurement, so no within-series experimental standard deviation can be formed）
- 因此按 source_rule 顺序落到 (2)：method audit 离散度。本仓库的“method audit”即 P0↔P1 在同一冻结几何上的逐分子位移。

## 组成项

| 层 | 目标 | delta_m [eV] | delta_m [kJ/mol] | 主导项 | 构象 p90 [eV] | 方法 pstdev [eV] | 下限 [eV] |
|---|---|---|---|---|---|---|---|
| P0 | oxidation | 0.7002 | 67.563 | method | 0.0350 | 0.7002 | 0.0500 |
| P0 | reduction | 2.0743 | 200.139 | method | 0.2212 | 2.0743 | 0.0500 |
| P1 | oxidation | 0.7002 | 67.563 | method | 0.0907 | 0.7002 | 0.0500 |
| P1 | reduction | 2.0743 | 200.139 | method | 0.2303 | 2.0743 | 0.0500 |

## 与预注册 units_policy 的一致性

预注册默认单位是 kJ/mol，因此上表同时给出 kJ/mol；换算常数 1 eV = 96.4853 kJ/mol （F = 96485.33212 C/mol）。本报告不引入任何电极换算，因为 Stage 6 的 dP 是气相垂直 IP/EA 的能量差，不涉及 reference electrode。

## 冻结前必须由操作者裁决的事项

- 选项 A：把上表数值经 amendment 追加写入 config/prereg.yaml 的 pair_comparison.delta_m（append-only amendment_log）。代价：scripts/freeze_gates.py 一见 amendment_log 非空就把 Gate 0 记为未关闭，所以必须在周报与 gate 记录里明确解释这次追加。
- 选项 B：把数值冻结在 outputs/week6/delta_m_frozen.json + docs/13_week6_report.md，config/prereg.yaml 保持逐字节不变。代价：delta_m 的值不在预注册文件里，与 docx §6.2“分析脚本从预注册文件读取，不写死”的措辞有张力；Stage 6 分析脚本因此显式把该文件作为读入项并在产物里回链。
- 待裁决的数值问题：p1 层的 method term 在本仓库内没有更高的第二个方法可对照，上表 p1 的 method term 复用了 p0↔p1 的审计离散度；若认为 p1 层应另取证据，则 p1 的 delta_m 退化为 max(构象项, 0.05 eV)。
- 待裁决的口径问题：预注册 delta_default = 2.0 kJ/mol（0.0207 eV）与 docx 下限 0.05 eV（4.8242 kJ/mol）不是同一个数；本表按 docx 使用 0.05 eV 下限，并把 2.0 kJ/mol 保留为 source_rule (3) 的兜底。

