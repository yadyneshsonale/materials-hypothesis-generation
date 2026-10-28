"""Round 4 (loop.md 19): likelihood scores of candidate hypotheses under a local pre-cutoff language model.

Runs in a separate environment with a V100-compatible PyTorch (the project's .venv has a CUDA 13 build). For every
candidate c of a question q it computes, with token log-probabilities summed over the scored span:
  forward:  log P(c | q) and log P(c)      -> pmi_sum = log P(c | q) - log P(c), pmi_mean = per-token version
  backward: log P(q | c) and log P(q)      -> channel = log P(q | c) - log P(q)  (noisy-channel reranking)
Resumable: candidates already in the output file are skipped. Target-free: it reads only the question and the
candidate text.

Usage: python round4_pmi.py <pool.jsonl> <scores.jsonl> [--model meta-llama/Llama-3.2-3B] [--gpu-gb 11]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

FORWARD_COND = "Research question: {q}\n\nProposed study and expected result: "
FORWARD_FREE = "Proposed study and expected result: "
BACKWARD_COND = "Proposed study and expected result: {c}\n\nThe research question this study answers: "
BACKWARD_FREE = "The research question this study answers: "


def pick_gpu() -> int:
    out = subprocess.run(["nvidia-smi", "--query-gpu=index,memory.free", "--format=csv,noheader,nounits"],
                         capture_output=True, text=True, check=True).stdout
    free = [(int(f), int(i)) for i, f in (line.split(",") for line in out.strip().splitlines())]
    return max(free)[1]


class Scorer:
    def __init__(self, model_name: str, gpu_gb: float) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch = torch
        gpu = pick_gpu()
        self.device = torch.device(f"cuda:{gpu}")
        total = torch.cuda.get_device_properties(gpu).total_memory
        torch.cuda.set_per_process_memory_fraction(min(1.0, gpu_gb * 2**30 / total), gpu)  # never crowd other jobs
        self.tok = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name, dtype=torch.float16).to(self.device).eval()
        self.bos = [self.tok.bos_token_id] if self.tok.bos_token_id is not None else []
        self.gpu = gpu

    def ids(self, text: str) -> list[int]:
        return self.tok(text, add_special_tokens=False)["input_ids"]

    def logprob(self, prefix: str, target: str) -> tuple[float, int]:
        """Sum of log P(target tokens | BOS + prefix) and the number of target tokens."""
        torch = self.torch
        p, t = self.bos + self.ids(prefix), self.ids(target)
        x = torch.tensor([p + t], device=self.device)
        with torch.no_grad():
            logits = self.model(x).logits[0, len(p) - 1:-1].float()
            lp = torch.log_softmax(logits, dim=-1).gather(1, torch.tensor(t, device=self.device)[:, None]).sum()
        return float(lp), len(t)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("pool")
    parser.add_argument("out")
    parser.add_argument("--model", default="meta-llama/Llama-3.2-3B")
    parser.add_argument("--gpu-gb", type=float, default=11.0)
    args = parser.parse_args()
    rows = [json.loads(line) for line in Path(args.pool).read_text().splitlines()]
    done = set()
    if os.path.exists(args.out):
        done = {json.loads(line)["run_id"] for line in Path(args.out).read_text().splitlines() if line.strip()}
    todo = [r for r in rows if r["run_id"] not in done]
    scorer = Scorer(args.model, args.gpu_gb)
    print(f"[pmi] {len(todo)} to score on cuda:{scorer.gpu} with {args.model}", flush=True)
    free_q: dict[str, tuple[float, int]] = {}
    with open(args.out, "a") as f:
        for n, r in enumerate(todo, 1):
            q, c = r["question"], r["text"]
            cond, nc = scorer.logprob(FORWARD_COND.format(q=q), c)
            free, _ = scorer.logprob(FORWARD_FREE, c)
            back, nq = scorer.logprob(BACKWARD_COND.format(c=c), q)
            if q not in free_q:
                free_q[q] = scorer.logprob(BACKWARD_FREE, q)
            f.write(json.dumps({"run_id": r["run_id"], "model": args.model, "tokens_c": nc, "tokens_q": nq,
                                "logp_cond": cond, "logp_free": free, "logp_cond_mean": cond / nc,
                                "pmi_sum": cond - free, "pmi_mean": (cond - free) / nc,
                                "channel": back - free_q[q][0]}) + "\n")
            if n % 200 == 0:
                f.flush()
                print(f"[pmi] {n}/{len(todo)}", flush=True)


if __name__ == "__main__":
    main()
