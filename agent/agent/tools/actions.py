"""Sanad's write actions. Each pauses for a person's approval before it runs (REQUIRE_APPROVAL in
agent/agent.py), and the supervisor calls one only when the user asks for that action.

Phase 4 stand-ins: they check the request and apply the business rules but write nothing yet.
Phase 5 replaces each body with a call to the mock ERP or ITSM through MCP. The rules and
descriptions were written by Claude at my request; I must be able to defend them.
"""

import re

from langchain_core.tools import tool

MANAGER_LIMIT_SAR = 5000  # agent card: credit notes above SAR 5,000 need a manager's approval
CATEGORIES = {"VPN", "Email", "Laptop", "Password reset", "ERP access", "Printer"}


@tool
def draft_credit_note(invoice_id: str, amount_sar: float, reason: str) -> dict:
    """Draft a credit note in the ERP for one invoice. A person approves this call before it runs.
    Use it only when the user asks for a credit note that a policy calls for, such as for a
    duplicate invoice. Copy invoice_id and amount_sar (in SAR) exactly as a specialist returned
    them; give the reason in one sentence, naming the policy."""
    # The model fills these arguments, so check them here rather than trust the prompt.
    if not re.fullmatch(r"INV-\d{6}", invoice_id) or amount_sar <= 0:
        return {"status": "rejected", "error": "Needs an id like INV-050001 and an amount > 0."}
    request = {"invoice_id": invoice_id, "amount_sar": round(amount_sar, 2), "reason": reason}
    if amount_sar > MANAGER_LIMIT_SAR:
        return {**request, "status": "waiting_for_manager", "note": "Above SAR 5,000: a manager "
                "must approve it before it is drafted."}  # fmt: skip
    # ponytail: stand-in, nothing is stored until Phase 5 connects the mock ERP
    return {**request, "status": "drafted", "note": "Phase 4 stand-in: the mock ERP (Phase 5) "
            "will store it and assign its id."}  # fmt: skip


@tool
def open_ticket(category: str, summary: str) -> dict:
    """Open an IT ticket. A person approves this call before it runs. Use it only when the user
    asks for a ticket, usually after service_desk found no knowledge-base fix. category is one of
    VPN, Email, Laptop, Password reset, ERP access or Printer; summary is one sentence."""
    if category not in CATEGORIES:
        return {"status": "rejected", "error": f"category must be one of {sorted(CATEGORIES)}"}
    # ponytail: stand-in, nothing is created until Phase 5 connects the mock ITSM
    return {"category": category, "summary": summary, "status": "queued", "note": "Phase 4 "
            "stand-in: the mock ITSM (Phase 5) will create it and assign its id."}  # fmt: skip
