# High-recall reader-question generation

This pass models the stream of questions an attentive materials scientist asks while reading. It
does not restrict a paper to a few hypothesis-planning questions and does not filter questions by
immediate usefulness. Filtering occurs later through type, intent, relevance, and text controls.

## Processing steps

1. **Read an overlapping passage.** The XML-derived paper text is split into approximately
   450-word windows with 50-word overlap. References and non-content end matter are excluded.
2. **Carry reading state.** Each call receives the paper title, reading position, current section,
   the preceding passage tail, and the 12 most recent questions. This supports follow-on thought
   and discourages exact repetition.
3. **Generate broadly.** Qwen asks multiple questions about terminology, choices, methods,
   mechanisms, evidence, comparisons, relevance, changed variables, boundaries, assumptions,
   limitations, transfer, replication, and follow-up work.
4. **Ground locally.** Every question must quote one exact contiguous evidence span from the
   current passage. Context state can guide continuity but cannot serve as evidence.
5. **Validate deterministically.** The pipeline checks syntax, type, reading step, intent,
   relevance tier, confidence, and exact source grounding. Invalid model items are retained in a
   rejection audit rather than silently accepted.
6. **Preserve high recall.** Only exact duplicate questions from overlapping chunks are removed.
   Near-duplicates and exploratory questions remain available for later human or automated
   filtering. Questions are linked to reconciled roles when their evidence overlaps.

## Stored question fields

- `question`
- `question_type`
- `reading_step`
- `reader_intent`
- `relevance`
- `rationale`
- `source_section`
- `chunk_index`
- `grounded_role_refs`
- one exact `evidence_span`
- `confidence`

Chunk checkpoints are written atomically. A resumed run reuses completed chunks only when both the
paper source hash and chunk hash match, so interruption does not require repeating successful
model calls.
