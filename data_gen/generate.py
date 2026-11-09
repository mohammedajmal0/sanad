"""Synthetic CRM, ERP and ITSM data for Najm Supply Co. (see docs/scenario.md).

Run:  uv run python data_gen/generate.py --out data_gen/output --seed 42

The same seed always gives the same files, so the planted problems (the
evaluation ground truth) stay in the same place between runs.
"""

import argparse
import csv
import json
import random
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path

START, END = date(2025, 11, 1), date(2026, 10, 31)  # 12 months of history
DAYS = (END - START).days + 1
N_ACCOUNTS, N_ORDERS, N_TICKETS = 2_000, 50_000, 10_000

REGIONS = ["Riyadh", "Jeddah", "Dammam", "Medina", "Abha"]
CARRIERS = ["Sahara Express", "Najd Freight", "Red Sea Cargo", "Gulf Line"]  # all fictional
# "Al-Faris" is left out on purpose: only one "Al-Faris Trading" exists, so the
# ground-truth question "why was Al-Faris Trading invoiced twice?" has one answer.
FAMILIES = [
    "Al-Otaibi",
    "Al-Qahtani",
    "Al-Ghamdi",
    "Al-Zahrani",
    "Al-Harbi",
    "Al-Mutairi",
    "Al-Shehri",
    "Al-Dosari",
    "Al-Subaie",
    "Al-Anazi",
    "Al-Shammari",
    "Al-Rashid",
    "Al-Hamdan",
    "Al-Tamimi",
    "Al-Juhani",
    "Al-Malki",
    "Al-Omari",
    "Al-Sulami",
    "Al-Yami",
    "Al-Khaldi",
    "Al-Amri",
    "Al-Asmari",
    "Al-Balawi",
    "Al-Bishi",
    "Al-Hajri",
    "Al-Jaber",
    "Al-Mansour",
    "Al-Nasser",
    "Al-Qurashi",
    "Al-Sharif",
    "Al-Thubaiti",
    "Al-Muhanna",
    "Al-Saleh",
    "Al-Fahad",
    "Al-Ali",
    "Al-Hussain",
    "Al-Ibrahim",
    "Al-Khalil",
    "Al-Mohsen",
    "Al-Nimr",
    "Al-Obaid",
    "Al-Rumaih",
    "Al-Saif",
    "Al-Turki",
    "Al-Wadie",
]
FIRST_NAMES = [
    "Mohammed",
    "Abdullah",
    "Fahad",
    "Khalid",
    "Saud",
    "Faisal",
    "Omar",
    "Ahmed",
    "Sultan",
    "Nasser",
    "Turki",
    "Yousef",
    "Ibrahim",
    "Majed",
    "Saad",
    "Nora",
    "Sara",
    "Reem",
    "Lama",
    "Haya",
    "Maha",
    "Mona",
    "Dana",
    "Hessa",
    "Abeer",
    "Amal",
    "Latifa",
    "Ghada",
    "Rana",
    "Hind",
]
SECTORS = [
    "Trading",
    "Contracting",
    "Foods",
    "Medical Supplies",
    "Steel",
    "Plastics",
    "Electrical",
    "Packaging",
    "Auto Parts",
    "Office Supplies",
    "Chemicals",
    "Textiles",
]
SUFFIXES = ["Co.", "Est.", "Group", "LLC"]
TITLES = ["Procurement Manager", "Finance Officer", "Operations Lead", "Owner", "Accounts Payable"]
TICKET_TYPES = {  # category: (share of tickets, typical summaries)
    "VPN": (8, ["VPN disconnects every few minutes", "Cannot connect to VPN from home"]),
    "Email": (20, ["Outlook not syncing", "Mailbox full"]),
    "Laptop": (20, ["Laptop very slow", "Screen flickers"]),
    "ERP access": (15, ["Cannot log in to ERP", "Need access to invoicing module"]),
    "Printer": (12, ["Printer offline", "Paper jam on second floor printer"]),
    "Password reset": (25, ["Password expired", "Account locked"]),
}
CSV_TABLES = {
    "accounts": "crm",
    "contacts": "crm",
    "orders": "erp",
    "invoices": "erp",
    "shipments": "erp",
}


