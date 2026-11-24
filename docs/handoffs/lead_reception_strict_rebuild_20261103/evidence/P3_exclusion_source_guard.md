# P3 · 排除来源守卫（Plan 首批第 3 项 = action item 4 前半：排除集判据改造）

> 会话：公共处理会话（唯一共享生产写入者）｜权限：Plan 首个执行批次第 3 项授权的**门控工程修改**。
> 边界：不新增计算、不改阈值、不改输出 schema、不填 `resolved`、不迁账本、不改正式标签与费用。
> 复核时间：2026-11-03（仓库 HEAD `80933e54f8a605d9dd6d033c0f2861e33b591c13`）。

## 1. 缺陷定位（改前，实测）

对象：`scripts/wp_production/build_coverage_reviews.py` 的 `_rejected_probe_members()`（排除集唯一来源；消费方 `:275` 覆盖审 + `run_coverage_generator_strict_sandbox.py:50/84` 隔离复跑包装器）。

| 旧行为 | 问题 |
|---|---|
| `if not manifests: raise SystemExit(...)` | 只要求**文件数非零**（数量非零判据） |
| `try: json.loads(...) except (OSError, ValueError): continue` | **损坏/不可读的 manifest 被静默跳过**——其拒绝/取消记录整份丢失，守卫照样通过（来源不完整、不可验证） |
| 无溯源 | 集合**可验证性**缺失：事后无法证明「这批排除项来自这些字节」 |

与 ARCHIVE_DEPENDENCIES 的既有契约一致（`build_coverage_reviews` 排除集空=静默重新放行 → 必须 SystemExit），本次把判据从「≥1 文件存在」升级为「**每个来源都被完整读取且可解析，否则拒绝**」，并登记逐源 SHA256 溯源；**完整读取后确实为零条拒绝 = 空集合被接受**（「没有记录拒绝」是真事实，不设非零条数要求）。

## 2. 改前基线（action item 1 纪律）

- 原字节副本：`evidence/p3_exclusion_guard/baseline/build_coverage_reviews.py.orig`（与改前盘上逐字节相同，实测 `copy_identical = True`）
- 登记：`evidence/p3_exclusion_guard/baseline/BASELINE.json`
  - `sha256 = ed2b621d30f8df5c2f3088f56012d7ca66447591918b2f00114ff06af2ad6784`
  - `bytes = 27,332`｜mtime 2026-11-03 11:17:13（**修改前即为 git 预存 M 文件**，非本轮引入）

## 3. 修改内容（48 个 diff 行，全部在该函数内）

| # | 修改 | 效果 |
|---|---|---|
| 1 | docstring 增补判据契约（source completeness, not a non-zero count；空集合可接受） | 契约成文 |
| 2 | `read_bytes()` 单独 try：`OSError` → `SystemExit("REFUSING … cannot read …")` | 不可读源 = 拒绝（原静默跳过） |
| 3 | `json.loads` 单独 try：`ValueError/UnicodeDecodeError` → `SystemExit("REFUSING … not parseable JSON …")` | 损坏源 = 拒绝（原静默跳过） |
| 4 | 解析结果必须是 `dict`，否则 `SystemExit("… not a manifest object")` | 结构不可读 = 拒绝 |
| 5 | 新模块级 `EXCLUSION_SOURCE_PROVENANCE`：成功后登记每源 `{path, bytes, sha256}`（glob 序） | 可验证溯源 |
| 6 | 零 manifest 的原拒绝文案**原样保留**（测试断言 `REFUSING`/`re-admit`） | 既有 clean-clone 契约不破坏 |

健康路径的条目抽取逻辑（`rejected[].member_key`、`replaces_cancelled_job`→整键）**一字未改**。

## 4. 修改后实测

| 项 | 结果 |
|---|---|
| 修改后 `build_coverage_reviews.py` | `a7eee5aa3df733cddd3fe4282a6b179c328fbe4b9b1c4ad319829b16ec07c765`｜29,558 B（+2,226） |
| 新测试 `tests/test_exclusion_source_completeness.py` | `22610644847f1f65c9c37ca89f26e929daf1ee65c3c4b234f4478860a430ecdc`｜6,189 B｜**8 用例** |
| `python -m py_compile scripts/wp_production/build_coverage_reviews.py` | **exit 0**（compile_ok） |
| `python -m pytest tests/test_exclusion_source_completeness.py tests/test_clean_clone_dependencies.py tests/test_archive_dependency_inventory.py -q -p no:cacheprovider` | **exit 0**｜22 用例全过 0 失败 0 跳过（新 8 + 既有 clean-clone/archive 契约 14） |
| `python -m pytest tests/test_strict_coverage_single_cluster.py -q -p no:cacheprovider` | **exit 0**｜5 用例全过（消费方 + 单簇判据回归） |
| 真实层只读验证（不写任何产物） | `exclusion_set_size = 3`、`has_DMC_key = True`、`provenance_n = 4`，4 个 manifest 逐个 `sha_ok True`（5,791/1,811/1,750/2,248 B）｜exit 0 |

## 5. 对照 Plan 验证口径

| Plan 要求 | 本轮证据 |
|---|---|
| 排除集 = 来源完整可验证，而非数量非零 | 损坏/不可读/非对象源逐一律 SystemExit（原静默跳过路径清零）；完整读取后的空集合被接受；逐源 sha256 溯源可验证（真实层 4/4 sha_ok） |
| 终态义务视图全保留 / 仅合格成员参与去重和权重 / 不手填 resolved | **不在本项范围**——属 action item 4 后半，本轮未触碰任何义务视图、去重权重与 resolved 字段 |
| 五态覆盖只消费数据分析审定谱系 | 属首批第 4 项（五态隔离绑定），本轮未触碰 |
| 单合格簇不被 `new` 误判多盆地、真实多簇不误拒 | `tests/test_strict_coverage_single_cluster.py` 5/5 回归通过（既有判据未被本轮改动破坏） |

## 6. 复现命令（cwd=仓库根）

```bash
python -m py_compile scripts/wp_production/build_coverage_reviews.py        # exit 0
python -m pytest tests/test_exclusion_source_completeness.py \
  tests/test_clean_clone_dependencies.py \
  tests/test_archive_dependency_inventory.py -q -p no:cacheprovider         # exit 0, 22 passed
python -m pytest tests/test_strict_coverage_single_cluster.py \
  -q -p no:cacheprovider                                                    # exit 0, 5 passed
sha256sum scripts/wp_production/build_coverage_reviews.py \
  tests/test_exclusion_source_completeness.py \
  docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/p3_exclusion_guard/baseline/build_coverage_reviews.py.orig
```

## 7. 恢复方式

```bash
cp docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/p3_exclusion_guard/baseline/build_coverage_reviews.py.orig \
   scripts/wp_production/build_coverage_reviews.py
# 恢复后 sha256 应为 ed2b621d30f8df5c2f3088f56012d7ca66447591918b2f00114ff06af2ad6784
```

## 8. 未确定 / 未做

1. 本项**未**改 `run_coverage_generator_strict_sandbox.py`（它以 `lambda` 注入已解析集合，绕过溯源登记；其自身输出 `rejected_probe_members.json` 未含溯源）。是否把溯源接入该 JSON 输出 → 待 Lead 裁定（改输出 schema 不在本批授权内）。
2. action item 4 后半（终态义务视图、去重权重、五态谱系消费）与不手填 `resolved` —— 首批第 4 项处理。
3. 本文件为 git 预存 M 上的追加修改；未提交、未推送、未改任何共享产物输出。
