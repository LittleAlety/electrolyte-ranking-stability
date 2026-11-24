"""P6 · 可重复完整隔离重建入口的验证器（Plan action item 6）。

三跑验证：
  A/B 相同输入重复运行 → 逐文件字节一致（科学内容一致）
  C  顺序打乱（STRUCTURES 行序 mirror）→ 规范化后 states/gap_actions/source_index 一致
双向冻结证明：
  全部 INPUTS 前后 sha256 一致；outputs/ 全树前一致；git status（除本目录）前后一致。
输出只进本目录 runs/ 与 p6_verification.json；重建脚本自身带
  ① 内容寻址 run_id ② out.exists() 拒覆盖 ③ 跑后 INPUTS 复核（rebuild:342）。
"""
import hashlib
import io
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = Path(__file__).resolve().parent                      # evidence/p6_isolated_entry/
REPO = HERE.parents[4]                                      # .../电解液溶剂HB-Code
SCRIPT = REPO / "scripts/wp_production/rebuild_strict_isolated.py"
CHILD = HERE / "shuffle_child.py"
RUNS = HERE / "runs"
OUT = HERE / "p6_verification.json"
EXCLUDE_GIT = "docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/p6_isolated_entry"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def input_paths() -> list[Path]:
    sys.path.insert(0, str(SCRIPT.parent))
    import rebuild_strict_isolated as r  # noqa
    paths = list(r.INPUTS)
    corr = REPO / "outputs/physics_completion/recovery/candidate_source_metadata_corrections.jsonl"
    if corr.is_file():
        paths.append(corr)
    return paths


def tree_manifest(root: Path) -> dict:
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            out[p.relative_to(REPO).as_posix()] = sha256(p)
    return out


def git_status() -> list[str]:
    r = subprocess.run(["git", "status", "--porcelain"], cwd=REPO,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return [ln for ln in r.stdout.splitlines() if EXCLUDE_GIT not in ln]


def canon(obj):
    """Order-normalize: sort every list by canonical json repr, recursively."""
    if isinstance(obj, list):
        items = [canon(x) for x in obj]
        return sorted(items, key=lambda x: json.dumps(x, ensure_ascii=False, sort_keys=True))
    if isinstance(obj, dict):
        return {k: canon(v) for k, v in obj.items()}
    return obj


def run_child(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main() -> int:
    before_inputs = {str(p.relative_to(REPO)): sha256(p) for p in input_paths()}
    before_outs = tree_manifest(REPO / "outputs")
    before_git = git_status()

    results = {}
    # --- A / B: identical-input reruns into fresh exclusive bases ---
    for tag in ("a", "b"):
        base = RUNS / tag
        if base.exists():
            for d in base.glob("run_*"):
                import shutil
                shutil.rmtree(d)
        code, log = run_child([sys.executable, str(SCRIPT), "--base", str(base)])
        results["run_" + tag] = {"exit": code, "log_tail": log.strip().splitlines()[-2:]}
        if code != 0:
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return 1
    # --- C: shuffled STRUCTURES row order ---
    base_c = RUNS / "c"
    if base_c.exists():
        import shutil
        for d in base_c.glob("run_*"):
            shutil.rmtree(d)
    code, log = run_child([sys.executable, str(CHILD), "--base", str(base_c)])
    results["run_c_shuffled"] = {"exit": code, "log_tail": log.strip().splitlines()[-2:]}
    if code != 0:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 1

    dirs = {t: next((RUNS / t).glob("run_*")) for t in ("a", "b", "c")}
    names = {t: d.name for t, d in dirs.items()}

    # --- A vs B: byte-identical ---
    fa = {p.relative_to(dirs["a"]).as_posix(): sha256(p) for p in dirs["a"].rglob("*") if p.is_file()}
    fb = {p.relative_to(dirs["b"]).as_posix(): sha256(p) for p in dirs["b"].rglob("*") if p.is_file()}
    ab_identical = fa == fb
    ab_diff = sorted(set(fa) ^ set(fb)) + sorted(k for k in set(fa) & set(fb) if fa[k] != fb[k])

    # --- A vs C: canonicalized scientific content ---
    def load(d, name):
        return json.loads((d / name).read_text(encoding="utf-8"))
    science = {}
    for name in ("states.json", "gap_actions.json", "source_index.json"):
        same = canon(load(dirs["a"], name)) == canon(load(dirs["c"], name))
        science[name] = same

    # --- freeze proofs ---
    after_inputs = {str(p.relative_to(REPO)): sha256(p) for p in input_paths()}
    inputs_unchanged = before_inputs == after_inputs
    after_outs = tree_manifest(REPO / "outputs")
    outputs_unchanged = before_outs == after_outs
    after_git = git_status()
    git_unchanged = before_git == after_git

    payload = {
        "schema": "p6_isolated_rebuild_entry/v1",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "entry": "python scripts/wp_production/rebuild_strict_isolated.py --base <exclusive-dir>",
        "run_ids": names,
        "runs": results,
        "same_input_rerun": {"byte_identical": ab_identical, "diff": ab_diff},
        "order_variation": {"scientific_content_equal": science},
        "freeze": {"inputs_unchanged": inputs_unchanged,
                   "outputs_tree_unchanged": outputs_unchanged,
                   "outputs_files": len(before_outs),
                   "git_status_unchanged_except_p6": git_unchanged},
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    ok = ab_identical and all(science.values()) and inputs_unchanged and outputs_unchanged and git_unchanged
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
