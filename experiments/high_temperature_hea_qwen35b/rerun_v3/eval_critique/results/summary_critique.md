Integrity verified: False. Judged per arm: {'original': 36, 'resample': 35, 'critique': 36, 'self_revise': 36} (expected 36); judge errors 0; critic-incomplete 0; invalid revised citations 0; hidden target sent 0; target-family records in payloads 0.

| Arm | Units judged | Reconstruction (0-4) | Overall (0-4) |
|---|---:|---:|---:|
| original | 36/36 | 0.40 | 0.76 |
| resample | 35/36 | 0.36 | 0.69 |
| critique | 36/36 | 0.35 | 0.87 |
| self_revise | 36/36 | 0.38 | 0.76 |

| A | B | Role | Units | Mean difference (A-B) | 95% CI (papers bootstrap) | Papers A higher / B higher | Sign-test p | Holm p |
|---|---|---|---:|---:|---|---:|---:|---:|
| critique | original | primary | 36 | -0.049 | [-0.090, -0.007] | 1 / 6 | 0.125 | 0.375 |
| self_revise | original | primary | 36 | -0.021 | [-0.090, +0.042] | 4 / 5 | 1.000 | 1.000 |
| critique | self_revise | primary | 36 | -0.028 | [-0.083, +0.035] | 2 / 7 | 0.180 | 0.375 |
| resample | original | noise | 35 | -0.031 | [-0.153, +0.094] | 4 / 6 | 0.754 | n/a (noise) |

| Arm | Records | Statuses | Findings by type | Citation set changed |
|---|---:|---|---|---:|
| critique | 36 | ok: 36 | unsupported: 83, untestable: 117, implausible: 13, miscited: 33, inconsistent: 13, other: 2 | 13 |
| self_revise | 36 | ok: 36 | none | 7 |
