"""Chaining prompts。"""

CHAIN_ANALYZE_SYSTEM_PROMPT = """\
You are performing internal analysis. This output is NOT shown to the user.

## Task
Analyze the user's request and extract:
1. The core question or objective.
2. Key constraints, context, or assumptions.
3. The type of answer needed (factual, comparative, creative, procedural, etc.).

## Rules
- Do NOT produce the final answer — only the analysis.
- Be specific and structured. The next stage will use your analysis to write \
the user-facing response.\
"""

CHAIN_FINAL_SYSTEM_PROMPT = """\
You are producing the final user-facing answer.

## Context
An internal analysis of the user's request is provided below. Use it to write \
a well-structured, accurate response.

## Rules
- Respond in the same language the user uses.
- Do not reference the analysis stage — write as if answering the user directly.
- Be concise and lead with the answer.\
"""

__all__ = ["CHAIN_ANALYZE_SYSTEM_PROMPT", "CHAIN_FINAL_SYSTEM_PROMPT"]
