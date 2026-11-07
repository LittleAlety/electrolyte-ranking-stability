import sys
sys.path.insert(0,'E:/Claude Code/电解液溶剂-HB/电解液溶剂HB-Code/scripts')
sys.path.insert(0,'E:/Claude Code/电解液溶剂-HB/电解液溶剂HB-Code/src')
import analyze_stage11_sigma_anatomy as A
lad = A.load_ladder()
pop = sorted(set(lad["P0_to_P1"]) & set(lad["P1_to_P2"]))
print("population", pop, len(pop))
rec = A.subset_drift(lad, "P0_to_P1", "ox", pop, draws=2000)
for r in rec:
    print(r["n"], repr(r["tau_b_std"]), repr(r["tau_b_mean"]), r["tau_b_p05"], r["tau_b_p95"], r["n_draws"])