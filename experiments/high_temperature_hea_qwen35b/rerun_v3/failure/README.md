# Experiment 22: failure analysis of the clean rerun (before any new method)

**Date.** 2026-10-24 to 2026-10-25. **Code.** [failure_clean.py](../../../../failure_clean.py).
**Rules.** [must_obey.md](../../../../must_obey.md). **Write-up.** [loop.md](../../../../loop.md), section 1.

## Configuration

- **Input:** all 1,476 judged hypotheses of experiment 21. That is 26 arms on benchmark v3, with the generator
  Llama-3.3-70B (cutoff December 2023).
- **Lever labels (`labels/`):**
  - Labeller: GPT-5.6, which sees the target. This is analysis only; no method sees the labels.
  - Scale: lever match 0 = a different kind of intervention, 1 = same kind, other lever, 2 = same lever,
    3 = the target's intervention.
  - Each target is also given its type (composition change, processing route, simulation study, …).
- **Error codes (`error_codes/`):** fatal-error coding of every hypothesis.
- **Analysis (`analysis.json`):**
  - dimensions;
  - lever-match distribution;
  - reconstruction by lever match;
  - per case;
  - question fit (does the question type fit the target type?);
  - selection headroom (pass@k, best-of-n);
  - per arm and per level;
  - error mix;
  - GPT-5.6 vs DeepSeek agreement.

## Results (F1–F8, loop.md section 1)

- **Intervention reconstruction:** 0.16 of 4. Lever match: 79% a different kind, 15% the same kind, 6% the same
  lever, 0% the target's intervention.
- **Default:** a strong default to composition changes, even when the question names a processing problem.
- **Question fit:** 4 of 12 targets are simulation or characterization studies, but every v3 question asks for "a
  single intervention". No hypothesis for those cases was in the right class (a construction error, fixed in
  experiment 23).
- **Coverage:** coverage, not selection, is the bottleneck. pass@1 0.06, pass@10 0.21; 25 of 36 units have no lever
  hit among 41 hypotheses.
- **Evidence:** it lowers problem alignment (closed-book 2.79 vs evidence arms 2.04–2.40).
- **Fatal errors:** 25% are vague or untestable claims.
- **Judges:** GPT-5.6 vs DeepSeek ρ = 0.39 at hypothesis level.
- **Query levels:** flat (0.45 / 0.48 / 0.48).

## Integrity and limits

- Analysis only; no new generation.
- The labels are produced by the same judge family that scores the outputs.
- The composition-default example CoCrFeNiTi (PMC12298864) is a test-split case. No method rule was derived from
  it.
