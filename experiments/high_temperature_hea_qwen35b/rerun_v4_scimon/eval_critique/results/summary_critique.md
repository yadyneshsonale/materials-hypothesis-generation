Integrity verified: True. Judged per arm: {'original': 12, 'resample': 12, 'critique': 12, 'self_revise': 12} (expected 12); judge errors 0; critic-incomplete 0; invalid revised citations 0; hidden target sent 0; target-family records in payloads 0.

| Arm | Units judged | Reconstruction (0-4) | Overall (0-4) |
|---|---:|---:|---:|
| original | 12/12 | 0.33 | 0.57 |
| resample | 12/12 | 0.27 | 0.55 |
| critique | 12/12 | 0.31 | 0.61 |
| self_revise | 12/12 | 0.33 | 0.55 |

| A | B | Role | Units | Mean difference (A-B) | 95% CI (papers bootstrap) | Papers A higher / B higher | Sign-test p | Holm p |
|---|---|---|---:|---:|---|---:|---:|---:|
| critique | original | primary | 12 | -0.021 | [-0.104, +0.062] | 2 / 3 | 1.000 | 1.000 |
| self_revise | original | primary | 12 | +0.000 | [-0.062, +0.062] | 1 / 1 | 1.000 | 1.000 |
| critique | self_revise | primary | 12 | -0.021 | [-0.104, +0.062] | 2 / 3 | 1.000 | 1.000 |
| resample | original | noise | 12 | -0.062 | [-0.146, +0.021] | 1 / 4 | 0.375 | n/a (noise) |

| Arm | Records | Statuses | Findings by type | Citation set changed |
|---|---:|---|---|---:|
| critique | 12 | ok: 12 | unsupported: 22, miscited: 11, untestable: 34, implausible: 4, other: 4, inconsistent: 1 | 6 |
| self_revise | 12 | ok: 12 | none | 4 |
