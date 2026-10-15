# Stage 21（Week 20）· Part B：`charge_l1` 身份判据的运行手册预检

本文件由 `scripts/analyze_stage21_protocol.py` 现算生成，全部数字来自 `outputs/week17/stage18_identity_census.csv`（SHA256 `a6dab39a0f98b999`），没有一条是手工抄写的。

## 1. 阈值与它的来源

- 冻结参考值 `FROZEN_THRESHOLD` = **0.039**（Stage 18 的 `CHARGE_L1_THRESHOLD`，是事后从 discovery 臂上读出来的**经验阈值**，不是物理常数）。
- 本模块用法：`verdict(charge_l1, threshold, margin)`，阈值与带宽都是**参数**；CLI 默认**从数据重新导出**，不把 0.039 当真值。
- 重新导出的口径：`discovery arm only`。coincident 组最大 = **0.038509**，moread_lower 组最小 = **0.039383**，两者之间的空隙 (0.038509, 0.039383) 宽度 **0.000874** 里**没有数据点**，所以取空隙中点 **0.038946** 作阈值。冻结的 0.039 恰好落在同一空隙内，因此两者对本目录的分类完全一致。
- 用全部格子（discovery + holdout）重导也是一样的空隙：coincident 最大 = 0.038509，moread_lower 最小 = 0.039383（说明 holdout 没有落进空隙，这与 Stage 18「未咨询 holdout」的纪律一致）。
- `borderline` 带：|charge_l1 − 阈值| ≤ **0.01**（约阈值的 25%）。

## 2. 三分类计数与 borderline 清单

| 分类 | 判据 | 格子数 |
| --- | --- | --- |
| `coincident` | charge_l1 < 阈值 − 带宽 | 237 |
| `borderline` | \|charge_l1 − 阈值\| ≤ 带宽 | 3 |
| `differs` | charge_l1 > 阈值 + 带宽 | 36 |
| `unmeasurable` | 读不到电荷表（闭壳层，Stage 17 的写读法） | 138 |

（`stage21_protocol_borderline.csv` 是**逐格**表：全部 414 行都写进去了，`is_borderline` 列可以直接筛。）

需要预检标记的格子（共 **3** 格）：

| name | state | epsilon | arm_set | charge_l1 | 距阈值 | 能量规则裁决 | 家族 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DMC | cation | 5.0 | discovery | 0.039383 | 0.000437 | `moread_lower` | linear_carbonate |
| EC | cation | 28.0 | discovery | 0.038509 | -0.000437 | `coincident` | cyclic_carbonate |
| EC | cation | 40.0 | discovery | 0.02958 | -0.009366 | `coincident` | cyclic_carbonate |

- 家族分布：cyclic_carbonate 2，linear_carbonate 1。
- state 分布：cation 3。

紧贴带外（距阈值在 0.01 与 0.02 之间、尚未触发标记）的格子：
- `EC/cation/eps=20.0`：charge_l1 = 0.049116，距阈值 0.01017，裁决 `differs`。
- `EC/cation/eps=80.0`：charge_l1 = 0.019923，距阈值 -0.019023，裁决 `coincident`。

## 3. `charge_l1` 与真身份判据（能量规则）的一致性

- 交叉表（廉价裁决 × `rule_classification`）：
  - `borderline|coincident`：2 格
  - `borderline|moread_lower`：1 格
  - `coincident|coincident`：237 格
  - `differs|moread_lower`：36 格
  - `unmeasurable|coincident`：138 格
- 交叉表（廉价裁决 × 冻结的 `identity_differs`）：
  - `borderline|False`：2 格
  - `borderline|True`：1 格
  - `coincident|False`：237 格
  - `differs|True`：36 格
  - `unmeasurable|False`：138 格
- 把 `differs` 当阳性、`rule_classification == moread_lower` 当真值：
  - 严格口径（只有 `differs` 算阳性）：TP 36 / FN 1 / FP 0 / TN 377，灵敏度 0.972973。
  - 宽松口径（`differs` 或 `borderline` 算阳性）：TP 37 / FN 0 / FP 2 / TN 375，灵敏度 1。
- 严格口径唯一的分歧是 **1 次漏检**（真值 `moread_lower` 却落在 borderline 带内）；把 borderline 也算阳性后翻成 **2 次误报**（真值 `coincident`）。带宽夹住的就是这几格 —— 这正是预检要标记的对象。

## 4. 「廉价单点读数」的适用条件与反例

Week 19 报告 §3 用 33/37（89%）说明「同一几何上廉价单点能复现昂贵方法的偏好方向」。把这句话套到 `charge_l1` 上，适用条件是：

1. 两条腿都必须打印出 `MULLIKEN ATOMIC CHARGES` 表，且原子数一致；
2. 冻结的 Stage 18 读法**还**要求自旋列，所以闭壳层（中性）格子对它一律「不可测」；本模块的实时读法则可以退一步只用电荷列。

- 概数：可测 **276/414 = 66.67%**；其中被判 `moread_lower` 的可测格子有 37 个，严格口径灵敏度 0.9730、宽松口径灵敏度 1.0000。
- 反例检验（闭壳层重读）：反例为空：138 个被冻结读法判为「不可测」的闭壳层格子里，改读打印出来的电荷表后 charge_l1 最大只有 0.006743 e（Mulliken 电荷的 L1 距离），仍比阈值 0.038946 小约 5.8 倍，没有任何一格会翻案。
- 与能量规则的净不一致数：严格口径 **1**，宽松口径 **2**。

读法：`charge_l1` 的**唯一**已知短板是「够不着」而不是「看错」——它对闭壳层格子（本目录全部 138 个 neutral）返回 `unmeasurable`，而对够得着的格子，它和能量规则没有一次翻案。

## 5. 给运行手册的一条可执行建议

把 `identity_distance` / `verdict` 接到**提交前**的自检里：任何一格的 |charge_l1 − 阈值| ≤ 0.01 就先打 `BORDERLINE` 标记并写进台账，再决定要不要花机时。本目录必须标记：`DMC/cation/eps=5.0`、`EC/cation/eps=28.0`、`EC/cation/eps=40.0`。

复现（三条产物都逐字节可校验）：

```
python scripts/analyze_stage21_protocol.py
python scripts/analyze_stage21_protocol.py --check
```

