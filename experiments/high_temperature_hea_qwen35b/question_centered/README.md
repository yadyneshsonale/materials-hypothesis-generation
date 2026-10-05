# Question-centered evidence experiment

This experiment makes scientific question clusters the agent-facing knowledge representation.
Normalized v2 evidence remains behind the interface to ground and validate paper-specific answers.

The automatic pipeline:

1. resolves all 8,848 reader questions against temporally eligible grounded evidence;
2. attaches paper-specific answers with exact source spans;
3. extracts controlled scientific facets;
4. forms coarse domain/topic/property/regime groups;
5. splits coarse groups using scientific-compatibility adjudication;
6. synthesizes agreements, different approaches, condition dependencies, contradictions, gaps,
   hypotheses, and discriminating experiments;
7. builds browser-review data;
8. runs five question-centered temporal ablations over the existing 12 held-out cases; and
9. audits temporal eligibility, test-paper exclusion, work-family exclusion, and citations.

Run detached:

```bash
tmux new-session -d -s mathg-question-centered \
  "cd $(pwd) && bash run_question_centered_experiments.sh"
```

Monitor:

```bash
cat experiments/high_temperature_hea_qwen35b/question_centered/status.json
tail -f experiments/high_temperature_hea_qwen35b/question_centered/logs/pipeline.log
tmux attach -t mathg-question-centered
```

After clusters exist, launch the review interface:

```bash
.venv/bin/python question_review_server.py --host 0.0.0.0 --port 8875
```

The experiment is complete only when `COMPLETE` exists and `status.json` reports
`"state": "complete"`.
