# Superseded: the suite's web tool agent with a separate web_search tool

These 36 experiment-7 tool-agent runs (and 24 GPT-5.6 judgments) were made with `web_search` as a fifth tool. With
Llama-3.3 on Azure, a tool beyond experiment 7's four breaks the model's tool-call format: it wrote a malformed
submission as text, and the agent fell through to a forced submission, so all 36 runs made no tool call
(experiment 21's KG agent, which also adds a fifth tool, made none in 35 of 36 runs). The design was fixed before any
analysis (loop.md 17.3): experiment 7's four tools are kept, and `search_corpus` also returns live web-search papers.
These runs are kept for the record and are not analysed.