def random_day(rng: random.Random) -> date:
    return START + timedelta(days=rng.randrange(DAYS))


def generate(seed: int = 42) -> dict[str, list[dict]]:
    """Build every table in memory as lists of dicts, then plant the problems."""
    rng = random.Random(seed)

    accounts, contacts = [], []
    names = rng.sample(
        [f"{f} {s} {x}" for f in FAMILIES for s in SECTORS for x in SUFFIXES], N_ACCOUNTS - 1
    )
    for i, name in enumerate(["Al-Faris Trading", *names], start=1):
        account_id = f"ACC-{i:05d}"
        accounts.append(
            {
                "account_id": account_id,
                "account_name": name,
                "region": rng.choice(REGIONS),
                "segment": rng.choice(["SMB", "Mid-market", "Enterprise"]),
                "created_date": START - timedelta(days=rng.randrange(1, 2000)),
            }
        )
        domain = "".join(c for c in name.lower() if c.isalnum())[:20] + ".com.sa"
        for _ in range(rng.randint(1, 3)):
            first, family = rng.choice(FIRST_NAMES), rng.choice(FAMILIES)
            contacts.append(
                {
                    "contact_id": f"CON-{len(contacts) + 1:05d}",
                    "account_id": account_id,
                    "full_name": f"{first} {family}",
                    "email": f"{first}.{family}@{domain}".lower(),
                    "phone": f"+9665{rng.randrange(10**8):08d}",
                    "title": rng.choice(TITLES),
                }
            )

    orders, invoices, shipments = [], [], []
    for i in range(1, N_ORDERS + 1):
        account_id = rng.choice(accounts)["account_id"]
        order_id, ordered = f"ORD-{i:06d}", random_day(rng)
        amount = round(rng.lognormvariate(8, 0.8), 2)  # median about 3,000 SAR
        orders.append(
            {
                "order_id": order_id,
                "account_id": account_id,
                "order_date": ordered,
                "amount_sar": amount,
            }
        )
        invoices.append(
            {
                "invoice_id": f"INV-{i:06d}",
                "order_id": order_id,
                "account_id": account_id,
                "invoice_date": ordered + timedelta(days=rng.randint(0, 3)),
                "amount_sar": amount,
            }
        )
        shipped = ordered + timedelta(days=rng.randint(0, 2))
        promised_days = rng.choice([2, 3, 5])
        transit = rng.randint(1, promised_days)
        if rng.random() < 0.03:  # normal background noise: about 3% arrive a little late
            transit += rng.randint(1, 3)
        delivered = shipped + timedelta(days=transit)
        shipments.append(
            {
                "shipment_id": f"SHP-{i:06d}",
                "order_id": order_id,
                "carrier": rng.choice(CARRIERS),
                "ship_date": shipped,
                "promised_date": shipped + timedelta(days=promised_days),
                "delivered_date": delivered if delivered <= END else None,
            }
        )

    categories = list(TICKET_TYPES)
    weights = [share for share, _ in TICKET_TYPES.values()]
    tickets = []
    for i in range(1, N_TICKETS + 1):
        category = rng.choices(categories, weights)[0]
        created = datetime.combine(random_day(rng), time(rng.randint(7, 18), rng.randrange(60)))
        tickets.append(
            {
                "ticket_id": f"TKT-{i:06d}",
                "created_at": created,
                "category": category,
                "priority": rng.choices(["low", "medium", "high"], [5, 4, 1])[0],
                "summary": rng.choice(TICKET_TYPES[category][1]),
                "status": "closed" if created.date() < END - timedelta(days=7) else "open",
            }
        )

    data = {
        "accounts": accounts,
        "contacts": contacts,
        "orders": orders,
        "invoices": invoices,
        "shipments": shipments,
        "tickets": tickets,
    }
    seed_problems(data, rng)
    return data


