# A3 探针 v2：几何/协议/振型核对（只读）
import hashlib, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = r"E:/Claude Code/电解液溶剂-HB/电解液溶剂HB-Code"
HAND = ROOT + "/docs/handoffs/strict_rebuild_20261103/remote_closure_20261103"

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def read_xyz(p):
    lines = open(p, encoding="utf-8", errors="replace").read().splitlines()
    n = int(lines[0].strip())
    return [(l.split()[0], tuple(float(x) for x in l.split()[1:4])) for l in lines[2:2 + n]]

def cart_blocks(p):
    """ORCA: 'CARTESIAN COORDINATES (ANGSTROEM)' + dashes + rows(元素 x y z)"""
    txt = open(p, encoding="utf-8", errors="replace").read().splitlines()
    blocks = []
    i = 0
    while i < len(txt):
        if "CARTESIAN COORDINATES (ANGSTROEM)" in txt[i]:
            j = i + 1
            while j < len(txt) and set(txt[j].strip()) <= {"-"} and txt[j].strip():
                j += 1
            rows = []
            while j < len(txt):
                parts = txt[j].split()
                if len(parts) == 4:
                    try:
                        rows.append((parts[0], tuple(float(x) for x in parts[1:])))
                    except ValueError:
                        break
                else:
                    break
                j += 1
            if rows:
                blocks.append(rows)
            i = j
        else:
            i += 1
    return blocks

def maxdelta(a, b):
    if not a or not b or len(a) != len(b):
        return None
    if any(x[0] != y[0] for x, y in zip(a, b)):
        return "element-mismatch"
    return max(max(abs(p - q) for p, q in zip(c1, c2)) for (_, c1), (_, c2) in zip(a, b))

def mode6(p, natoms):
    """取 NORMAL MODES 后第一张表中第 6 列；行=3N 分量，行//3=原子序"""
    ncomp = 3 * natoms
    txt = open(p, encoding="utf-8", errors="replace").read().splitlines()
    s = next(i for i, l in enumerate(txt) if l.strip() == "NORMAL MODES")
    for i in range(s, min(s + 400, len(txt))):
        if re.match(r"\s+6\s+7\s+8\s+9\s+10\s+11\s*$", txt[i]):
            vals = {}
            for j in range(i + 1, i + 1 + ncomp + 1):
                parts = txt[j].split()
                if len(parts) == 7 and parts[0].isdigit() and int(parts[0]) < ncomp:
                    vals[int(parts[0])] = float(parts[1])
            if len(vals) == ncomp:
                return vals
            return None  # 表不完整，说明匹配错块
    return None

strict = read_xyz(HAND + "/raw/AN_LiM2plus_job.xyz")
primary = read_xyz(ROOT + "/work/wp2prod/AN/LiM_2plus/AN_LiM_2plus_opt.xyz")
n = len(strict)
print(f"strict(xyz d7d0b63c) vs primary(23d738cf): maxdelta = {maxdelta(strict, primary):.10f} Å")
print("atoms:", [e for e, _ in strict])

files = {
    "anfreq_audit(input=首块)": ROOT + "/work/hpc_anfreq_audit_20261016/tasks/AN/LiM_2plus/run/job.log",
    "anfreq_cohort(input=首块)": ROOT + "/work/hpc_anfreq_cohort_20261016/hpc_runs/AN_LiM_2plus/job.log",
    "superseded_numfreq(末块=Opt末几何)": ROOT + "/work/wp2prod/AN/LiM_2plus/superseded_numfreq/AN_LiM_2plus.log",
    "recovered_3706757(末块=Opt末几何)": HAND + "/raw/74240733bce010708ac42e20e28a15f726eefdf01367a3295c3f608351b7abba.log",
}
for name, p in files.items():
    bl = cart_blocks(p)
    if not bl:
        print(name, "NO BLOCK")
        continue
    first, last = bl[0], bl[-1]
    print(f"{name}: blocks={len(bl)} | first-vs-strict={maxdelta(first, strict)} first-vs-primary={maxdelta(first, primary)} | "
          f"last-vs-strict={maxdelta(last, strict)} last-vs-primary={maxdelta(last, primary)}")

print("\n=== 振型第6列对比（质量加权，行=3N 分量，原子序=行//3）===")
labels = [e for e, _ in strict]
for name, p in [("recovered_3706757(−115.27)", files["recovered_3706757(末块=Opt末几何)"]),
                ("anfreq_audit(+37.07)", files["anfreq_audit(input=首块)"])]:
    m = mode6(p, n)
    if m is None:
        # AnFreq 日志的 NORMAL MODES 可能不同名，退化到频率表后第一张位移表
        print(name, "NORMAL MODES 缺失，尝试 VIBRATIONAL…")
        txt = open(p, encoding="utf-8", errors="replace").read().splitlines()
        cand = [i for i, l in enumerate(txt) if "NORMAL MODE" in l.upper()]
        print("  candidates:", cand[:5])
        continue
    if not m:
        print(name, "no mode table")
        continue
    amp = {}
    for k, v in m.items():
        amp[k // 3] = amp.get(k // 3, 0.0) + v * v
    tot = sum(amp.values())
    shares = ", ".join(f"{labels[a]}{a}:{amp[a]/tot*100:.1f}%" for a in sorted(amp, key=lambda x: -amp[x]))
    # 实际位移（×sqrt(m)）分布
    mass = {"H": 1.008, "C": 12.011, "N": 14.007, "Li": 6.94}
    real = {}
    for k, v in m.items():
        a = k // 3
        u = v * (mass.get(labels[a], 12.0) ** 0.5)
        real[a] = real.get(a, 0.0) + u * u
    rt = sum(real.values())
    rshares = ", ".join(f"{labels[a]}{a}:{real[a]/rt*100:.1f}%" for a in sorted(real, key=lambda x: -real[x]))
    print(f"{name}: 质量加权份额 [{shares}]")
    print(f"{'':>{len(name)}} 实际位移份额 [{rshares}]")
    print("  comp值:", {k: round(v, 4) for k, v in sorted(m.items())})
