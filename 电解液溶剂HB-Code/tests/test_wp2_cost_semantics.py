from __future__ import annotations

import csv
import importlib.util
import io
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
COST_SCRIPT = REPO / "scripts/wp_production/build_wp2_cost_scenarios.py"
EMIT_SCRIPT = REPO / "scripts/wp_production/emit_wp2.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rows(text):
    return list(csv.DictReader(io.StringIO(text)))


def _closure():
    states = ("M", "M_tzvpd", "M_plus", "LiM_plus", "LiM_2plus")
    return [{"mol_id": "C%02d" % mol, "name": "MOL%02d" % mol, "state": state,
             "basis": "def2-TZVPD", "register_status": "produced_single_conformer"}
            for mol in range(1, 5) for state in states]


def _production(n=45, incomplete=0):
    states = ("M", "M_tzvpd", "M_plus", "LiM_plus", "LiM_2plus")
    rows = []
    for index in range(n):
        mol = index // 5 + 1
        state = states[index % 5]
        is_incomplete = index < incomplete
        rows.append({"mol_id": "C%02d" % mol, "name": "MOL%02d" % mol, "state": state,
                     "core_hours": "" if is_incomplete else "1.25",
                     "wall_sec": "" if is_incomplete else "1125",
                     "cores": "4", "cost_status": "incomplete" if is_incomplete else "complete"})
    return rows


def _absolute(missing=True):
    return [{"item": item, "kind": "absolute", "status": "MISSING" if missing else "measured",
             "value": "" if missing else "1.0", "note": "fixture"}
            for item in ("cpu_core_hours", "p90_job_cost", "frequency_only_cost")]


def test_project_rows_do_not_pollute_registered_pilot_twenty(monkeypatch):
    module = _load(COST_SCRIPT, "cost_scenarios_scope")
    closure = _closure()
    production = _production(45)

    def fake_read(path):
        if path == module.CLOSURE:
            return closure
        if path == module.PRODUCTION:
            return production
        if path == module.COST_LEDGER:
            return _absolute(missing=True)
        return []

    monkeypatch.setattr(module, "read_csv", fake_read)
    outputs = module.build()
    checks = {row["check_id"]: row for row in
              _rows(outputs["outputs/physics_completion/cost/cost_scenario_acceptance.csv"])}
    accounted = checks["every_registered_leg_is_accounted_for"]
    assert accounted["ok"] == "true"
    assert "registered=20 pilot_measured=20 pending=0" in accounted["detail"]
    index = json.loads(outputs["outputs/physics_completion/cost/cost_scenario_index.json"])
    assert index["measured"]["project_legs"] == 45
    assert index["measured"]["registered_pilot_legs"] == 20


def test_generated_cost_row_validator_accepts_explicit_incomplete_not_zero():
    module = _load(EMIT_SCRIPT, "emit_cost_semantics")
    ids = json.dumps([mol_id for mol_id, _name in module.MOLS])
    names = json.dumps(dict(module.MOLS))
    namespace = {}
    exec(module.CONST_PREFIX % (ids, names, json.dumps(["M_tzvpd"]))
         + module.literal([]) + module.POST_CONST, namespace)
    valid = namespace["_wp2_cost_record_valid"]
    assert valid({"cost_status": "complete", "wall_sec": "3600", "cores": "4",
                  "core_hours": "4"})
    assert valid({"cost_status": "incomplete", "wall_sec": "", "cores": "4",
                  "core_hours": ""})
    assert not valid({"cost_status": "incomplete", "wall_sec": "0", "cores": "4",
                      "core_hours": "0"})
    assert not valid({"cost_status": "complete", "wall_sec": "", "cores": "4",
                      "core_hours": ""})


def test_absolute_headlines_fill_only_when_project_loop_and_costs_are_complete():
    module = _load(EMIT_SCRIPT, "emit_absolute_gate")
    ids = json.dumps([mol_id for mol_id, _name in module.MOLS])
    names = json.dumps(dict(module.MOLS))
    namespace = {}
    exec(module.CONST_PREFIX % (ids, names, json.dumps(["M_tzvpd"]))
         + module.literal([]) + module.POST_CONST, namespace)
    gate = namespace["_absolute_cost_gate_ok"]
    missing = _absolute(missing=True)
    filled = _absolute(missing=False)
    assert gate(missing, loop_closed=False, cost_complete=False)
    assert gate(missing, loop_closed=True, cost_complete=False)
    assert not gate(filled, loop_closed=True, cost_complete=False)
    assert gate(filled, loop_closed=True, cost_complete=True)
    assert not gate(missing, loop_closed=True, cost_complete=True)


def test_wp2_progress_is_indexed_and_production_layout_is_registered():
    """`wp2_progress.py` 必须可定位，六分类布局必须是成文的规则。

    取代旧的「wp_production 精确文件数」断言：实现搬到 `scripts/production/<category>/`
    之后目录计数不再是契约（会随新增脚本变化），契约改为
    「每个生产脚本都登记在 registry.json 里，并出现在生成索引与骨架图中」。
    """
    prod_readme = (REPO / "scripts/production/SCRIPT_INDEX.md").read_text(encoding="utf-8")
    legacy_readme = (REPO / "scripts/wp_production/README.md").read_text(encoding="utf-8")
    layout = (REPO / "docs/65_repo_layout.md").read_text(encoding="utf-8")
    assert "`wp2_progress.py`" in prod_readme
    assert "`validation/wp2_progress.py`" in layout
    assert "`wp2_progress.py`" in legacy_readme, "兼容入口索引也要列出 wp2_progress.py"

    registry = json.loads((REPO / "scripts/production/registry.json").read_text(encoding="utf-8"))
    categories = set(registry["categories"])
    assert categories == {"jobs", "ingest", "validation", "ensembles", "analysis", "release"}
    registered = {Path(row["name"]).name for row in registry["scripts"]}
    on_disk: set[str] = set()
    for category in categories:
        on_disk |= {path.name for path in (REPO / "scripts/production" / category).glob("*.py")}
    registered_py = {name for name in registered if name.endswith(".py")}
    assert on_disk == registered_py, "分类目录与 registry.json 不一致：%s" % (on_disk ^ registered_py)
