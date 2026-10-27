Integrity verified: True. Judged per arm: {'original': 36, 'resample': 36, 'critique': 36, 'self_revise': 36} (expected 36); judge errors 0; critic-incomplete 0; invalid revised citations 0; hidden target sent 0; target-family records in payloads 0.

| Arm | Units judged | Reconstruction (0-4) | Overall (0-4) |
|---|---:|---:|---:|
| original | 36/36 | 0.35 | 0.67 |
| resample | 36/36 | 0.28 | 0.62 |
| critique | 36/36 | 0.43 | 0.89 |
| self_revise | 36/36 | 0.38 | 0.75 |

| A | B | Role | Units | Mean difference (A-B) | 95% CI (papers bootstrap) | Papers A higher / B higher | Sign-test p | Holm p |
|---|---|---|---:|---:|---|---:|---:|---:|
| critique | original | primary | 36 | +0.076 | [+0.000, +0.153] | 7 / 3 | 0.344 | 1.000 |
| self_revise | original | primary | 36 | +0.021 | [-0.042, +0.083] | 5 / 4 | 1.000 | 1.000 |
| critique | self_revise | primary | 36 | +0.056 | [-0.042, +0.153] | 7 / 4 | 0.549 | 1.000 |
| resample | original | noise | 36 | -0.069 | [-0.111, -0.028] | 1 / 8 | 0.039 | n/a (noise) |

| Arm | Records | Statuses | Findings by type | Citation set changed |
|---|---:|---|---|---:|
| critique | 36 | ok: 36 | unsupported: 75, inconsistent: 9, untestable: 108, miscited: 32, implausible: 10, other: 8 | 12 |
| self_revise | 36 | ok: 36 | none | 14 |
