# 电子身份：前沿轨道组成分析（全系综成员）

> 生成器 `build_frontier_localization.py`（`--check` 完全只读）。
> 单点固定几何、冻结生产级别；Molden 由 `orca_2mkl job -molden` 生成。
> 分类阈值在**读任何结果之前**就冻结：轨道定域 weight ≥ 0.5，Li 定域 ≥ 0.25。

## 覆盖进度

| 项 | 值 |
|---|---|
| 系综加权成员（非仅 48 primary） | 80 |
| 已解析 | **12** |
| 待算 | 68 |

## 两个前沿并不一致

| 指标 | HOMO 侧 | LUMO 侧 |
|---|---|---|
| Li 权重最大值 | **0.002363** | **0.219803** |
| 分类分布 | donor_localized 6 / ligand_localized 6 | li_localized 6 / ligand_localized 6 |

**Li 在 HOMO 中实质上不参与**（最大权重 2.4e-03，远低于 0.25 的 Li 定域阈值），但它在 LUMO 中可以占到 0.22。因此「Li 是否承载前线轨道」这个问题，**只问 HOMO 会得出错误答案**。

## Li 定域的例外（LUMO 侧）

| 成员 | Li_LUMO | 给体_LUMO | 分类 |
|---|---|---|---|
| `TMP|LiM_plus|primary` | 0.2198 | 0.5624 | `li_localized` |
| `TMP|LiM_plus|r3m_c05` | 0.2118 | 0.6498 | `li_localized` |
| `TMP|LiM_plus|r3m_c08` | 0.2068 | 0.6613 | `li_localized` |
| `DME|LiM_plus|primary` | 0.1041 | 0.5447 | `li_localized` |
| `DME|LiM_2plus|r3m_c05` | 0.0009 | 0.3472 | `li_localized` |
| `EMC|LiM_2plus|primary` | 0.0008 | 0.2676 | `li_localized` |

这些态的还原过程涉及 Li 本身，与「Li⁺ 氧化还原沉默」的一般规律相反。**它们是结论的边界，不是噪声**：报告一般规律时必须同时报告例外。

## HOMO/LUMO 分类不一致的成员

8 / 12 个已解析成员的 HOMO 与 LUMO 分类不同。

| 成员 | HOMO | LUMO |
|---|---|---|
| `DME|LiM_2plus|r3m_c05` | `ligand_localized` | `li_localized` |
| `DME|LiM_plus|primary` | `donor_localized` | `li_localized` |
| `EC|M|63` | `donor_localized` | `ligand_localized` |
| `EMC|LiM_2plus|primary` | `ligand_localized` | `li_localized` |
| `TMP|LiM_plus|primary` | `donor_localized` | `li_localized` |
| `TMP|LiM_plus|r3m_c05` | `donor_localized` | `li_localized` |
| `TMP|LiM_plus|r3m_c08` | `donor_localized` | `li_localized` |
| `TMP|M_plus|27` | `donor_localized` | `ligand_localized` |

## 已解析成员明细

| 成员 | Li_HOMO | 给体_HOMO | HOMO 分类 | Li_LUMO | 给体_LUMO | LUMO 分类 |
|---|---|---|---|---|---|---|
| `DME|LiM_2plus|r3m_c05` | 0.0002 | 0.4019 | `ligand_localized` | 0.0009 | 0.3472 | `li_localized` |
| `DME|LiM_plus|primary` | 0.0024 | 0.4924 | `donor_localized` | 0.1041 | 0.5447 | `li_localized` |
| `DME|M_plus|23` | 0.0000 | 0.3831 | `ligand_localized` | 0.0000 | 0.3184 | `ligand_localized` |
| `DME|M_plus|c07` | 0.0000 | 0.4643 | `ligand_localized` | 0.0000 | 0.4557 | `ligand_localized` |
| `EC|M_plus|0` | 0.0000 | 0.7442 | `ligand_localized` | 0.0000 | 0.3659 | `ligand_localized` |
| `EC|M_plus|primary` | 0.0000 | 0.7435 | `ligand_localized` | 0.0000 | 0.3639 | `ligand_localized` |
| `EC|M|63` | 0.0000 | 0.9175 | `donor_localized` | 0.0000 | 0.3299 | `ligand_localized` |
| `EMC|LiM_2plus|primary` | 0.0003 | 0.3974 | `ligand_localized` | 0.0008 | 0.2676 | `li_localized` |
| `TMP|LiM_plus|primary` | 0.0002 | 0.7382 | `donor_localized` | 0.2198 | 0.5624 | `li_localized` |
| `TMP|LiM_plus|r3m_c05` | 0.0002 | 0.7720 | `donor_localized` | 0.2118 | 0.6498 | `li_localized` |
| `TMP|LiM_plus|r3m_c08` | 0.0002 | 0.7647 | `donor_localized` | 0.2068 | 0.6613 | `li_localized` |
| `TMP|M_plus|27` | 0.0000 | 0.8399 | `donor_localized` | 0.0000 | 0.6246 | `ligand_localized` |

**口径**：本报告只描述已解析成员的轨道组成，不改变任何验收判定。
待算成员补齐后本表会自动扩展——覆盖率本身就是「并行补电子身份」这项工作的进度。
