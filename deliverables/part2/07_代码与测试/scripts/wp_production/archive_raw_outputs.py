"""把 provenance 里登记的原始作业文件打成**独立可复核的 zip 归档**。

为什么需要它：`outputs/physics_completion/provenance/job_archive_manifest.csv` 只记录
每个作业的路径与 sha256，原始 ORCA / xTB 输出本身在仓库外的 `work/`下。
审阅者要能独立取得并重新解析，就需要这份归档。

归档是**确定性**的：zip 内条目顺序、时间戳固定，同一份 manifest 重建得到同一个 zip。
每个文件在打包前先按 manifest 重算 sha256；不一致或缺失会被报告，不会被静默忽略。

用法：
    .venv\\Scripts\\python.exe -X utf8 scripts\\wp_production\\archive_raw_outputs.py --build
    .venv\\Scripts\\python.exe -X utf8 scripts\\wp_production\\archive_raw_outputs.py --check <zip>
    # --out 可改归档目录（默认 <仓库父目录>/_compute_archive）

与冻结边界：归档不入仓库（zip 放在仓库外的 `_compute_archive/`），仓库内只留这个构建器。
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MANIFEST = REPO / "outputs" / "physics_completion" / "provenance" / "job_archive_manifest.csv"
PROVENANCE_INDEX = REPO / "outputs" / "physics_completion" / "provenance" / "provenance_index.json"
DEFAULT_OUT = REPO.parent / "_compute_archive"
#: 内嵌进归档的登记表副本：这份 zip 对应哪一版 manifest 由它自证，不靠猜。
MANIFEST_ENTRIES = (("_manifest/job_archive_manifest.csv", MANIFEST),
                    ("_manifest/provenance_index.json", PROVENANCE_INDEX))

#: (manifest 列, zip 内后缀)——字典顺序就是输出顺序
PATH_COLUMNS = (("input_path", "inp"), ("start_geometry_path", "start.xyz"),
                ("final_geometry_path", "opt.xyz"), ("raw_output_path", "raw.log"))
FIXED_DATE = (1980, 1, 1, 0, 0, 0)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evidence_digest() -> str:
    if PROVENANCE_INDEX.exists():
        import json
        return json.loads(PROVENANCE_INDEX.read_text(encoding="utf-8")).get("evidence_digest", "")
    return ""


def load_jobs():
    with open(MANIFEST, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def planned_entries(rows):
    """(arcname, abs path, expected sha256, job_id, column) for every registered file."""
    entries, missing = [], []
    for row in rows:
        job = row["job_id"]
        for column, suffix in PATH_COLUMNS:
            rel = (row.get(column) or "").strip()
            if not rel:
                continue
            source = REPO / rel
            digest = (row.get(column.replace("_path", "_sha256")) or "").strip()
            if not source.is_file():
                missing.append((job, rel))
                continue
            arcname = "%s/%s" % (job, Path(rel).name)
            entries.append((arcname, source, digest, job, column))
    entries.sort(key=lambda item: item[0])
    return entries, missing


def build(out_dir: Path) -> int:
    rows = load_jobs()
    entries, missing = planned_entries(rows)
    digest = evidence_digest()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    name = "raw_jobs_%d_%s_%s.zip" % (len(rows), (digest or "nodigest")[:12], stamp)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / name

    mismatches, index_rows, total_bytes = [], [], 0
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for arcname, source, expected, job, column in entries:
            actual = sha256_of(source)
            if expected and actual != expected:
                mismatches.append((job, column, expected, actual))
            info = zipfile.ZipInfo(arcname, date_time=FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with open(source, "rb") as handle:
                zf.writestr(info, handle.read())
            size = source.stat().st_size
            total_bytes += size
            index_rows.append({"job_id": job, "column": column, "arcname": arcname,
                               "sha256": actual, "bytes": str(size)})
        # 登记表本身也进归档：审阅者据此核对「这份 zip 对应哪一版 manifest」，
        # 也让 verify_archive.py 能直接判归档是否过期。
        for arcname, source in MANIFEST_ENTRIES:
            if not source.is_file():
                continue
            actual = sha256_of(source)
            info = zipfile.ZipInfo(arcname, date_time=FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with open(source, "rb") as handle:
                zf.writestr(info, handle.read())
            size = source.stat().st_size
            total_bytes += size
            index_rows.append({"job_id": "_manifest", "column": "manifest",
                               "arcname": arcname, "sha256": actual, "bytes": str(size)})

    index_csv = target.with_suffix(".index.csv")
    with open(index_csv, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["job_id", "column", "arcname", "sha256", "bytes"],
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(index_rows)

    readme = target.with_suffix(".README.md")
    readme.write_text(
        "# 原始作业输出归档（独立于仓库）\n\n"
        "- 来源：`outputs/physics_completion/provenance/job_archive_manifest.csv`\n"
        "- 作业数：%d，文件数：%d，未压缩大小：%.1f MB\n"
        "- evidence_digest：`%s`\n"
        "- 内嵌登记表 `_manifest/job_archive_manifest.csv`：sha256 `%s`（%d 行）\n\n"
        "## 如何复核\n\n"
        "1. 解压；2. 对每个条目重算 sha256，与 `%s` 逐行比对\uff1b\n"
        "3. 与 manifest 的同名 sha256 列再比一次（两处应一致）。\n"
        "4. 判断本归档是否过期：把内嵌的 `_manifest/job_archive_manifest.csv` 与仓库当前那份逐字节比较，\n"
        "   不一致就说明归档早于最新登记，需要重新 `--build`。\n"
        "\n也可直接\uff1a`python scripts/wp_production/archive_raw_outputs.py --check %s`\n"
        % (len(rows), len(entries), total_bytes / 1e6, digest or "(none)",
           sha256_of(MANIFEST) if MANIFEST.is_file() else "(absent)", len(rows),
           index_csv.name, target.name),
        encoding="utf-8", newline="\n")

    print("归档：%s" % target)
    print("  jobs=%d files=%d  %.1f MB -> %.1f MB zip"
          % (len(rows), len(entries), total_bytes / 1e6, target.stat().st_size / 1e6))
    if missing:
        print("  缺失已登记但不在本地的文件：%d" % len(missing))
        for job, rel in missing[:10]:
            print("    - %s %s" % (job, rel))
    if mismatches:
        print("  sha256 不一致：%d" % len(mismatches))
        for job, column, expected, actual in mismatches[:10]:
            print("    ! %s %s %s != %s" % (job, column, expected[:12], actual[:12]))
    return 1 if mismatches else 0


def check(target: Path) -> int:
    rows = load_jobs()
    entries, missing = planned_entries(rows)
    expected = {arcname: (source, digest) for arcname, source, digest, _job, _col in entries}
    # 内嵌登记表也要核：少了它就无从判断这份归档对应哪一版 manifest。
    for arcname, source in MANIFEST_ENTRIES:
        if source.is_file():
            expected[arcname] = (source, sha256_of(source))
    problems = []
    with zipfile.ZipFile(target) as zf:
        names = set(zf.namelist())
        for arcname, (source, digest) in expected.items():
            if arcname not in names:
                problems.append("缺条目 %s" % arcname)
                continue
            actual = hashlib.sha256(zf.read(arcname)).hexdigest()
            if digest and actual != digest:
                problems.append("sha256 不符 %s" % arcname)
        extra = names - set(expected)
        for arcname in sorted(extra)[:10]:
            problems.append("多余条目 %s" % arcname)
    if missing:
        print("提醒：%d 个已登记文件本地缺失（归档只能含本地存在的）" % len(missing))
    if problems:
        print("CHECK FAILED (%d)" % len(problems))
        for item in problems[:20]:
            print("  - %s" % item)
        return 1
    print("CHECK OK -- %d 条目与 manifest sha256 一致" % len(expected))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Independent archive of raw per-job outputs.")
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--check", metavar="ZIP")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args(argv)
    if args.check:
        return check(Path(args.check))
    return build(Path(args.out))


if __name__ == "__main__":
    raise SystemExit(main())
