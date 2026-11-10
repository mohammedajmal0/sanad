"""The last step of every turn: turn the finished conversation into an `Answer`.

Why not create_agent(response_format=...)? Tested 2026-11-08 with gpt-oss-120b behind the AI
Gateway: ToolStrategy's forced tool call (tool_choice="any") is ignored, and ProviderStrategy
fails with "response_format and tools are not supported together". So the tool loop runs as
usual, then one extra call with no tools bound applies the JSON schema.
"""

import json
import logging
import re
from typing import Any

import mlflow
from langchain.agents.middleware import AgentMiddleware
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import ValidationError

from agent.schema import Answer, Citation

logger = logging.getLogger(__name__)

# Written by Claude at my request; I must be able to defend it.
INSTRUCTIONS = (
    "Rewrite the assistant's final reply above as the Answer schema. Use only facts and rules "
    "that appear in the tool results above, copy ids, dates and amounts exactly, and cite every "
    "document by its doc_id, every record by its id and every ops_analytics answer by its "
    "deep_link. Keep every citation a specialist returned. If the tools did not answer the "
    "question, say so, leave citations empty and set confidence to low."
)


# The model labels, code speaks (2026-11-10): asked four times to "reply with exactly this",
# gpt-oss-120b paraphrased every time, but it fills an enum reliably. Written by Claude at my request.
FIXED_REPLY = {
    "out_of_scope": (
        "That's outside what I can do. I can help with one customer's account, invoices and "
        "deliveries, with IT problems and IT ticket trends, and with delivery performance across "
        "regions and carriers."
    ),
    "decline_memory": (
        "I can't keep customer or business data in memory; I only remember your own preferences. "
        "Customer facts come from Najm's systems."
    ),
}

# Record ids as the tools print them. In prose the model sometimes writes a non-breaking hyphen
# (U+2011, "INV\u2011050001"): it looks the same, but a person searching the ERP for it finds nothing.
RECORD_ID = re.compile(r"\b(INV|ORD|ACC|SHP|TKT)[-\u2011](\d{5,6})\b")


def _this_turn(messages: list) -> list:
    """The messages since the user's latest message (a resume adds none, so it stays this turn)."""
    turn = max((i for i, m in enumerate(messages) if isinstance(m, HumanMessage)), default=0)
    return messages[turn:]


def specialist_citations(messages: list) -> list[Citation]:
    """Citations in this turn's tool results that are a specialist's Answer (customer_service)."""
    found: list[Citation] = []
    for m in _this_turn(messages):
        if not isinstance(m, ToolMessage):
            continue
        try:
            found += [Citation(**c) for c in json.loads(m.content)["citations"]]
        except (ValueError, TypeError, KeyError):
            continue  # an ordinary tool result, not an Answer
    return found


def mentioned_records(text: str, messages: list) -> list[Citation]:
    """Record ids the answer names that this turn's tool results contain, cited by the tool that
    returned them. An id no tool returned is not cited: it may be invented."""
    returned: dict[str, str] = {}
    for m in _this_turn(messages):
        if isinstance(m, ToolMessage):
            for prefix, digits in RECORD_ID.findall(str(m.content)):
                returned.setdefault(f"{prefix}-{digits}", m.name or "tool")
    named = dict.fromkeys(f"{prefix}-{digits}" for prefix, digits in RECORD_ID.findall(text))
    return [Citation(source="record", ref=r, title=returned[r]) for r in named if r in returned]


class StructuredAnswer(AgentMiddleware):
    def __init__(self, model: Any) -> None:
        super().__init__()
        self.formatter = model.with_structured_output(Answer, method="json_schema")

    async def aafter_agent(self, state: dict, runtime: Any) -> dict:
        messages = [*state["messages"], SystemMessage(INSTRUCTIONS)]
        final = state["messages"][-1]
        unformatted = False
        try:
            answer = await self.formatter.ainvoke(messages)
        except (ValidationError, OutputParserException) as error:
            # e.g. no citations but confidence "high": ask once more with the reason
            try:
                answer = await self.formatter.ainvoke(
                    [*messages, SystemMessage(f"Fix this: {error}")]
                )
            except (ValidationError, OutputParserException) as again:
                # Twice failed (empty output twice, 2026-11-10, on a deployed follow-up turn):
                # keep the agent's own reply, flagged, rather than lose the turn. Chosen by me.
                logger.warning("StructuredAnswer fell back to the agent's reply: %s", again)
                answer = Answer(
                    answer=final.text or "Sanad couldn't finish this answer. Please ask again.",
                    citations=[],
                    confidence="low",
                    next_action="none",
                )
                unformatted = True
        answer.answer = FIXED_REPLY.get(answer.next_action, answer.answer)
        answer.answer = RECORD_ID.sub(r"\1-\2", answer.answer)  # ids in prose must be copyable
        # Citations are provenance, so code carries them: a specialist's citations (the formatter
        # once dropped a policy when merging two answers) and every record the answer names (a
        # specialist once cited one of the two duplicate invoices it described). 2026-11-09.
        known = {c.ref for c in answer.citations}
        for c in [
            *specialist_citations(state["messages"]),
            *mentioned_records(answer.answer, state["messages"]),
        ]:
            if c.ref not in known:
                answer.citations.append(c)
                known.add(c.ref)
        # This turn's MLflow trace (agent.run_agent's start_trace), so the chat UI's thumbs land on
        # the exact trace that produced this answer. None when tracing is off.
        span = mlflow.get_current_active_span()
        trace = {"trace_id": span.trace_id} if span else {}
        flags = {"unformatted": True} if unformatted else {}
        # Same id: replaces the free-text reply, so the chat shows the answer once.
        return {
            "messages": [
                AIMessage(
                    id=final.id,
                    content=answer.answer,
                    additional_kwargs={"answer": answer.model_dump(), **trace, **flags},
                )
            ]
        }
