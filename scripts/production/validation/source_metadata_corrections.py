"""Append-only source metadata corrections, bound to original evidence bytes."""

from pathlib import Path as _ReorgPath
import sys as _reorg_sys

_reorg_sys.path.insert(0, str(_ReorgPath(__file__).resolve().parents[1]))
import _paths  # noqa: F401,E402  (仓库根 + scripts/production/* 注册到 sys.path)

import json
from pathlib import Path


def effective_protocol(candidate, old_value, source_sha256, correction_path: Path):
    applied = []
    value = old_value
    if correction_path.is_file():
        for line in correction_path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            if record["candidate"] != candidate:
                continue
            if record["source_sha256"] != source_sha256 or record["old_value"] != value:
                raise ValueError("metadata correction does not match original source")
            value = record["new_value"]
            applied.append(record["correction_id"])
    return {"original": old_value, "effective": value, "correction_ids": applied,
            "c3_i": "CLOSED_UNAPPROVED_EQUIVALENCE_RULE"}
