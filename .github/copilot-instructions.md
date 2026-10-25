# Instructions for every agent and every prompt in this repository

Before doing anything, read [must_obey.md](./must_obey.md) and follow it. It defines the benchmark, which models
may see a query (knowledge cutoff before the held-out papers), how queries and evidence are kept free of answer
leakage, the dev/test discipline, and how results must be evaluated and recorded. Method work is logged in
[loop.md](./loop.md). Run `python must_obey_check.py <run_dir>` before reporting any result.
