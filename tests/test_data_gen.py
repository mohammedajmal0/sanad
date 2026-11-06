"""The generator's contract. The last three tests are the evaluation ground truth from
docs/scenario.md: if one fails, the agents have nothing real to find."""

from collections import Counter
from datetime import date
from statistics import median

from data_gen.generate import N_ACCOUNTS, N_ORDERS, N_TICKETS, generate

DATA = generate(42)  # built once and shared by every test


def test_same_seed_gives_same_data():
    assert generate(42) == DATA


def test_sizes():
    assert len(DATA["accounts"]) == N_ACCOUNTS
    assert len(DATA["orders"]) >= N_ORDERS
    assert len(DATA["tickets"]) >= N_TICKETS


def test_al_faris_invoiced_twice_for_one_september_order():
    al_faris = next(a for a in DATA["accounts"] if a["account_name"] == "Al-Faris Trading")
    invoices_per_order = Counter(
        inv["order_id"]
        for inv in DATA["invoices"]
        if inv["account_id"] == al_faris["account_id"]
        and date(2026, 9, 1) <= inv["invoice_date"] <= date(2026, 9, 30)
    )
    assert max(invoices_per_order.values(), default=0) >= 2


def test_one_region_stands_out_for_late_deliveries_in_q3():
    region_of_account = {a["account_id"]: a["region"] for a in DATA["accounts"]}
    region_of_order = {o["order_id"]: region_of_account[o["account_id"]] for o in DATA["orders"]}
    total, late = Counter(), Counter()
    for s in DATA["shipments"]:
        if s["delivered_date"] and date(2026, 7, 1) <= s["ship_date"] <= date(2026, 9, 30):
            region = region_of_order[s["order_id"]]
            total[region] += 1
            late[region] += s["delivered_date"] > s["promised_date"]
    worst, next_worst = sorted((late[r] / total[r] for r in total), reverse=True)[:2]
    assert worst >= 2 * next_worst


def test_vpn_cluster_starts_on_a_monday():
    vpn_per_day = Counter(t["created_at"].date() for t in DATA["tickets"] if t["category"] == "VPN")
    normal = median(vpn_per_day.values())
    spike_days = sorted(day for day, n in vpn_per_day.items() if n >= 5 * normal)
    assert spike_days, "no VPN spike found"
    assert spike_days[0].weekday() == 0  # Monday