def seed_problems(data: dict[str, list[dict]], rng: random.Random) -> None:
    """Plant the problems the agents must find. They are the evaluation ground truth.

    docs/scenario.md fixes three; tests/test_data_gen.py checks each one:
    1. Al-Faris Trading is invoiced twice for one order in September 2026.
    2. One region has clearly more late deliveries in Q3 2026 (July to September),
       for a reason an analyst could find in the data.
    3. A cluster of VPN tickets starts on a Monday (the day of a software update).

    Change the lists in `data` in place. Use `rng` for any randomness so the
    same seed still gives the same data.
    """
    # 1. Duplicate invoice: Al-Faris's September order is billed a second time,
    #    same amount, 4 days later, as if someone re-sent the invoice by mistake.
    original = next(
        inv
        for inv in data["invoices"]
        if inv["account_id"] == "ACC-00001"
        and inv["invoice_date"].month == 9
        and inv["invoice_date"].year == 2026
    )
    data["invoices"].append(
        {
            **original,  # copy every field of the original invoice...
            "invoice_id": f"INV-{len(data['invoices']) + 1:06d}",  # ...but give it a new ID
            "invoice_date": original["invoice_date"] + timedelta(days=4),  # ...and a later date
        }
    )

    # 2. Late deliveries: in Q3 2026 the carrier "Red Sea Cargo" struggles in Jeddah
    #    (say, a port delay). Jeddah's late rate jumps, and the "why" is that one carrier.
    region_of_account = {a["account_id"]: a["region"] for a in data["accounts"]}
    region_of_order = {o["order_id"]: region_of_account[o["account_id"]] for o in data["orders"]}
    for s in data["shipments"]:
        if (
            region_of_order[s["order_id"]] == "Jeddah"
            and s["carrier"] == "Red Sea Cargo"
            and date(2026, 7, 1) <= s["ship_date"] <= date(2026, 9, 30)
            and rng.random() < 0.6
        ):  # 6 in 10 of those shipments arrive late
            s["delivered_date"] = s["promised_date"] + timedelta(days=rng.randint(1, 4))

    # 3. VPN cluster: Monday 19 October 2026 a software update breaks the VPN.
    #    Many tickets on Monday, fewer each day after as IT rolls out a fix.
    update_day = date(2026, 10, 19)
    for day, count in enumerate([30, 20, 12, 6, 3]):  # Monday to Friday
        for _ in range(count):
            data["tickets"].append(
                {
                    "ticket_id": f"TKT-{len(data['tickets']) + 1:06d}",
                    "created_at": datetime.combine(
                        update_day + timedelta(days=day),
                        time(rng.randint(7, 18), rng.randrange(60)),
                    ),
                    "category": "VPN",
                    "priority": rng.choice(["medium", "high"]),
                    "summary": rng.choice(
                        [
                            "VPN keeps dropping since Monday's update",
                            "VPN disconnects every few minutes",
                        ]
                    ),
                    "status": "closed",  # the fix was rolled out that week
                }
            )


def write(data: dict[str, list[dict]], out: Path) -> None:
    """CRM and ERP as CSV batch exports; tickets as JSON lines, one file per month."""
    for table, system in CSV_TABLES.items():
        folder = out / system / table  # one folder per table: Auto Loader reads a folder
        folder.mkdir(parents=True, exist_ok=True)
        with open(folder / f"{table}.csv", "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=data[table][0].keys())
            writer.writeheader()
            writer.writerows(data[table])

    by_month = defaultdict(list)
    for ticket in sorted(data["tickets"], key=lambda t: t["created_at"]):
        by_month[ticket["created_at"].strftime("%Y-%m")].append(ticket)
    folder = out / "itsm" / "tickets"
    folder.mkdir(parents=True, exist_ok=True)
    for month, rows in by_month.items():
        with open(folder / f"{month}.jsonl", "w") as f:
            f.writelines(json.dumps(row, default=lambda v: v.isoformat()) + "\n" for row in rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "output")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    data = generate(args.seed)
    write(data, args.out)
    print({table: len(rows) for table, rows in data.items()}, "->", args.out)


if __name__ == "__main__":
    main()
