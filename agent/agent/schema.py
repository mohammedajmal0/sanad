"""The answer every Sanad agent returns (agent card: answer, citations, confidence, next_action).
Fields, descriptions and the citation rule were written by Claude at my request; I must be
able to defend them."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Citation(BaseModel):
    source: Literal["document", "record", "query"] = Field(
        description="document: a policy or KB article from search_policies. "
        "record: a row from a lookup tool (get_customer_summary, get_invoices, "
        "get_shipment_status or get_ticket_trend). "
        "query: an ops_analytics (Genie) answer, which ran SQL on the gold tables."
    )
    ref: str = Field(
        description="The doc_id (e.g. fin-duplicate-invoices), the record id "
        "(e.g. INV-027711, ORD-027711, ACC-00001, TKT-010001), or for a query the deep_link that opens "
        "its SQL and rows, copied exactly."
    )
    title: str = Field(
        description="The document title, the tool that returned the record, or what the query "
        "measured."
    )


class Answer(BaseModel):
    answer: str = Field(
        min_length=1,
        description="The answer in plain language, using only facts and rules the tools returned.",
    )
    citations: list[Citation] = Field(
        description="Every document and record the answer relies on. Empty only if the tools "
        "returned nothing useful."
    )
    confidence: Literal["high", "medium", "low"] = Field(
        description="high: every claim comes from a cited tool result. medium: you chose between "
        "several matching records or documents. low: the tools did not answer the question."
    )
    next_action: Literal["none", "draft_credit_note", "open_case", "open_ticket", "ask_user"] = (
        Field(
            description="What a person should do next, if a policy calls for it. You never do it "
            "yourself: draft_credit_note, open_case and open_ticket need human approval. ask_user: you need "
            "more detail (e.g. which of several customers)."
        )
    )

    @model_validator(mode="after")
    def _uncited_answers_are_low_confidence(self) -> "Answer":
        # An answer with no sources can't claim to be sure: that's how invented reasons slip in.
        if not self.citations and self.confidence != "low":
            raise ValueError("an answer without citations must have confidence 'low'")
        return self
