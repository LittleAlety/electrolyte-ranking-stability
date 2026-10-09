# `scripts/` —— 入口脚本布局

本目录放**可执行的入口脚本**（CLI 与批次生成器）；可复用的库代码在 `src/electrolyte_ranking/`。
分工不要混：`src/` 放被 `import` 的纯逻辑，`scripts/` 放「读仓库产物 → 校验 → 写产物」的入口。

## 目录约定

| 位置 | 放什么 |
| --- | --- |
| `scripts/*.py` | 历史各周（week1–week25）的分析 / 生成入口，以及少数仍被测试或门禁直接调用的全局入口（`build_terminal_site.py`、`freeze_gates.py`、`audit_clean_room.py`、`audit_claim_scope.py`、`build_physics_completion_batch.py`、`build_deliverables.py`、`build_week*_deliverables.py` 等） |
| `scripts/wp_production/` | 当前批次 **physics_completion_v1（WP0–WP7）的完整流水线**：生产驱动 + 生成器 emit + 各派生层 + 一键收口。见 `scripts/wp_production/README.md` |
| `scripts/wp_production/wp1_audit_src.txt` / `wp1_newsrc.py` | WP1 方法审计的补丁源（由 `emit_wp1.py` 折进生成器） |
| `work/`（不跟踪） | 原始 ORCA / xTB 输出、生成器基线缓存、临时脚本 |

## 新增脚本的落点规则

1. 属于当前批次流水线 → 放 `scripts/wp_production/`，并在该目录 README 的脚本表里登记；
2. 全局门禁 / 交付入口（被 `tests/` 或 `freeze_gates.py` 直接调用）→ 留在 `scripts/` 顶层；
3. 一次性历史分析 → 也放 `scripts/` 顶层，命名沿用 `analyze_*`（分析）、`build_week*` / `build_*deliverables`（出交付）、`run_*`（跑计算/驱动）；
4. 脚本只能用 `Path(__file__).resolve().parents[N]` 定位仓库根：顶层脚本 `N = 1`，`scripts/wp_production/` 内脚本 `N = 2`。

## 一个重要约束

`outputs/**` 是**生成物**。改动量名、阈值、措辞或路径时，要改生成脚本，然后跑

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\wp_production\finalize_wp2.ps1
```

让产物、交付镜像、站点、冻结门与测试一起收敛；直接手改 `outputs/**` 会在下一次 `--check` 失败。
`scripts/build_physics_completion_batch.py` 本身也是**派生物**（由 `emit_wp2.py` 从 git 历史基线 + 补丁块确定性重打），手工改会被覆盖。