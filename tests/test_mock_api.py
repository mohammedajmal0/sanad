"""The mock systems' contract: validation, the ERP's SAR 5,000 rule, and idempotent creates."""

import uuid

from fastapi.testclient import TestClient

from mock_systems.api import app

api = TestClient(app)


def post(path, body, key=None):
    return api.post(path, json=body, headers={"Idempotency-Key": key or uuid.uuid4().hex})


def test_every_credit_note_waits_for_the_approver_the_policy_names():
    def draft(amount):
        body = {"invoice_id": "INV-050001", "amount_sar": amount, "reason_code": "DUP",
                "reason": "Duplicate of INV-027711"}  # fmt: skip
        return post("/erp/credit-notes", body)

    note = draft(1440.71)
    assert note.status_code == 201 and note.json()["status"] == "awaiting_approval"
    assert api.get(f"/erp/credit-notes/{note.json()['id']}").json() == note.json()
    tiers = [draft(a).json()["approver"] for a in (1000, 1000.01, 5000, 5000.01, 50000.01)]
    assert tiers == [
        "account manager's team lead",
        "regional sales manager",
        "regional sales manager",
        "finance manager",
        "finance manager and chief financial officer",
    ]


def test_a_retried_create_returns_the_first_record():
    body = {"category": "VPN", "summary": "VPN drops every few minutes"}
    first, retry = (
        post("/itsm/tickets", body, key="retry-key-1"),
        post("/itsm/tickets", body, key="retry-key-1"),
    )
    assert first.json() == retry.json()
    assert first.json()["id"].startswith("TKT-1")  # clear of the lakehouse's TKT-0xxxxx ids


def test_a_reused_key_with_a_different_request_is_refused():
    post(
        "/crm/cases", {"account_id": "ACC-00001", "subject": "Duplicate invoice"}, key="case-key-1"
    )
    clash = post("/crm/cases", {"account_id": "ACC-00002", "subject": "Other"}, key="case-key-1")
    assert clash.status_code == 409


def test_bad_requests_are_rejected():
    assert (
        post(
            "/erp/credit-notes",
            {"invoice_id": "050001", "amount_sar": 10, "reason_code": "DUP", "reason": "x"},
        ).status_code
        == 422
    )
    bad_code = {"invoice_id": "INV-050001", "amount_sar": 10, "reason_code": "OOPS", "reason": "x"}
    assert post("/erp/credit-notes", bad_code).status_code == 422
    assert post("/itsm/tickets", {"category": "Coffee", "summary": "x"}).status_code == 422
    no_key = api.post("/teams/messages", json={"channel": "ops", "text": "hi"})
    assert no_key.status_code == 422
    assert api.get("/itsm/tickets/TKT-999999").status_code == 404


def test_teams_messages_are_listed_by_channel():
    post("/teams/messages", {"channel": "billing", "text": "Credit note drafted"})
    assert [
        m["text"] for m in api.get("/teams/messages", params={"channel": "billing"}).json()
    ] == ["Credit note drafted"]
