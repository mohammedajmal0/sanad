"""Mock Najm enterprise systems (Phase 5): ERP credit notes, ITSM tickets, CRM cases and a Teams
channel behind one REST API. State lives in memory, so a restart empties it.

Every create needs an Idempotency-Key header. The same key again returns the first result instead
of creating a duplicate, so a client may retry a create after a timeout; the same key with a
different body is refused (409). Rules and shapes written by Claude at my request.

    docker compose -f mock_systems/compose.yaml up --build     # or: uv run uvicorn mock_systems.api:app
"""

import itertools
import threading
from typing import Annotated, Literal

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Najm mock systems")


def approver(amount_sar: float) -> str:
    """Who must approve a credit note: the Credit Note and Refund Policy (fin-credit-notes)."""
    if amount_sar > 50000:
        return "finance manager and chief financial officer"
    if amount_sar > 5000:
        return "finance manager"
    if amount_sar > 1000:
        return "regional sales manager"
    return "account manager's team lead"


class CreditNoteIn(BaseModel):
    invoice_id: str = Field(pattern=r"^INV-\d{6}$")
    amount_sar: float = Field(gt=0)
    # fin-credit-notes: DUP duplicate invoice, LATE late delivery, RET returned goods,
    # PRC pricing error, OTH anything else (the reason then explains it)
    reason_code: Literal["DUP", "LATE", "RET", "PRC", "OTH"]
    reason: str = Field(min_length=1)


class TicketIn(BaseModel):
    category: Literal["VPN", "Email", "Laptop", "Password reset", "ERP access", "Printer"]
    summary: str = Field(min_length=1)
    priority: Literal["low", "medium", "high"] = "medium"


class CaseIn(BaseModel):
    account_id: str = Field(pattern=r"^ACC-\d{5}$")
    subject: str = Field(min_length=1)


class MessageIn(BaseModel):
    channel: str = Field(min_length=1)
    text: str = Field(min_length=1)


# ponytail: in-memory and one process; a database when the mock needs to survive restarts
ID_FORMAT = {"credit-notes": "CN-{:06d}", "tickets": "TKT-{:06d}", "cases": "CASE-{:06d}",
             "messages": "MSG-{:06d}"}  # fmt: skip
# New tickets start at TKT-100001, clear of the lakehouse's TKT-0xxxxx ids.
counters = {"credit-notes": itertools.count(1), "tickets": itertools.count(100001),
            "cases": itertools.count(1), "messages": itertools.count(1)}  # fmt: skip
records: dict[str, dict[str, dict]] = {system: {} for system in ID_FORMAT}
by_key: dict[tuple[str, str], tuple[dict, dict]] = {}  # (system, key) -> (request, record)
lock = threading.Lock()  # FastAPI runs these handlers on a thread pool

IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key", min_length=8)]


def _create(system: str, key: str, request: dict, **computed) -> dict:
    """Store a new record once per idempotency key; a repeated key returns the first record."""
    with lock:
        if (system, key) in by_key:
            first_request, record = by_key[(system, key)]
            if first_request != request:
                raise HTTPException(409, "Idempotency-Key reused with a different request")
            return record
        record = {"id": ID_FORMAT[system].format(next(counters[system])), **request, **computed}
        records[system][record["id"]] = record
        by_key[(system, key)] = (request, record)
        return record


def _get(system: str, record_id: str) -> dict:
    if record_id not in records[system]:
        raise HTTPException(404, f"{record_id} not found")
    return records[system][record_id]


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/erp/credit-notes", status_code=201)
def create_credit_note(note: CreditNoteIn, key: IdempotencyKey) -> dict:
    # Every credit note is a draft until a second person approves it; an AI may never approve one.
    approve_by = approver(note.amount_sar)
    return _create("credit-notes", key, note.model_dump(), status="awaiting_approval",
                   approver=approve_by)  # fmt: skip


@app.get("/erp/credit-notes/{credit_note_id}")
def get_credit_note(credit_note_id: str) -> dict:
    return _get("credit-notes", credit_note_id)


@app.post("/itsm/tickets", status_code=201)
def create_ticket(ticket: TicketIn, key: IdempotencyKey) -> dict:
    return _create("tickets", key, ticket.model_dump(), status="open")


@app.get("/itsm/tickets/{ticket_id}")
def get_ticket(ticket_id: str) -> dict:
    return _get("tickets", ticket_id)


@app.post("/crm/cases", status_code=201)
def create_case(case: CaseIn, key: IdempotencyKey) -> dict:
    return _create("cases", key, case.model_dump(), status="open")


@app.get("/crm/cases/{case_id}")
def get_case(case_id: str) -> dict:
    return _get("cases", case_id)


@app.post("/teams/messages", status_code=201)
def post_message(message: MessageIn, key: IdempotencyKey) -> dict:
    return _create("messages", key, message.model_dump())


@app.get("/teams/messages")
def list_messages(channel: str) -> list[dict]:
    return [m for m in records["messages"].values() if m["channel"] == channel]
