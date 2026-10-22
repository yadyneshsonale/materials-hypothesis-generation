Integrity verified: True. Judged per arm: {'original': 36, 'resample': 36, 'critique': 36, 'self_revise': 36} (expected 36); judge errors 0; critic-incomplete 0; invalid revised citations 0; hidden target sent 0; target-family records in payloads 0.

| Arm | Units judged | Reconstruction (0-4) | Overall (0-4) |
|---|---:|---:|---:|
| original | 36/36 | 1.64 | 1.84 |
| resample | 36/36 | 1.55 | 1.82 |
| critique | 36/36 | 1.49 | 1.64 |
| self_revise | 36/36 | 1.60 | 1.79 |

| A | B | Role | Units | Mean difference (A-B) | 95% CI (papers bootstrap) | Papers A higher / B higher | Sign-test p | Holm p |
|---|---|---|---:|---:|---|---:|---:|---:|
| critique | original | primary | 36 | -0.153 | [-0.361, +0.028] | 2 / 8 | 0.109 | 0.328 |
| self_revise | original | primary | 36 | -0.042 | [-0.104, +0.021] | 3 / 7 | 0.344 | 0.688 |
| critique | self_revise | primary | 36 | -0.111 | [-0.306, +0.069] | 4 / 7 | 0.549 | 0.688 |
| resample | original | noise | 36 | -0.090 | [-0.188, +0.014] | 2 / 8 | 0.109 | n/a (noise) |

| Arm | Records | Statuses | Findings by type | Citation set changed |
|---|---:|---|---|---:|
| critique | 36 | ok: 36 | unsupported: 111, miscited: 42, inconsistent: 26, untestable: 93, implausible: 24, other: 10 | 14 |
| self_revise | 36 | ok: 36 | none | 7 |
