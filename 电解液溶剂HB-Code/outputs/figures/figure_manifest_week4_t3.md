# Figure manifest - T3 bare-CPCM dielectric scan (F10)

| figure | file | figure SHA256 | inputs (SHA256) |
| --- | --- | --- | --- |
| F10 | `F10_cpcm_eps_scan.png` | 7a260d2c17e89e0ed988f139f073357169b128a91ab45ed01f502e62d35c7f2a | `t3_cpcm_eps_scan_summary.json` ce04777bf324683526183ef783177073cb70512f94d623b7bd559391706a28d4 | `t3_cpcm_eps_scan.csv` 992f2348ad81a1f3c26c0a00aac2a49ce43905272709656519addb8c1eef75c7 | `p1_core_set.csv` a872f359d93d64ccd97ded9561cf21b6a66917c4d10cfb9b893442c4f067caaa |

F10 note: panel (a) shows the mean of the vertical gas -> bare-CPCM(eps) shift of IP
and EA against the dielectric constant on a log axis, with error bars giving the
population std over the molecules of the subset. The hollow marker at eps = 1 is the
gas-phase P1 reference: the shift is zero there by definition, so eps = 1 is a reference
point and NOT a CPCM calculation. Panel (b) puts sigma_env (left axis, eV) -- the
molecule-to-molecule population std of that shift, which is 0 eV at the gas reference --
next to the Kendall tau-b of the screened ranking against the gas-phase P1 ranking
(right axis, 1.0 at the gas reference). The method (r2SCAN-3c) and the geometry (G1)
are fixed throughout; the only variable is the bare CPCM dielectric, with no SMD
non-electrostatic terms.

- n_molecules: 12, n_jobs: 144, n_ok: 144, n_failed: 0, n_missing: 0
- gas-phase 1-sigma across the subset: IP 0.961 eV, EA 0.562 eV
- generated_utc: 2026-09-29T05:38:41.975735+00:00

Labels are English on purpose (no guaranteed CJK font in the workspace).
