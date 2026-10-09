"""收口七：把本机独立方法审计折进主生成器（一次性补丁）。

读 scripts/wp_production/wp1_audit_src.txt 的分段源码 + work/audit/ 的派生 JSON，拼出 WP1
常量块与新 wp1()，就地替换 scripts/build_physics_completion_batch.py 的 wp1 段落，
把 WP3 的稳健翻转让位给方法审计认证结论，并同步 WP5 成本账本与结题报告口径。
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
GEN = REPO / "scripts" / "build_physics_completion_batch.py"
AUDIT = REPO / "work" / "audit"
SRC = HERE / "wp1_audit_src.txt"

MOLECULES = ["C01", "C02", "C04", "C08", "C13", "C14", "C16", "C17"]
CORES = 4
FIELDS = ["mol_id", "name", "state", "setting_id", "functional", "basis", "has_diffuse",
          "charge", "multiplicity", "orca_keyword", "geometry", "basis_functions",
          "scf_cycles", "final_sp_eh", "terminated", "wall_sec", "status", "qc_flag"]


def _sections():
    text = SRC.read_text(encoding="utf-8")
    parts = {}
    for chunk in text.split("# ==== SECTION: ")[1:]:
        name, _, body = chunk.partition(" ====\n")
        parts[name.strip()] = body.split("\n# ==== END ====")[0].rstrip("\n")
    return parts


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _rows(path):
    return [[str(cell.get(field, "")) for field in FIELDS]
            for cell in _load(path)["cells"]]


def _lit(value):
    return '"%s"' % str(value).replace("\\", "\\\\").replace('"', '\\"')


def _tuples(name, rows):
    body = ["    (" + ", ".join(_lit(value) for value in row) + ")," for row in rows]
    return "\n".join([name + " = ["] + body + ["]"])


def _dicts(name, rows):
    body = ["    {" + ", ".join("%s: %s" % (_lit(key), _lit(value))
                                for key, value in row.items()) + "}," for row in rows]
    return "\n".join([name + " = ["] + body + ["]"])


def collect_cells():
    vertical, relaxed = [], []
    for mol in MOLECULES:
        vertical += _rows(AUDIT / ("%s_audit.json" % mol))
        relaxed += _rows(AUDIT / ("%s_relaxed_audit.json" % mol))
    if len(vertical) != 128 or len(relaxed) != 32:
        raise SystemExit("audit cells incomplete: %d / %d" % (len(vertical), len(relaxed)))
    return vertical, relaxed


def collect_cost(vertical, relaxed):
    cost = []
    for index, row in enumerate(vertical + relaxed, 1):
        cell = dict(zip(FIELDS, row))
        wall = float(cell["wall_sec"] or 0.0)
        cost.append({"job_id": "A%03d" % index, "mol_id": cell["mol_id"], "name": cell["name"],
                     "state": cell["state"], "setting_id": cell["setting_id"],
                     "basis": cell["basis"], "cores": CORES, "wall_sec": "%.1f" % wall,
                     "core_hours": "%.6f" % (wall * CORES / 3600.0),
                     "phase": "orca_audit_single_point"})
    meta = _load(AUDIT / "EMC_Li" / "EMC_m1_G2Li.meta.json")
    wall = float(meta.get("wall_sec") or 0.0)
    cost.append({"job_id": "A%03d" % (len(cost) + 1), "mol_id": "C02", "name": "EMC",
                 "state": "LiM_plus", "setting_id": "EMC_Li_opt", "basis": "r2SCAN-3c",
                 "cores": CORES, "wall_sec": "%.1f" % wall,
                 "core_hours": "%.6f" % (wall * CORES / 3600.0), "phase": "orca_emc_li_opt"})
    if len(cost) != 161:
        raise SystemExit("audit cost ledger size %d != 161" % len(cost))
    return cost, meta


def main():
    parts = _sections()
    vertical, relaxed = collect_cells()
    cost, meta = collect_cost(vertical, relaxed)

    emc_block = json.dumps(meta, ensure_ascii=False, indent=4)
    emc_block = (emc_block.replace(": true", ": True")
                 .replace(": false", ": False").replace(": null", ": None"))
    emc_block = "METHOD_AUDIT_EMC_LI_OPT = " + emc_block

    body_src = "\n".join([parts["BODYA"], parts["BODYB"], parts["BODYC"], parts["BODYD"]])
    new_block = "\n".join([
        parts["HEAD"], "",
        _tuples("METHOD_AUDIT_CELLS", vertical), "",
        _tuples("METHOD_AUDIT_RELAXED_CELLS", relaxed), "",
        emc_block, "",
        _dicts("METHOD_AUDIT_COST", cost),
        "METHOD_AUDIT_JOB_COUNT = len(METHOD_AUDIT_CELLS) + len(METHOD_AUDIT_RELAXED_CELLS) + 1",
        parts["HELPERS"], "", body_src,
    ]) + "\n"

    text = GEN.read_text(encoding="utf-8")
    if "METHOD_AUDIT_CELLS" in text:
        raise SystemExit("generator already carries METHOD_AUDIT_CELLS; refusing to re-patch")

    start = text.index("def wp1():")
    stop = text.index("# Week 39 / WP2")
    marker = text.rindex("# ---", start, stop)
    cut = text.rindex("\n", 0, marker) + 1
    text = text[:cut] + new_block + "\n\n" + text[cut:]

    anchor = "HARTREE_TO_EV = 27.211386245988\n"
    if text.count(anchor) != 1:
        raise SystemExit("HARTREE_TO_EV anchor is not unique")
    text = text.replace(anchor, anchor + "\n" + parts["CERT"] + "\n\n")

    namespace = {}
    exec(parts["PATCHES"], namespace)  # noqa: S102 - trusted local patch table
    for old, new in namespace["PATCHES"]:
        count = text.count(old)
        if count != 1:
            raise SystemExit("patch anchor count=%d for: %s" % (count, old.strip()[:70]))
        text = text.replace(old, new)

    tmp = GEN.with_name(GEN.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="")
    tmp.replace(GEN)
    print("patched %s -> %d bytes" % (GEN.name, len(text.encode("utf-8"))))
    print("audit cells: %d vertical + %d relaxed; cost jobs: %d" % (len(vertical), len(relaxed), len(cost)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
