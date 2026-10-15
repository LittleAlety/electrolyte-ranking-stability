# Stage 7 feature manifest

来源：`ranking-electrolyte-materials-v2.md sections 11-13; config/prereg.yaml sections 5-6, 8`

## 口径
- ox = IP (eV), red = -EA (eV); both are maximised
- a consequence, not a sign bug: P1_red - P0_red is the negative of the underlying EA correction, because the P0 layer stores +eps_LUMO

## feature cost levels
| 级别 | 列 | 何时可用 |
| --- | --- | --- |
| X0 | `mw`, `donor_count`, `n_heavy`, `rotatable_bonds`, `tpsa`, `is_cyclic`, `has_fluorine`, `p0_ox_ev`, `p0_red_ev`, `hl_gap_ev`, `dipole_debye`, `aux_alpha_bohr3` | query 前（SMILES + 廉价 xTB 单点） |
| X1 | `p1_ox_ev`, `p1_red_ev`, `p2_ox_ev`, `p2_red_ev`, `env_d_ox_ev`, `env_d_red_ev` | 拿到 free-molecule DFT 之后 |
| X2 | `x2_dgdg_bind_ev`, `x2_li_min_distance_a`, `x2_li_contacts_n`, `x2_motif_switch` | **需要 Li-complex DFT 之后；只做机制解释** |

## 任务与允许的 feature set
| 任务 | 台阶 | 目标层 | 特征集 | 列数 |
| --- | --- | --- | --- | --- |
| M | method (P0 -> P1) | P1 | X0 | 12 |
| E | environment (P1 -> P2) | P2 | X0+P1 | 14 |
| C | coordination (C0 -> C1) | C1 | X0 | 12 |
| C | coordination (C0 -> C1) | C1 | X0+X1 | 18 |

## 计数
- core 分子数：**18**
- 有 environment 目标的分子数：**18**
- 有 coordination 目标的分子数：**10**
- broad pool（无 target 标签）：**40**
- 一致性异常：无

## 源文件 sha256
| 文件 | sha256 |
| --- | --- |
| `data/metadata/broad_pool.csv` | `a6ca215e8e217e24c036a4c3571c8096e949b9f46e51571749c7581b9584e346` |
| `data/metadata/core_set.csv` | `630b0ee8c09dc4141124e335181572bf27a63f297a8df95f9c774683a10cf91b` |
| `outputs/week3/p0_broad_pool.csv` | `363f67eca29afa0a986e5e48964447f9e821a2c0669c2517397f74f5cc25b2aa` |
| `outputs/week3/p0_core_set.csv` | `8001accb7066b18bdc8b622466163f796ba0b7c527f394d585ff3bdfab5b1cb3` |
| `outputs/week4/p1_core_set_derived.csv` | `2987f8771b722d5a07517289a18a486fb2da24ed5775a196ffd7baf2c57517d3` |
| `outputs/week4/p2_environment_effects.csv` | `b74de81a66979f04c96b52c4280842ae8df8c8db2a9c50d6fb96675e0b752363` |
| `outputs/week4/t2_opt_freq.csv` | `c05c33ac967e436f309588115ac45470a4f540996d3c3a6f868a68feca79ec9e` |
| `outputs/week5/c1_coord_shifts.csv` | `1f9597ba376ffb19610e855e4d83a4e2360a8ac5009209cf764be91008634b5d` |
| `outputs/week5/c1_ligand_exchange.csv` | `6fbb385a5416044ac910c2d05c32ccffa588b174a6955babe4db3ba263c56a6b` |
| `outputs/week5/c1_state_identity.csv` | `cc035b941936842a739d2c23833552acfa3c010283e280276849e0be8d6d1aa3` |
