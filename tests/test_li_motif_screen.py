"""Li 配位 motif 筛选的契约测试：执行器必须忠于已登记的规则与运行记录。

钉住几条容易悄悄退化的性质：
1. 规则先登记后执行：没有 motif_plan.csv 就不许跑筛选（load_legs 直接退出）；
2. 运行记录与落盘 CSV 必须同版（sha256 + 行数），且逐腿与登记计划一一对应；
3. 保留 motif 不超过登记上限，每个保留结构都带父几何 sha256，父几何路径仍在仓库外缓存里；
4. 计划覆盖 physics_completion_set.csv 的**全部 12 个 in_main 分子 x 2 个 Li 态 = 24 条腿**，
   分子集不是硬编码，而是从冻结的 in_main 集合推导；
5. 24 条腿**逐条**都能解析出自己的父几何（该腿自己的生产几何去掉 Li），没有腿靠兜底默认值；
6. 未算的腿保持 not_computed，绝不允许默认通过；运行记录里也不许出现计划外的腿。
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "wp_production" / "screen_li_motifs.py"
PLAN_SCRIPT = REPO_ROOT / "scripts" / "wp_production" / "build_li_motif_sampling_plan.py"
PLAN = REPO_ROOT / "outputs" / "physics_completion" / "li_motif_sampling" / "motif_plan.csv"
ACCEPTANCE = REPO_ROOT / "outputs" / "physics_completion" / "li_motif_sampling" / "acceptance.csv"
RUN_RECORD = REPO_ROOT / "outputs" / "physics_completion" / "li_motif_sampling" / "li_motif_screen.json"
SCREEN_CSV = REPO_ROOT / "outputs" / "physics_completion" / "li_motif_sampling" / "li_motif_screen.csv"
PHYSICS_SET = REPO_ROOT / "data" / "metadata" / "physics_completion_set.csv"
CORE_SET = REPO_ROOT / "data" / "metadata" / "core_set.csv"
LI_STATES = ("LiM_plus", "LiM_2plus")


def _module():
    spec = importlib.util.spec_from_file_location("screen_li_motifs_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _plan_module():
    spec = importlib.util.spec_from_file_location("li_motif_plan_under_test", PLAN_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_rows(path: Path):
    with io.open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _in_main_pairs():
    """(mol_id, name) of the frozen in_main set, in the frozen file order."""
    pairs = []
    for row in _read_rows(PHYSICS_SET):
        if row["in_main"] != "true":
            continue
        pair = (row["mol_id"], row["name"])
        if pair not in pairs:
            pairs.append(pair)
    return pairs


def _plan_rows():
    return _read_rows(PLAN)


def test_screen_module_imports_the_frozen_rule_instead_of_restating_it():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "build_li_motifs" in source, "筛选必须复用冻结的枚举规则，不能另写一套"
    module = _module()
    assert module.RULE_SOURCE.name == "build_li_motifs.py"


def test_screen_refuses_to_run_without_the_registered_plan(monkeypatch, tmp_path):
    module = _module()
    monkeypatch.setattr(module, "PLAN_PATH", tmp_path / "absent.csv")
    with pytest.raises(SystemExit):
        module.load_legs(None)


def test_run_record_matches_the_registered_plan(tmp_path):
    if not RUN_RECORD.is_file():
        pytest.skip("no screen run record registered yet")
    payload = json.loads(RUN_RECORD.read_text(encoding="utf-8"))
    rows = SCREEN_CSV.read_text(encoding="utf-8")
    assert hashlib.sha256(rows.encode("utf-8")).hexdigest() == payload["screen_csv_sha256"]
    modules = _module()
    plan_ids = {row.split(",")[0] for row in PLAN.read_text(encoding="utf-8").strip().splitlines()[1:]}
    assert {entry["record_id"] for entry in payload["legs"]} == plan_ids
    assert payload["n_failed"] == 0
    for entry in payload["legs"]:
        assert len(entry["kept"]) <= modules.MAX_KEEP
        assert entry["parent_naming"] in ("exact", "opt"), entry["record_id"]
        parent = REPO_ROOT / entry["parent_path"]
        assert parent.is_file(), entry["parent_path"]
        for motif in entry["kept"]:
            assert motif["parent_sha256"] == entry["parent_sha256"]
            assert motif["parent_kind"].startswith("state_own")
            assert motif["parent_naming"] == entry["parent_naming"], entry["record_id"]
            assert motif["motif_path"].startswith("work/")


# ---------------------------------------------------------------------------
# 覆盖：12 个 in_main 分子 x 2 个 Li 态 = 24 条腿
# ---------------------------------------------------------------------------
def test_the_plan_covers_every_in_main_molecule_and_both_li_states():
    """计划必须等于冻结的 in_main 集合 x 两个 Li 态，而不是硬编码的 4 分子。"""
    pairs = _in_main_pairs()
    assert len(pairs) == 12, "physics_completion_set.csv must still declare 12 in_main molecules"
    expected = {"%s|%s" % (mol_id, state) for mol_id, _ in pairs for state in LI_STATES}
    rows = _plan_rows()
    assert {row["record_id"] for row in rows} == expected
    assert len(rows) == 24, "12 molecules x 2 Li states = 24 legs"


def test_the_plan_molecule_list_is_derived_from_the_frozen_in_main_set():
    """分子集不能是脚本里另抄一份的常量：必须与 in_main 集合逐条一致。"""
    module = _plan_module()
    assert [tuple(item) for item in module.MOLS] == _in_main_pairs()


def test_every_planned_leg_has_its_own_charge_multiplicity_and_identity():
    """24 条腿逐条真实：q/m 与 pilot 登记一致，未算的腿不许有筛选结论。"""
    pilot = {row["record_id"]: row for row in _read_rows(
        REPO_ROOT / "outputs" / "physics_completion" / "free_states" / "pilot_li_state_energies.csv")}
    for row in _plan_rows():
        evidence = pilot[row["record_id"]]
        assert row["charge"] == evidence["charge"], row["record_id"]
        assert row["multiplicity"] == evidence["multiplicity"], row["record_id"]
        assert row["round0_identity"] == evidence["identity"], row["record_id"]
        # 筛选结论只允许来自运行记录；没有结论时必须留空，不许默认通过
        if row["motif_screen_status"] == "not_computed":
            assert row["screen_verdict"] == "", row["record_id"]
            assert row["screen_kept_motifs"] == "", row["record_id"]
            assert row["screen_parent_current"] == "", row["record_id"]


def test_uncomputed_legs_are_never_reported_as_passing():
    """验收表里「有记录就必须逐腿有结论」这条 check 必须真的在跑，且逐腿为真。"""
    checks = {row["check_id"]: row for row in _read_rows(ACCEPTANCE)}
    assert checks, "acceptance.csv must exist"
    assert all(row["ok"] == "True" for row in checks.values()), \
        [key for key, row in checks.items() if row["ok"] != "True"]
    coverage = checks["covers_every_li_leg_of_the_main_cohort"]
    assert coverage["ok"] == "True"
    assert "24" in coverage["detail"]


# ---------------------------------------------------------------------------
# 执行器：24 条腿逐条解析自己的父几何
# ---------------------------------------------------------------------------
def test_every_planned_leg_resolves_its_own_parent_geometry():
    """执行器必须为每条腿找到该腿自己的生产几何；一条都不能靠兜底默认值。"""
    module = _module()
    unresolved = []
    for row in _plan_rows():
        try:
            path, naming = module.production_geometry(row)
        except SystemExit as exc:  # 找不到几何时执行器直接退出
            unresolved.append((row["record_id"], str(exc)))
            continue
        if not path.is_file():
            unresolved.append((row["record_id"], "missing " + str(path)))
            continue
        assert "Li" in path.read_text(encoding="utf-8"), row["record_id"]
        assert naming in ("exact", "opt"), (row["record_id"], naming)
    assert not unresolved, "legs without a resolvable parent geometry: %r" % (unresolved,)


def test_parent_geometry_is_the_legs_own_and_not_another_states():
    """父几何必须来自该腿自己的 <NAME>/<STATE>/ 目录，禁止跨态借用。"""
    module = _module()
    for row in _plan_rows():
        path, _naming = module.production_geometry(row)
        parts = path.relative_to(REPO_ROOT).parts
        assert parts[:2] == ("work", "wp2prod"), parts
        assert parts[2] == row["name"], (row["record_id"], parts)
        assert parts[3] == row["state"], (row["record_id"], parts)


def test_parent_naming_distinguishes_the_two_on_disk_conventions():
    """两种命名来源都要被真实用到，并且是「同一条腿的同一个几何」而不是借几何。"""
    module = _module()
    namings = {}
    for row in _plan_rows():
        path, naming = module.production_geometry(row)
        namings.setdefault(naming, []).append(row["record_id"])
        stem = row["name"] + "_" + row["state"]
        assert path.name in (stem + ".xyz", stem + "_opt.xyz"), path.name
    assert set(namings) == {"exact", "opt"}, namings
    # 每条腿只解析出唯一一个父几何，不存在两义
    assert sum(len(v) for v in namings.values()) == len(_plan_rows())


def test_the_executor_never_falls_back_to_a_shared_geometry():
    """执行器不得含任何跨腿/共享几何的兜底路径（这正是 4 分子硬编码时代留下的隐患）。"""
    source = SCRIPT.read_text(encoding="utf-8")
    assert "work/audit" not in source, "no shared EMC audit geometry fallback"
    assert "week5/c1" not in source, "no shared week5 frozen-geometry fallback"
    assert "G2Li" not in source, "no shared week-3 frozen-geometry fallback"


def test_charge_and_multiplicity_are_never_taken_from_the_other_li_state():
    """LiM_plus 恒为 1/1，LiM_2plus 恒为 2/2；计划里逐腿钉死。"""
    for row in _plan_rows():
        if row["state"] == "LiM_plus":
            assert (row["charge"], row["multiplicity"]) == ("1", "1"), row["record_id"]
        else:
            assert (row["charge"], row["multiplicity"]) == ("2", "2"), row["record_id"]


def test_screen_run_record_contains_no_leg_outside_the_registered_plan():
    """运行记录里不许有计划外的腿（防止旧 8 腿记录被当成 24 腿记录沿用）。"""
    if not RUN_RECORD.is_file():
        pytest.skip("no screen run record registered yet")
    payload = json.loads(RUN_RECORD.read_text(encoding="utf-8"))
    plan_ids = {row["record_id"] for row in _plan_rows()}
    record_ids = {entry["record_id"] for entry in payload["legs"]}
    assert record_ids <= plan_ids, "run record has legs outside the plan: %r" % (record_ids - plan_ids,)
    if len(plan_ids) == 24 and record_ids == plan_ids:
        assert payload["totals"]["legs"] == 24
