# Gate 1 record

- status: **NOT CLOSED**
- frozen artefacts: 30

## checks

| check | ok | detail |
| --- | --- | --- |
| anchors:validate_anchors | yes | PASS |
| anchors:solution_absolute_calibration | NO | 31 solution rows are still method=est; absolute-calibration level recorded as a limitation, not a blocker (docs/31 R7; data/anchors/solution_anchor_verification.md 4.4) |
| anchors:series_rel_ordering | NO | tau_b=0.4286 < 0.90 over n_pairs=21 |
| toolchain:xtb | yes | found |
| toolchain:orca | yes | found |

## blockers

- Gate 1 ordering-consistency tier (R7): tau_b=0.4286 < 0.90 over n_pairs=21

## sha256

- data/anchors/gas_phase_anchors.csv  ee39c5150db8cb7beb2e783e4d8463a2540a913a1125f9d7ee995cebde2d859e
- data/anchors/solution_redox_anchors.csv  802b9b4ac76a36b50dd4b2cbdd4df2a47c7c1bc0546fa052f3e0a614c735ef41
- data/anchors/README.md  41589fa7b50adc66ccea7b5134d44d97b99b27f35e22daae11570c9cbef16463
- docs/01_stage1_external_anchors.md  f7be8e3d969c7e65def890b89efe63939215861463824e2730bcf949537f1617
- docs/02_stage1_method_audit.md  1acf6b547eebfea94595f19bcadc78989bd944fa721b3d2cdabd75d4292d9edb
- src/electrolyte_ranking/toolchain.py  7c11695f8119e1d31be70c5589bb92e2e0d1f9d7339c9f787e8800a89cc04fec
- src/electrolyte_ranking/xtb.py  577f6108a78814ae4fe892484418cd69dd7a4360b98dd222239f899d7ee3cc89
- src/electrolyte_ranking/orca.py  829ddd5fa68d261559b0d4b2265ded4ba1aa6b9851f59af900903b7b9dcb4751
- src/electrolyte_ranking/provenance.py  1b676a62cf2d6bee1c1a9f097b3c6cfb9278f5973f5933cedcde47f3a361766a
- src/electrolyte_ranking/qc.py  ee421a148c18b788be4c8875e0a77d171ea2123b677daa7b8096391dfd9af154
- scripts/check_environment.py  6df74c4188158cf44643764e2b043d3eec9c40625dc2ec0fe8e0cfa1778a90a3
- scripts/validate_anchors.py  53e5ab40d5e2cfd6dbe31aaa8aca79e15cc4f26be214811ba03c52a04d8ef23c
- scripts/run_xtb_job.py  5f42df62ecddff5973a8ea64a69586b64477e7f41670fbbfebbb4c68a09e99fb
- scripts/freeze_gates.py  e0052dabac99a6bc5921f690c53d571bb47def61ecbfb8dd985fe1e5087bd4eb
- scripts/run_method_audit_xtb.py  f1102602f476bbd3b9aa60dec0e3af491d09922a614ce92c776886d8d21b0827
- docs/04_stage1_xtb_audit_result.md  19cca3fc7a80296d500c5a0418ea9566033613969e63af116518a64b71ff321b
- outputs/week2/method_audit_xtb.csv  a43eca8386c10a80b44917756fcc718c7b040b20a6854b549a2372a6bcd5480c
- outputs/week2/method_audit_xtb_summary.json  e6bdf6217f71e2d01e26ee181ee9b71b12fd58558054c82a093fc27678d5ad76
- data/anchors/solution_anchor_verification.md  da8da092a58d2d3eeb1fb4002dfd73c80c1f4069e27b2e77e554dcd7e504931c
- docs/06_stage1_solution_anchor_audit.md  9e5dfc80e0d40f516140b7f75c6b3146165e088b2d29ae2b8a71b34d58c68e5c
- docs/07_orca_setup_and_runner.md  45d9d8401fe10d1dd8510e46f80984f908e0c15900a5b0be43f18bdf1ee85b4f
- scripts/audit_solution_anchors.py  d8258e07ca72925de898af5f0fb8c356d5da89f58df6b26c347e88c822f124c8
- scripts/run_orca_job.py  3ac3e5391f7292b4ea52d4ca7e074e414a2db75be2d6e8ac67423bd7e4527b74
- scripts/setup_orca.ps1  810e4e35c58aaa806e574f386f10cdc759e2620bc2ca0dd43223f63ccfb9b1bc
- tests/test_bundled_toolchain.py  6d17132c01bcdd83aa30a247f6a5daed7fc86aa1a01aae8b594855220bddd8e3
- outputs/week2/solution_anchor_audit.csv  619461ef8f2ee6a74e73d0a2829d436c968af6a8f88497e4d3654a8677a5add2
- outputs/week2/solution_anchor_audit.json  bec6f71270fac92066cfe1cc9239e012d2e595f48c84fa1ec233d3b111e34719
- data/anchors/within_series_ordering.csv  bd54233799154343c1f8da3cf3e753588f593d159c4098dd086cf50efe57f2c5
- scripts/check_series_rel_ordering.py  df65bda7c4122e7fb47d87c454b3ac420e75aa516bdef39951bc3990d8186754
- outputs/week2/series_rel_ordering_check.json  c79e2a34e6df7aafa5f39fef2af475823507e2c83cfac8053ea5a384fd257e25
