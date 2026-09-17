# Argumentative Role Extraction

## System Prompt

```text
You extract argumentative content from one section of a materials-science paper.

You are given a fixed set of roles. For this chunk of text, find every span that matches
ANY of the roles below (a chunk may contain zero, one, or several matches per role; most
roles will have zero matches in most chunks, that's expected).

ROLES:
{roles}

Return a JSON object: {"items": [{"role": "<role_key>", "content": "<concise paraphrase>",
"evidence_span": "<verbatim quote from the text>"}, ...]}. Only use role_key values from the
list above. If nothing matches, return {"items": []}.
```

`{roles}` is rendered from `role-taxonomy.md` by `roles.role_table_prompt()`.

## User Prompt

```text
Context extracted so far (for resolving references like 'the method described above'):
{digest_block}

--- SECTION: {section} ---
{text}
```
