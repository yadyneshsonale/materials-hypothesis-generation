# Experiment 41: raising the score from the failure points (a complete-study writer)

**Plan.** [loop.md](../../../loop.md) section 22 (22.1 failure analysis, offline checks and pre-registered plan).
**Code.**
- The writers (`STUDY_TYPES_GUIDE`, `STUDY_DESIGN_GUIDE`, `WRITER_STUDY`) at the end of
  [loop_methods.py](../../../loop_methods.py), tested in [test_study.py](../../../test_study.py).
- Offline selection checks: [select_offline.py](../../../select_offline.py).
- Analysis: [study_analysis.py](../../../study_analysis.py).

**Runner.** [loop/run_study.sh](../loop/run_study.sh). **Report.** `analysis_study.md` and `analysis_study.json`.

## Failure points of the best method (`writer_only_b_o3mini`)

- **The intervention is where most points are lost:** 3.69 of 4.
- **Blind spots by study type** (the share of runs matching the paper's lever):
  - processing-route papers (22% of runs): 2%;
  - simulation papers (11%): 0%, with a score of 0.48;
  - coating papers: 12%.
- **Missing study design.** Answer keys name the processing or treatment route in 58% of interventions, hypotheses
  in 28%.
- **Judge criticisms:** conditions in 86% of runs, vagueness in 75%.

## Offline: selection cannot beat the writer

[../loop_select/offline/](../loop_select/offline/) holds the results for 15,600 judged, target-free o3-mini hypotheses (116 per unit). The pool itself is rebuilt with `python select_offline.py pool`. The best per unit averages
1.28, but no target-free rule finds it:

| Rule | vs the writer (GPT-5.6) |
|---|---|
| Literature support (BM25 against corpus abstracts) | −0.07 |
| Consensus | −0.01 |
| Leave-one-paper-out learned reranker | +0.005 [−0.05, +0.06] |

The writer already sits at the consensus level.

## Configurations (270 runs each: 45 papers × 3 levels × 2 samples; o3-mini, 1 call)

| Configuration | The incumbent writer (WRITER_B) plus | Evidence |
|---|---|---|
| `writer_study_b_o3mini` (primary) | study types + study design | none |
| `writer_types_b_o3mini` | study types (consider processing routes, coatings, microstructure, simulation, characterisation) | none |
| `writer_design_b_o3mini` | study design (processing route, treatment, test conditions; general mechanism; outcome direction vs the baseline) | none |
| `web_study_64k_b_o3mini` | study types + study design | the 64,000-character web pack |

## Results

Full tables: [analysis_study.md](./analysis_study.md). Statistics and interpretation:
[loop.md](../../../loop.md) 22.2. Exploratory, because all 45 papers are spent.

| Configuration | GPT-5.6 | vs baseline [CI] | DeepSeek | Lever ≥ 2 | Names a route |
|---|---:|---|---:|---:|---:|
| `writer_only_b_o3mini` (same session) | 0.632 | – | 0.575 | 19% | 27% |
| `writer_study_b_o3mini` | 0.601 | −0.031 [−0.08, +0.01] | 0.538 | 12% | 50% |
| `writer_types_b_o3mini` | 0.632 | −0.000 [−0.03, +0.03] | 0.525 | 13% | 46% |
| `writer_design_b_o3mini` | 0.614 | −0.019 [−0.06, +0.02] | 0.544 | 17% | 44% |
| `web_study_64k_b_o3mini` (vs `web_text_64k_b_o3mini`, 0.631) | 0.606 | −0.025 [−0.07, +0.02] | 0.630 | 20% | 54% |

- **No configuration raises the score.** The guides make the hypotheses describe complete studies, and they raise
  conditions (types) and outcome (design). But they pull the model away from its own best guess, so intervention
  agreement falls.
- **The blind spots remain.** Processing-route and simulation papers stay near 0% lever match.
- **Quality without the answer key.** All three judges prefer the complete-study writer: +0.20 to +0.32.
- **Together with the offline selection checks:** the closed-book writer is at the ceiling for target-free methods.
