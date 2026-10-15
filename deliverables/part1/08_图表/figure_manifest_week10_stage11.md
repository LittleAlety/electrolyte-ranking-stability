# Figure manifest - Week 10 / Stage 11 (F20, F21)

| figure | file | figure SHA256 | inputs (SHA256) |
| --- | --- | --- | --- |
| F20 | `F20_sigma_anatomy.png` | 96410e63e55061f9295cc74f982520ffcc8d7482433b36b1e2482e912fa79b2b | `stage11_sigma_anatomy.json` 0057eab40133c3e18a7afbaa37ccb5be97a4512c87014fb98f544f97d90b1290 |
| F21 | `F21_sigma_controls.png` | 41e8a4bee94412a986b33a57301147da64128cf9b7912ec57ba66b74652bb9e1 | `stage11_sigma_anatomy.csv` 6aee2149eb639f848a2230995d308060d99d8b833cfa3299ec30e6255205a317 |

Common-10 subset only, one row per (rung, axis), ten points in total.

F20 panel (a): verified identity T1, maximum absolute error 1.11e-15 eV over all
pairs of all ten points. sigma_ij is the *difference* of the per-molecule
shift, so sigma carries no information about the size of the shift at all.

F20 panel (b): the ten per-rung secant-slope distributions
q_ij = abs(delta_i - delta_j)/abs(dP_ij), with the two critical slopes
sqrt(2)/z = 1.414 (z=1) and 0.722 (z=1.96). A pair is resolved exactly when
its slope stays below the line.

F20 panel (c): T4 checked at both thresholds; maximum absolute error 0.0e+00,
i.e. exact. The twenty points split into 0 at f = 0, 0 at f = 1 and 20
strictly in between, which is why the closed form is a real statement and
not a restatement of the data.

F20 panel (d): AUC of every cheap single-variable predictor of a top-2
shortlist rewrite. The signed slope `ols_slope_b` reaches 1.000 with exact
permutation p = 0.0083 (1/120 over 10 points with 3 positives), while its
absolute value `abs_ols_slope_b` reaches only 0.905. The two unsigned
magnitude proxies are weaker: `q_median` 0.857 and `sd(delta)` 0.810.

F21 panel (a): the linear-shift phase diagram. With delta = b*(target - mean)
every secant slope equals abs(b) exactly (max deviation 4.4e-16), so tau_b flips
sign at b = -1 and f_unresolved steps from 0 to 1 at abs(b) = sqrt(2)/z.
The diagram is the closed form of the whole resolved/unresolved machinery.

F21 panel (b): a shift that is monotone and f-Lipschitz with f <= 1 keeps
tau_b = 1.000 and f_unresolved = 0.000 at every amplitude, with q_max = f
exactly. Monotonicity alone is not sufficient; the Lipschitz constant is
what T4 charges for.

F21 panel (c): rigid inter-layer offsets are free (max abs(d tau_b) = 0e+00),
while inflating the shift pushes f_unresolved towards 1 without moving tau_b,
and per-molecule white noise degrades tau_b. This is why the week-9
observation f_robust_inv = 0 everywhere must be read together with
f_unresolved and never on its own.

F21 panel (d): tau_b when N molecules are drawn at random from the
18-molecule population, band = p05..p95, star = the common-10 subset,
plus = the full population. The reported tau_b of a rung depends on the
subset at the +/-0.1 level for N ~ 10, which is the same order as several
of the rung-to-rung differences quoted in weeks 4-9.

Palette and dpi follow the other week figures (warm/cool pair for the
oxidation/reduction axes, dpi = 160, bbox_inches = tight).

`stage11_summary.md` is the narrative companion of these figures.
