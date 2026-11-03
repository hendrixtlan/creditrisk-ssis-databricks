"""Generate reproducible synthetic lending CSVs and a legacy-style Gold baseline.
No third-party dependencies; no real financial or customer records.
"""
from __future__ import annotations
import argparse
import csv
import random
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

D = Decimal
Q = D("0.01")
FIELDS = {
    "customers": ["customer_id", "region", "risk_band", "updated_at"],
    "loans": ["loan_id", "customer_id", "principal_amount", "outstanding_balance", "due_date", "updated_at"],
    "payments": ["payment_id", "loan_id", "payment_amount", "payment_date", "updated_at"],
}
GOLD_FIELDS = ["as_of_date", "region", "risk_band", "loan_count", "total_principal", "outstanding_exposure", "past_due_exposure", "total_collected", "past_due_pct"]


def money(value: Decimal) -> str:
    return str(value.quantize(Q, rounding=ROUND_HALF_UP))


def build_records(as_of: date):
    rnd = random.Random(20261031)
    anchor = datetime(2026, 10, 15, 12, 0, 0)
    customers, loans, payments = [], [], []
    for n in range(1, 121):
        customers.append(dict(customer_id=n, region=rnd.choice(["North", "Central", "South"]),
                              risk_band=rnd.choice(["A", "B", "C", "D"]),
                              updated_at=(anchor + timedelta(days=rnd.randint(0, 12))).isoformat(sep=" ")))
    for n in range(1, 301):
        principal = D(rnd.randint(1000, 40000))
        balance = principal * D(rnd.randint(15, 100)) / D(100)
        loans.append(dict(loan_id=n, customer_id=rnd.randint(1, 120),
                          principal_amount=money(principal), outstanding_balance=money(balance),
                          due_date=(as_of + timedelta(days=rnd.randint(-90, 45))).isoformat(),
                          updated_at=(anchor + timedelta(days=rnd.randint(0, 12))).isoformat(sep=" ")))
    for n in range(1, 601):
        payments.append(dict(payment_id=n, loan_id=rnd.randint(1, 300),
                             payment_amount=money(D(rnd.randint(50, 1500)) + D("0.25")),
                             payment_date=(as_of + timedelta(days=rnd.randint(-110, 15))).isoformat(),
                             updated_at=(anchor + timedelta(days=rnd.randint(0, 12))).isoformat(sep=" ")))
    return {"customers": customers, "loans": loans, "payments": payments}


def compute_gold(data: dict, as_of: date) -> list[dict]:
    """Equivalent definition to the reference legacy SQL query and Gold Spark job."""
    customer_by_id = {int(row["customer_id"]): row for row in data["customers"]}
    paid_by_loan = defaultdict(lambda: D("0"))
    for row in data["payments"]:
        if date.fromisoformat(row["payment_date"]) <= as_of:
            paid_by_loan[int(row["loan_id"])] += D(row["payment_amount"])
    groups = defaultdict(lambda: dict(loan_count=0, total_principal=D(0),
                                      outstanding_exposure=D(0), past_due_exposure=D(0), total_collected=D(0)))
    for row in data["loans"]:
        customer = customer_by_id[int(row["customer_id"])]
        key = (customer["region"], customer["risk_band"])
        bucket = groups[key]
        principal = D(row["principal_amount"])
        outstanding = D(row["outstanding_balance"])
        bucket["loan_count"] += 1
        bucket["total_principal"] += principal
        bucket["outstanding_exposure"] += outstanding
        if date.fromisoformat(row["due_date"]) < as_of and outstanding > 0:
            bucket["past_due_exposure"] += outstanding
        bucket["total_collected"] += paid_by_loan[int(row["loan_id"])]
    result = []
    for (region, band), metrics in sorted(groups.items()):
        overdue_pct = (D(100) * metrics["past_due_exposure"] / metrics["outstanding_exposure"]
                       if metrics["outstanding_exposure"] else D(0))
        result.append(dict(as_of_date=as_of.isoformat(), region=region, risk_band=band,
                           loan_count=metrics["loan_count"],
                           total_principal=money(metrics["total_principal"]),
                           outstanding_exposure=money(metrics["outstanding_exposure"]),
                           past_due_exposure=money(metrics["past_due_exposure"]),
                           total_collected=money(metrics["total_collected"]),
                           past_due_pct=str(overdue_pct.quantize(D("0.0001"), rounding=ROUND_HALF_UP))))
    return result


def write_csv(path: Path, columns: list[str], rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def run(out: Path, as_of: date):
    dataset = build_records(as_of)
    for table, rows in dataset.items():
        write_csv(out / "landing" / table / "run_local_001" / f"{table}_run_local_001.csv", FIELDS[table], rows)
    write_csv(out / "legacy_gold_baseline.csv", GOLD_FIELDS, compute_gold(dataset, as_of))
    return dataset


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("demo/generated"))
    parser.add_argument("--as-of-date", type=date.fromisoformat, default=date(2026, 10, 31))
    args = parser.parse_args()
    data = run(args.out, args.as_of_date)
    print(f"Synthetic CSVs: {args.out} | " + ", ".join(f"{n}: {len(rows)}" for n, rows in data.items()))
