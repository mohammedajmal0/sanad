"""The last step of every turn: turn the finished conversation into an `Answer`.

Why not create_agent(response_format=...)? Tested 2026-11-08 with gpt-oss-120b behind the AI
Gateway: ToolStrategy's forced tool call (tool_choice="any") is ignored, and ProviderStrategy
fails with "response_format and tools are not supported together". So the tool loop runs as
usual, then one extra call with no tools bound applies the JSON schema.
"""

from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import AIMessage, SystemMessage
from pydantic import ValidationError

from agent.schema import Answer

# Written by Claude at my request; I must be able to defend it.
INSTRUCTIONS = (
    "Rewrite the assistant's final reply above as the Answer schema. Use only facts and rules "
    "that appear in the tool results above, copy ids, dates and amounts exactly, and cite every "
    "document by its doc_id and every record by its id. If the tools did not answer the "
    "question, say so, leave citations empty and set confidence to low."
)


class StructuredAnswer(AgentMiddleware):
    def __init__(self, model: Any) -> None:
        super().__init__()
        self.formatter = model.with_structured_output(Answer, method="json_schema")

    async def aafter_agent(self, state: dict, runtime: Any) -> dict:
        messages = [*state["messages"], SystemMessage(INSTRUCTIONS)]
        try:
            answer = await self.formatter.ainvoke(messages)
        except (ValidationError, OutputParserException) as error:
            # e.g. no citations but confidence "high": ask once more with the reason, then fail loudly
            answer = await self.formatter.ainvoke([*messages, SystemMessage(f"Fix this: {error}")])
        final = state["messages"][-1]
        # Same id: replaces the free-text reply, so the chat shows the answer once.
        return {
            "messages": [
                AIMessage(
                    id=final.id,
                    content=answer.answer,
                    additional_kwargs={"answer": answer.model_dump()},
                )
            ]
        }
