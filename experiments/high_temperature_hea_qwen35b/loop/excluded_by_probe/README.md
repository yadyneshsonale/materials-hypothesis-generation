# Excluded by the memorisation probe (experiment 34, loop.md 16.1)

These runs are kept for the record and are never judged or analysed.

| Model | Specific recall | Llama-3.3 control, same papers | Excess |
|---|---:|---:|---:|
| o3 | 32.8% | 6.9% | +25.9 points |
| gpt-5 | 43.5% | 6.5% | +37.0 points |

Both exceed the pre-registered threshold of +15 percentage points (loop.md 16.1 addendum), so must_obey.md 2.3
excludes them as generators. Their runs were generated alongside the probe, before its result was known.

The probe gives each model only the title and year of every paper it is eligible for, and GPT-5.6 scores the recall
against the answer key. Results: [review_eval/probe/summary.json](../../review_eval/probe/summary.json).
