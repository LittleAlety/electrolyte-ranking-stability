"""Isolated eight-state coverage with the full terminal obligation view retained."""
from __future__ import annotations

from pathlib import Path as _ReorgPath
import sys as _reorg_sys

_reorg_sys.path.insert(0, str(_ReorgPath(__file__).resolve().parents[1]))
import _paths  # noqa: F401,E402  (仓库根 + scripts/production/* 注册到 sys.path)

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_coverage_generator_strict_sandbox as base

ROOT = _paths.REPO_ROOT
OUT = ROOT / "docs/handoffs/strict_rebuild_20261103/remote_closure_20261103/eight_admission_v2"


def main():
    base.OUT = OUT
    base.main()
    states = {s["state_key"]: s for s in json.loads((base.RUN / "states.json").read_text(encoding="utf-8")) if s["strict_kept"]}
    sources = json.loads((base.RUN / "source_index.json").read_text(encoding="utf-8"))
    current = [a for a in sources["member_sources"] if a["is_current_attempt"]
               and a["member_key"].rsplit("|", 1)[0] in states]
    originals = base.read(base.STRUCT)
    dispositions_path = ROOT / "outputs/physics_completion/ensembles/production_ensemble_dispositions.csv"
    dispositions = {r["member_key"]: r for r in base.read(dispositions_path)}
    qualified = base.read(base.gen.STRUCT)
    sandbox_struct = base.gen.STRUCT.with_name("production_ensemble_structures_with_terminal.csv")
    qualified_keys = {r["member_key"] for r in qualified}
    obligation_rows = []
    for audit in current:
        key = audit["member_key"]
        row = next(r for r in originals if r["member_key"] == key and r["attempt"] == audit["attempt"])
        source_disposition = dispositions.get(key)
        if source_disposition and source_disposition["log_sha256"]:
            assert source_disposition["log_sha256"] == row["log_sha256"], key
        original_status = row["status"]
        isolated_status = original_status
        if key not in qualified_keys:
            row = dict(row)
            if original_status == "computed" or row["member_role"] == "primary":
                isolated_status = "strict_evidence_incomplete"
                row["status"] = isolated_status
            row["note"] += ";isolated_only_historical_status=" + original_status
            qualified.append(row)
        obligation_rows.append({"member_key": key, "attempt": audit["attempt"],
                                "historical_status": original_status, "isolated_evidence_status": isolated_status,
                                "strict_eligible": audit["eligible"], "strict_reasons": audit["reasons"],
                                "historical_disposition": source_disposition,
                                "log_path": row["log_path"], "log_sha256": row["log_sha256"]})
    base.write(sandbox_struct, qualified, list(originals[0]))
    base.gen.STRUCT = sandbox_struct
    rows = base.gen.build_rows(strict_scope=True)
    kept_keys = {mk for s in states.values() for mk in s["strict_kept"]}
    for row in rows:
        assert set(filter(None, row["kept_pool_evidence"].split(";"))) <= kept_keys
    assert len(rows) == 8
    (OUT / "full_obligation_generator_8.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    (OUT / "member_terminal_dispositions.json").write_text(json.dumps(obligation_rows, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    # A file outside the repository (e.g. a sandbox built outside ROOT) must not crash
    # the manifest; it is recorded under its absolute POSIX path so it cannot be
    # mistaken for a repository-relative one.  (2026-11-04, Lead-2 switch prep)
    def _manifest_key(p: Path) -> str:
        try:
            return p.relative_to(ROOT).as_posix()
        except ValueError:
            return p.resolve().as_posix()

    manifest = {_manifest_key(p): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (sandbox_struct, dispositions_path, Path(__file__), Path(base.gen.__file__))}
    (OUT / "terminal_input_sha256.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({r["name"]+"|"+r["state"]:r["route"] for r in rows}, ensure_ascii=False))


if __name__ == "__main__":
    main()
