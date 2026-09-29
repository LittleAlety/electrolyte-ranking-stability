# Gate 1 record

- status: **NOT CLOSED**
- frozen artefacts: 27

## checks

| check | ok | detail |
| --- | --- | --- |
| anchors:validate_anchors | yes | PASS |
| anchors:solution_verified | NO | 31 solution rows are still method=est (needs primary-source check) |
| toolchain:xtb | yes | found |
| toolchain:orca | yes | found |

## blockers

- solution_redox_anchors.csv: 31 rows are estimates without a verified DOI

## sha256

- data/anchors/gas_phase_anchors.csv  a957ef0126efb817d115d4e0ed663207e401e42b5e6e63ffbb78942660c347b0
- data/anchors/solution_redox_anchors.csv  48bb6c0e3fbcc8ef94cc586a3ad40f00869bdd19f43826908057f0cfdb08b213
- data/anchors/README.md  0c458a1bbdb52dd5fbda6f709fc70317a80e3ad478943cd5d62fc3b74a6053f2
- docs/01_stage1_external_anchors.md  5656882885cc4b70ee24020762fecc90b1b6d7aa365573cd04ecbeed76b82250
- docs/02_stage1_method_audit.md  1acf6b547eebfea94595f19bcadc78989bd944fa721b3d2cdabd75d4292d9edb
- src/electrolyte_ranking/toolchain.py  018c82502e051f012a52160da086d4b214e9a44cdbe07d3c6ca9a05a5d50651f
- src/electrolyte_ranking/xtb.py  577f6108a78814ae4fe892484418cd69dd7a4360b98dd222239f899d7ee3cc89
- src/electrolyte_ranking/orca.py  4652ab2648a1d9cf82e66900501f0375df56434fefdf995da1ab76444d2c8988
- src/electrolyte_ranking/provenance.py  1b676a62cf2d6bee1c1a9f097b3c6cfb9278f5973f5933cedcde47f3a361766a
- src/electrolyte_ranking/qc.py  ee421a148c18b788be4c8875e0a77d171ea2123b677daa7b8096391dfd9af154
- scripts/check_environment.py  6df74c4188158cf44643764e2b043d3eec9c40625dc2ec0fe8e0cfa1778a90a3
- scripts/validate_anchors.py  da35617235d7ca11ba6c75da1adad9a3933677dcb797a132667b4a85a1b384fb
- scripts/run_xtb_job.py  5f42df62ecddff5973a8ea64a69586b64477e7f41670fbbfebbb4c68a09e99fb
- scripts/freeze_gates.py  a98a6a1c3ac623ccca9b391f42dc5a169c636e37187bbe8da35849e572dfa45e
- scripts/run_method_audit_xtb.py  f1102602f476bbd3b9aa60dec0e3af491d09922a614ce92c776886d8d21b0827
- docs/04_stage1_xtb_audit_result.md  e9117051e156a51256b1808ebd0404bec7ab575e62e7d3ad317f89ef17ab347d
- outputs/week2/method_audit_xtb.csv  bd5d1f1fd26b5e2b438b8fe0b24725e6178bdab1c413e44b9442a06cf32b5d72
- outputs/week2/method_audit_xtb_summary.json  e6bdf6217f71e2d01e26ee181ee9b71b12fd58558054c82a093fc27678d5ad76
- data/anchors/solution_anchor_verification.md  0c65391dad45f9c579604d335a9ab6719794a4f776edc6ef02e2e06bfa17c2a1
- docs/06_stage1_solution_anchor_audit.md  88c0eb127b29b721fd2fa9f5202bb81e81fc8d5f0ad8f2ad099103d743ad3105
- docs/07_orca_setup_and_runner.md  19cb3f15adf20a085e8e8ea199b3ef256037d4f9a3bbbf8d78f70f46d845461c
- scripts/audit_solution_anchors.py  b5ba44e952bb5c5a6eeec04ccc2e22f4667d1712fe6f6f03d0f54a995425f02f
- scripts/run_orca_job.py  b2d6f1cccb518aee555fc21be96d22cc3925baea36b8f0bcd4f867ae033c8930
- scripts/setup_orca.ps1  810e4e35c58aaa806e574f386f10cdc759e2620bc2ca0dd43223f63ccfb9b1bc
- tests/test_bundled_toolchain.py  6d17132c01bcdd83aa30a247f6a5daed7fc86aa1a01aae8b594855220bddd8e3
- outputs/week2/solution_anchor_audit.csv  8d0bea685fcd111179aeac63822c1d805f1f7e15d01254d76ad9131a9d7bde4f
- outputs/week2/solution_anchor_audit.json  898c92f6f0dde15119bc68b337d679e45af02d9807551f662e2bb2bdb8e87841
