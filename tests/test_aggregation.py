import unittest
from compute.aggregation import (
    compute_totals,
    compute_category_breakdown,
    compute_savings_rate,
)
from schemas import TransactionRecord


class TestAggregation(unittest.TestCase):
    """Unit tests for aggregation module."""

    def test_compute_totals_with_income_and_expenses(self):
        """Test computing totals with mixed transactions."""
        transactions = [
            TransactionRecord(
                date="2024-01-01",
                description="Salary",
                amount=5000.0,
                category="Income",
            ),
            TransactionRecord(
                date="2024-01-02",
                description="Rent",
                amount=-1500.0,
                category="Housing",
            ),
            TransactionRecord(
                date="2024-01-03", description="Food", amount=-200.0, category="Food"
            ),
        ]

        result = compute_totals(transactions)

        self.assertEqual(result.total_income, 5000.0)
        self.assertEqual(result.total_expense, 1700.0)
        self.assertEqual(result.net_savings, 3300.0)

    def test_compute_totals_empty_list(self):
        """Test computing totals with empty list."""
        result = compute_totals([])

        self.assertEqual(result.total_income, 0.0)
        self.assertEqual(result.total_expense, 0.0)
        self.assertEqual(result.net_savings, 0.0)

    def test_compute_totals_only_expenses(self):
        """Test computing totals with only expenses."""
        transactions = [
            TransactionRecord(
                date="2024-01-01",
                description="Rent",
                amount=-1500.0,
                category="Housing",
            ),
            TransactionRecord(
                date="2024-01-02", description="Food", amount=-200.0, category="Food"
            ),
        ]

        result = compute_totals(transactions)

        self.assertEqual(result.total_income, 0.0)
        self.assertEqual(result.total_expense, 1700.0)
        self.assertEqual(result.net_savings, -1700.0)

    def test_compute_category_breakdown(self):
        """Test computing category breakdown."""
        transactions = [
            TransactionRecord(
                date="2024-01-01",
                description="Rent",
                amount=-1500.0,
                category="Housing",
            ),
            TransactionRecord(
                date="2024-01-02", description="Grocery", amount=-200.0, category="Food"
            ),
            TransactionRecord(
                date="2024-01-03",
                description="Restaurant",
                amount=-100.0,
                category="Food",
            ),
            TransactionRecord(
                date="2024-01-04",
                description="Salary",
                amount=5000.0,
                category="Income",
            ),
        ]

        result = compute_category_breakdown(transactions)

        self.assertEqual(result.breakdown["Housing"], 1500.0)
        self.assertEqual(result.breakdown["Food"], 300.0)
        self.assertEqual(result.uncategorized_total, 0.0)

    def test_compute_category_breakdown_with_uncategorized(self):
        """Test computing category breakdown with uncategorized expenses."""
        transactions = [
            TransactionRecord(
                date="2024-01-01", description="Unknown", amount=-100.0, category=None
            ),
            TransactionRecord(
                date="2024-01-02", description="Food", amount=-200.0, category="Food"
            ),
        ]

        result = compute_category_breakdown(transactions)

        self.assertEqual(result.breakdown["Uncategorized"], 100.0)
        self.assertEqual(result.breakdown["Food"], 200.0)
        self.assertEqual(result.uncategorized_total, 100.0)

    def test_compute_savings_rate(self):
        """Test computing savings rate."""
        self.assertEqual(compute_savings_rate(5000, 3500), 30.0)
        self.assertEqual(compute_savings_rate(5000, 5000), 0.0)
        self.assertEqual(compute_savings_rate(5000, 6000), -20.0)

    def test_compute_savings_rate_zero_income(self):
        """Test computing savings rate with zero income."""
        self.assertEqual(compute_savings_rate(0, 100), 0.0)


if __name__ == "__main__":
    unittest.main()
