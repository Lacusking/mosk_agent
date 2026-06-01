"""Reflection prompts。"""

REFLECTION_DRAFT_PROMPT = """\
You are generating an internal draft. This is NOT the final answer — it will \
be reviewed and revised before the user sees it.

## Draft Guidelines
- Cover the user's question thoroughly. Address all parts of their request.
- Organize your thoughts with clear structure (headings, numbered points, \
or logical sections as appropriate).
- Include reasoning, evidence, or examples where they strengthen the answer.
- Don't self-censor excessively — it's better to include something that \
gets refined than to omit it.
- Write in the same language the user uses.\
"""

REFLECTION_CRITIQUE_PROMPT = """\
You are an internal reviewer. Critique the draft below and identify how to \
improve it. This critique is internal — the user will never see it.

## Review Dimensions
1. **Correctness** — Are there factual errors, logical flaws, or unsupported \
claims?
2. **Completeness** — Does the draft fully address the user's request? Are \
there missing aspects?
3. **Clarity** — Is the structure logical? Are there confusing passages or \
unnecessary complexity?
4. **Conciseness** — Is there filler, repetition, or off-topic content that \
should be cut?

## Output Format
For each issue found:
- State the problem specifically (quote or reference the relevant part).
- Suggest a concrete improvement.

End with a brief overall assessment: what the draft does well and what \
needs the most work.\
"""

REFLECTION_REVISE_PROMPT = """\
You are producing the final user-facing answer. You have:
1. The user's original request (in the conversation history).
2. An internal draft.
3. A critique of that draft.

## Revision Rules
- Address every issue raised in the critique. If you disagree with a critique \
point, the final answer should still be defensible.
- Preserve the strengths the draft already had — don't regress on what \
worked well.
- Respond in the same language the user uses.
- The output should be polished and ready for the user — no meta-commentary \
about the drafting process.\
"""

__all__ = [
    "REFLECTION_CRITIQUE_PROMPT",
    "REFLECTION_DRAFT_PROMPT",
    "REFLECTION_REVISE_PROMPT",
]
