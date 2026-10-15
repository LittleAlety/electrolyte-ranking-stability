# figure_manifest_week24_corealign

| figure | sha256 | size |
| --- | --- | --- |
| `F48_ml_direct_vs_shift.png` | `76dfcce7eb7d0ec1e30eb1e5c198ab771b1d376016bef1246958057dc5724672` | 157638 B |
| `F49_al_budget.png` | `7f50d469c58da9bf3fd494235e2f72ff003c839e42c188a7cfe0c0e88fe1de85` | 106588 B |
| `F50_decision_metrics.png` | `d4b4543bc851a4242cd88a69eb2e723cba8f9f2ce0f64e155aaf5518bc32dbeb` | 135427 B |
| `F51_minimal_budget_flowchart.png` | `857dc62df65b1cb19cd5ea1c4305a37a408065b7a25f24dccdbb368d2ab2647d` | 499599 B |

| input | sha256 |
| --- | --- |
| `outputs/week24_corealign/ml_direct_vs_shift.json` | `91128346e8d146b7b06426290da520e46ccb36a7412e36aadbcf840ea3e7c8ba` |
| `outputs/week24_corealign/al_budget.json` | `d4af49ca5dfee2de3528f9148e85c2c6eae9138a5abdce00dead6fa813007598` |
| `outputs/week24_corealign/decision_metrics.json` | `27af61760ba7670d30be784e7a2ae9ab56680ee3c6faaeba98486ed7734e0fd3` |
| `outputs/week24_corealign/core_alignment.json` | `71878ff801dd81fa0f1fee93b0f42b5da5eeb030c3902c7e391239e30d9fd984` |
| `outputs/week24_corealign/audit_tables.json` | `60947a47af12ffbcf057294c19fbc2537a7ac517618a5641ea545ecaf1d620d1` |
| `outputs/week9/stage10_ladder.json` | `3eb6b36d5622ec0e3147dd827a6437aabac2ea38c53936fddc974e85376ac3cf` |
| `outputs/week22_hardening/broad_pool_demo.json` | `670d067f8b74380f258d52e03c658d1c86bc233c526a35d77097101fa34fc6f0` |
| `outputs/week23/targeted_two_guess.json` | `c6ca4fbbdd50c79e82a9251a69916c75cd29e288f9f571971da8ebf22b14756a` |
| `outputs/week22/dielectric_limit.json` | `bef5d38096beb2d2baa07dacaf5884090139d41af0e1042408a22b4d0f278002` |
| `outputs/week4/p1_core_set_audit.json` | `d796fcfd4477ec7be9cdcf6951f2980a2b9c3252e4a08a5346f32c7088809a48` |
| `outputs/week7/stage8_al_results.json` | `d2a6298cb47f604a32b0fb92f9b7812cfe1475b03417317e15ed54f71aa069fd` |
| `outputs/week10/stage11_sigma_anatomy.json` | `0057eab40133c3e18a7afbaa37ccb5be97a4512c87014fb98f544f97d90b1290` |
| `outputs/week9/stage10_ladder.csv` | `c4cdec417373fcd6dfb63221bc4d7a727c65a563c4923e5a433b0048bbb9ea6e` |

Generate (from the repository root):

```powershell
& $py scripts\analyze_w24_ml.py          # F48
& $py scripts\analyze_w24_al.py          # F49
& $py scripts\analyze_w24_decision.py    # F50
& $py scripts\make_w24_flowchart.py      # F51
```

F48-F50 come from the W24-C distillation of the Stage 7 / Stage 8 / Stage 9-10 products.
F51 is the minimal-information-budget decision flowchart; it resolves every number it
shows by dotted path from the JSON products above (`--check` prints the resolved table
plus the sha256 of each file, including the three transitive hops it declares).

The PNGs carry no timestamp, so re-running on the same inputs gives byte-identical files.
`make_w24_flowchart.py` additionally refuses to save when matplotlib reports a missing
glyph, so a CJK font regression cannot silently ship a figure full of boxes.
