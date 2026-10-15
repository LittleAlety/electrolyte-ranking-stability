# Week 1 成果小结 —— Stage 0 定义冻结 / Gate 0

## 1. 本周做了什么
- 冻结 Stage 0 科学定义与预注册，建立「定义先于数据」的纪律：`config/scientific_definitions.yaml`
  固定 P0/P1/P2、C0/C1/C2、R_gas/R_sol/R_env、目标量方向、参考配体 R 与受控词表；
  `config/prereg.yaml` 固定 pair 比较规则、z 因子、bootstrap 种子与决策指标。
- 构建并核对 chemical-space 元数据：core set 18 行、broad pool 40 行，均可由
  `scripts/build_metadata.py` 重建。
- 运行 Gate 0 检查，留下 `outputs/week1/gate0_record.md`（frozen artefacts: 6）。
- 本目录**额外快照** `config/scientific_definitions.yaml` 与 `config/prereg.yaml`：冻结定义必须
  与派生产物同行交付，否则下游任何一个数字都不可判读。

## 2. 关键数字
| 项目 | 值 |
| --- | --- |
| Gate 0 状态 | **CLOSED** |
| 冻结产物数 | 6 |
| core set 行数 | 18 |
| broad pool 行数 | 40 |
| `config/prereg.yaml` sha256 | `e89f2e2ab714ac4268d7b695fbb8494b7aef61a68341753cc031b8af0ca5f340` |

### 2.1 冻结产物 sha256（现场重算逐字节比对）
| 冻结产物 | sha256 (记录值) | 现场重算 | 一致 |
| --- | --- | --- | --- |
| `config/scientific_definitions.yaml` | `40f7854b37dfac97a08ab26fe360ab86f817c36d0f49bbc26168a1b694f20ed2` | `40f7854b37dfac97a08ab26fe360ab86f817c36d0f49bbc26168a1b694f20ed2` | yes |
| `config/prereg.yaml` | `e89f2e2ab714ac4268d7b695fbb8494b7aef61a68341753cc031b8af0ca5f340` | `e89f2e2ab714ac4268d7b695fbb8494b7aef61a68341753cc031b8af0ca5f340` | yes |
| `data/metadata/core_set.csv` | `630b0ee8c09dc4141124e335181572bf27a63f297a8df95f9c774683a10cf91b` | `630b0ee8c09dc4141124e335181572bf27a63f297a8df95f9c774683a10cf91b` | yes |
| `data/metadata/broad_pool.csv` | `a6ca215e8e217e24c036a4c3571c8096e949b9f46e51571749c7581b9584e346` | `a6ca215e8e217e24c036a4c3571c8096e949b9f46e51571749c7581b9584e346` | yes |
| `data/metadata/chemical_space_metadata.md` | `19be337b1440a58705f57091cba622003653b2a29a2f8fc37b10b20217b394f0` | `19be337b1440a58705f57091cba622003653b2a29a2f8fc37b10b20217b394f0` | yes |
| `docs/00_stage0_definitions.md` | `4372a4bb8ed3a552cb91bccdeb543d45d9699ffa3d84a555150481dd4b984d1a` | `4372a4bb8ed3a552cb91bccdeb543d45d9699ffa3d84a555150481dd4b984d1a` | yes |

`config/prereg.yaml` 的 sha256 为 `e89f2e2ab714ac4268d7b695fbb8494b7aef61a68341753cc031b8af0ca5f340`，是 Gate 0 的唯一判据载体：任何对预注册的
改动都会立即改变该值，从而使 Gate 0 失效（变更只允许以 append-only 方式写入 `amendment_log`，
历史条目不得删除或改写）。

## 3. 质量与复核（QC）
- Gate 0 的检查项（两份 yaml 的 `frozen=true`、metadata `--check`、`amendment_log` 为空）全部通过；
  逐项实测值见本目录 `verification.json` 的 `checks`。
- 上表对每个冻结产物做了**现场重算**，与记录值逐字节比对。
- `outputs/week1` 自身产物很少是正常的：Gate 0 的实质定义在 `docs/00_stage0_definitions.md` 与
  `config/*.yaml`，两者都已在同一目录内。

## 4. 产物清单
- `00_stage0_definitions.md`
- `artifacts/F0_project_pipeline.png`
- `gate0_record.md`
- `prereg.yaml`
- `scientific_definitions.yaml`

## 5. 已知限制
- Week 1 不产生任何 redox 数值结论；它只冻结定义与预注册，供后续周次引用。
- Gate 1（方法 / 锚点）在本周**并未**关闭，其 blocker 见 `week2_report.md`。
- 本目录快照是**只读副本**；任何定义变更必须回到仓库 `config/` 走 amendment 流程。

## 6. 源文件缺失
- 无（全部源路径均存在）
