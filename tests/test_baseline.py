"""Locally executable standard-library tests — not cloud integration tests."""
import csv
import sys
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "demo"))
from generate_data import build_records, compute_gold, run  # noqa: E402
from reconcile_gold import reconcile  # noqa: E402


class TestSyntheticCreditRisk(unittest.TestCase):
    def setUp(self):
        self.cutoff = date(2026, 10, 31)
        self.data = build_records(self.cutoff)

    def test_reproducible_data(self):
        self.assertEqual(self.data, build_records(self.cutoff))
        self.assertEqual(len(self.data["customers"]), 120)
        self.assertEqual(len(self.data["loans"]), 300)
        self.assertEqual(len(self.data["payments"]), 600)

    def test_referential_integrity(self):
        customers = {r["customer_id"] for r in self.data["customers"]}
        loans = {r["loan_id"] for r in self.data["loans"]}
        self.assertTrue(all(r["customer_id"] in customers for r in self.data["loans"]))
        self.assertTrue(all(r["loan_id"] in loans for r in self.data["payments"]))

    def test_gold_reconciliation_invariants(self):
        actual = compute_gold(self.data, self.cutoff)
        self.assertEqual(sum(int(r["loan_count"]) for r in actual), len(self.data["loans"]))
        self.assertEqual(sum(Decimal(r["outstanding_exposure"]) for r in actual),
                         sum(Decimal(r["outstanding_balance"]) for r in self.data["loans"]))
        self.assertTrue(all(Decimal(0) <= Decimal(r["past_due_pct"]) <= Decimal(100) for r in actual))

    def test_reconciliation_detects_tampering(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            run(path, self.cutoff)
            expected = path / "legacy_gold_baseline.csv"
            actual = path / "cloud_export.csv"
            actual.write_bytes(expected.read_bytes())
            self.assertEqual(reconcile(expected, actual), [])
            with actual.open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            rows[0]["outstanding_exposure"] = "9999999999.00"
            with actual.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader(); writer.writerows(rows)
            self.assertTrue(reconcile(expected, actual))


if __name__ == "__main__":
    unittest.main()
