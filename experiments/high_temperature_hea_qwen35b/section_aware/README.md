# Section-aware extraction experiment

This experiment uses validated v2 evidence as scientific triggers, retrieves relevant Methods,
Results, Discussion, figure-caption, and table context from elsewhere in the same paper, and asks
Qwen to generate grounded cross-section questions and research threads.

The factual substrate remains the normalized v2 evidence. Questions are a reasoning and retrieval
interface, not facts.

Run in detached tmux:

```bash
tmux new-session -d -s mathg-section-aware \
  "cd $(pwd) && bash run_section_aware_experiments.sh"
```

Monitor:

```bash
cat experiments/high_temperature_hea_qwen35b/section_aware/status.json
tail -f experiments/high_temperature_hea_qwen35b/section_aware/logs/pipeline.log
```

Canonical outputs:

- `paper_maps/`: deterministic searchable chunk maps;
- `papers/`: validated links, questions, and research threads per paper;
- `results/evaluation.json`: exact-grounding and identifier integrity audit.
