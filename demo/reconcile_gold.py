"""Compare Databricks CSV Gold export vs legacy Gold CSV by business key."""
import argparse
import csv
from decimal import Decimal
from pathlib import Path

KEY = ("as_of_date", "region", "risk_band")
MEASURES = ("loan_count", "total_principal", "outstanding_exposure", "past_due_exposure", "total_collected", "past_due_pct")


def load(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    result = {}
    for row in rows:
        key = tuple(row[column] for column in KEY)
        if key in result:
            raise ValueError(f"Duplicate Gold key in {path}: {key}")
        result[key] = {name: Decimal(row[name]) for name in MEASURES}
    return result


def reconcile(expected: Path, actual: Path, tolerance: Decimal = Decimal("0.01")):
    a, b = load(expected), load(actual)
    errors = []
    for key in sorted(set(a) | set(b)):
        if key not in a or key not in b:
            errors.append(f"Missing key {key} in {'expected' if key not in a else 'actual'}")
            continue
        for name in MEASURES:
            threshold = Decimal("0") if name == "loan_count" else tolerance
            if abs(a[key][name] - b[key][name]) > threshold:
                errors.append(f"{key} {name}: legacy={a[key][name]} cloud={b[key][name]}")
    return errors


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--expected", type=Path, required=True)
    ap.add_argument("--actual", type=Path, required=True)
    ap.add_argument("--tolerance", type=Decimal, default=Decimal("0.01"))
    args = ap.parse_args()
    errors = reconcile(args.expected, args.actual, args.tolerance)
    if errors:
        print("RECONCILIATION FAILED:\n" + "\n".join(errors[:30]))
        raise SystemExit(1)
    print("PASS — all Gold grouping keys and numeric measures match within tolerance")
