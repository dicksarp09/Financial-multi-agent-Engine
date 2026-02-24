from typing import Dict, Any, List
from schemas import TransactionRecord, CategorizationRequest


DEFAULT_CATEGORIES = {
    "grocery": "Food",
    "restaurant": "Food",
    "coffee": "Food",
    "uber": "Transportation",
    "lyft": "Transportation",
    "gas": "Transportation",
    "fuel": "Transportation",
    "rent": "Housing",
    "mortgage": "Housing",
    "electric": "Utilities",
    "water": "Utilities",
    "internet": "Utilities",
    "netflix": "Entertainment",
    "spotify": "Entertainment",
    "doctor": "Healthcare",
    "pharmacy": "Healthcare",
    "hospital": "Healthcare",
    "amazon": "Shopping",
    "target": "Shopping",
    "walmart": "Shopping",
    "salary": "Income",
    "payroll": "Income",
    "deposit": "Income",
    "subscription": "Subscription",
    "transfer": "Transfer",
    "venmo": "Transfer",
    "zelle": "Transfer",
}


class CategorizationAgent:
    """Agent responsible for categorizing transactions."""

    def __init__(self):
        self.name = "categorization_agent"

    def categorize_transaction(self, transaction: TransactionRecord) -> str:
        """
        Categorize a single transaction based on description.

        Args:
            transaction: Transaction to categorize

        Returns:
            Category string
        """
        if transaction.category:
            return transaction.category

        desc_lower = transaction.description.lower()

        for keyword, category in DEFAULT_CATEGORIES.items():
            if keyword in desc_lower:
                return category

        if transaction.amount > 0:
            return "Income"

        return "Other"

    def categorize_transactions(
        self, transactions: List[TransactionRecord]
    ) -> List[TransactionRecord]:
        """
        Categorize a list of transactions.

        Args:
            transactions: List of transactions to categorize

        Returns:
            List of transactions with categories assigned
        """
        categorized = []
        for txn in transactions:
            category = self.categorize_transaction(txn)
            categorized.append(
                TransactionRecord(
                    date=txn.date,
                    description=txn.description,
                    amount=txn.amount,
                    category=category,
                    transaction_id=txn.transaction_id,
                )
            )
        return categorized

    def execute(self, session_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the categorization agent.

        Args:
            session_id: Session identifier
            input_data: Input data containing transactions

        Returns:
            Result dictionary with categorized transactions
        """
        transactions_data = input_data.get("transactions", [])

        transactions = [
            TransactionRecord(
                date=t["date"],
                description=t["description"],
                amount=t["amount"],
                category=t.get("category"),
                transaction_id=t.get("transaction_id"),
            )
            for t in transactions_data
        ]

        categorized = self.categorize_transactions(transactions)

        category_counts: Dict[str, int] = {}
        for txn in categorized:
            cat = txn.category or "Uncategorized"
            category_counts[cat] = category_counts.get(cat, 0) + 1

        return {
            "transactions": [txn.model_dump() for txn in categorized],
            "category_counts": category_counts,
            "uncategorized_count": sum(
                1 for t in categorized if not t.category or t.category == "Other"
            ),
        }
