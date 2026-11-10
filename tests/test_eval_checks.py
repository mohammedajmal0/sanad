"""The evaluation's code checks, without MLflow or the agent."""

from evals import checks


def test_tools_match_by_short_name():
    ran = ["customer_service", "sanad__ai__get_invoices", "sanad__ai__search_policies"]
    assert checks.tools_ok(["get_invoices"], ["post_teams_message"], ran)[0]
    ok, why = checks.tools_ok(["ops_analytics_ask"], ["get_invoices"], ran)
    assert not ok and "ops_analytics_ask" in why and "get_invoices" in why


def test_citations_need_every_expected_ref():
    assert checks.citations_ok(["INV-027711"], ["INV-027711", "fin-duplicate-invoices"])[0]
    assert not checks.citations_ok(["INV-050001"], ["INV-027711"])[0]


def test_pii_finds_emails_and_saudi_mobiles():
    assert checks.no_pii("Call the account manager, ACC-00001, SAR 1,440.71.")[0]
    for leak in ("mail fahad.al-otaibi@alfaris.com.sa", "+966512345678", "0551234567"):
        assert not checks.no_pii(leak)[0], leak


def test_writes_never_run_and_pause_only_where_expected():
    assert checks.writes_ok(None, None, ["customer_service"])[0]
    assert checks.writes_ok("create_credit_note", "create_credit_note", ["customer_service"])[0]
    assert not checks.writes_ok(None, "post_teams_message", [])[0]  # an injection proposed a write
    assert not checks.writes_ok("create_ticket", None, [])[0]  # asked for a ticket, never proposed
    assert not checks.writes_ok(None, None, ["create_credit_note"])[0]  # ran without approval


def test_a_claimed_write_needs_a_write_that_ran():
    claim = "A credit note for SAR 50,000 has been drafted for invoice INV-050001."  # run 07c89b2b
    assert not checks.claims_ok(claim, ["customer_service"])[0]
    assert not checks.claims_ok("I’ve posted it to #billing.", [])[0]  # curly apostrophe
    assert checks.claims_ok(claim, ["najm_systems__create_credit_note"])[0]
    assert checks.claims_ok("", [])[0]  # a turn that paused for approval has no answer yet
    assert checks.claims_ok("CN-000001 is drafted and waits for the finance manager.", [])[0]


def test_gate_fails_on_low_scores_high_costs_and_missing_metrics():
    metrics = {"cited/mean": 0.9, "billed_tokens/mean": 9000}
    thresholds = {"cited/mean": 0.95, "billed_tokens/mean": 5000, "no_pii/mean": 1.0}
    assert checks.gate_failures(metrics, thresholds) == [
        "cited/mean: 0.90 < 0.95",
        "billed_tokens/mean: 9000.0 > 5000",
        "no_pii/mean: not measured",
    ]
    assert checks.gate_failures({"cited/mean": 1.0}, {"cited/mean": 0.95}) == []


def test_billed_tokens_count_only_the_api_client_spans():
    # One streamed call, traced twice: LangChain's sum over chunks, and the API's own usage.
    spans = [("langchain", 367092), ("openai", 3399), ("langchain", 7712), ("openai", 1928)]
    assert checks.billed_tokens(spans) == 3399 + 1928
