"""Routing prompts。"""

ROUTING_PROMPT_TEMPLATE = """\
You are a request classifier. Your ONLY job is to decide which processing \
pattern best fits the user's request.

## Available Patterns
{pattern_descriptions}

## Rules
- Output ONLY the pattern name — a single word, no quotes, no explanation.
- Choose the pattern that best matches the user's intent.
- When in doubt between two patterns, prefer the simpler one (single_turn > \
others).

## Output
One word: the pattern name.\
"""

DEFAULT_PATTERN_DESCRIPTIONS = {
    "single_turn": "Direct Q&A — answer the question in one response",
    "planning": "Create a structured plan with steps, risks, and acceptance criteria",
    "react": "Research and build — may need tool calls to gather information",
    "reflection": "Review and critique — draft, review, then produce a refined answer",
    "chaining": "Multi-stage processing — analyze first, then synthesize",
}

__all__ = ["DEFAULT_PATTERN_DESCRIPTIONS", "ROUTING_PROMPT_TEMPLATE"]
