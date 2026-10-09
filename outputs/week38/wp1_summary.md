# Week 38 / WP1 — 独立方法审计表（首轮登记）

**状态**：矩阵与规则已冻结；首轮只盘点既有电子能层作业，零新增计算。

## 冻结内容

- 固定条件：SMD 乙腈、298.15 K、溶液标准态 1 mol/L；几何起点 r2SCAN-3c。
- 方法矩阵：8 分子 × 4 状态 × 4 设定 = **128** 单点上限。
- 生产候选 ωB97X-D4（def2-TZVP / def2-TZVPD）；审计对照 PBE0-D4（同两基组）。
- 还原态必须使用含弥散函数设定（S2 / S4）；有限基组能收敛**不能**证明束缚。
- 方法选择规则：QC 可用率 / 数值稳定性 / 气相 anchor 可比 / rank sensitivity / 实测成本；**不**按翻转数量选方法。

## 验收（5/5 通过）

| check | ok | detail |
| --- | --- | --- |
| matrix_is_full_factorial | PASS | n_rows=128 |
| reduction_has_diffuse_option | PASS | diffuse settings=S2,S4 |
| both_functionals_present | PASS | functionals=PBE0-D4,omegaB97X-D4 |
| existing_jobs_are_electronic_layer_only | PASS | 3 个既有载荷被盘点 |
| no_method_selected_by_flip_count | PASS | 冻结规则：QC 可用率 / 数值稳定性 / 气相 anchor 可比 / 固定介质内 rank sensitivity / 实测成本 |

## 既有可复用作业（只到电子能层）

| 载荷 | 层 | 行数 | 分子 | 复用范围 | 限制 |
| --- | --- | --- | --- | --- | --- |
| `outputs/week4/p1_core_set.csv` | P1v (gas-phase vertical) | 54 | 18 | electronic-energy layer only | no diffuse functions; no thermal correction |
| `outputs/phase2_p1a/p1a_adiabatic.csv` | P1a (gas-phase adiabatic) | 12 | 12 | relaxation effect only | reduction axis excluded by the unbound_anion rule |
| `outputs/week5/c1_coord_shifts.csv` | C1 (Li-coordination) | 12 | 10 | conditional shift demonstration | single representative motif; identity stratification applies |

## 限制

- 首轮**没有**任一候选泛函/基组在本机的实测支持性回显；方案中的 ωB97X-D4 / PBE0-D4 仍是建议候选。
- 既有作业是气相 r2SCAN-3c（无弥散），不能裁断 0.01 eV 量级的阴离子束缚，也不含热校正。
- 独立方法审计是 sensitivity assessment，不等于校准的概率误差；1.96×spread 不得自动标成 95% 置信度。
