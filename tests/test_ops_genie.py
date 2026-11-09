"""The Ops Analytics check's pass/fail rule, without calling Genie."""

from evals.ops_genie import genie_failures

SUM_RATIO = ["SELECT region, carrier, SUM(late) / SUM(delivered) AS rate FROM t GROUP BY ALL"]
ANSWER = "Jeddah had the highest late rate (16.2%), mostly Red Sea Cargo."


def test_passes_with_region_carrier_and_sum_ratio():
    assert genie_failures(ANSWER, SUM_RATIO) == []


def test_fails_on_the_wrong_region():
    assert genie_failures("Dammam, mostly Red Sea Cargo.", SUM_RATIO) == ["doesn't mention Jeddah"]


def test_fails_when_it_averages_late_rate():
    averaged = ["SELECT region, AVG(d.late_rate) FROM t AS d GROUP BY region"]
    assert genie_failures(ANSWER, averaged) == [
        "averages late_rate instead of SUM(late) / SUM(delivered)"
    ]
