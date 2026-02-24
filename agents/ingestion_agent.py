from typing import Dict, Any, List
import json
import uuid
from schemas import TransactionRecord, ReadTransactionsInput


class IngestionAgent:
    """Agent responsible for reading and parsing transaction data."""

    def __init__(self):
        self.name = "ingestion_agent"

    def read_transactions(self, file_path: str) -> List[TransactionRecord]:
        """
        Read transactions from a JSON file.

        Args:
            file_path: Path to the transaction file

        Returns:
            List of TransactionRecord objects
        """
        input_schema = ReadTransactionsInput(file_path=file_path)

        with open(input_schema.file_path, "r") as f:
            data = json.load(f)

        transactions = []
        for idx, item in enumerate(data):
            txn = TransactionRecord(
                date=item["date"],
                description=item["description"],
                amount=float(item["amount"]),
                category=item.get("category"),
                transaction_id=item.get("transaction_id", str(uuid.uuid4())),
            )
            transactions.append(txn)

        return transactions

    def execute(self, session_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the ingestion agent.

        Args:
            session_id: Session identifier
            input_data: Input data containing file_path

        Returns:
            Result dictionary with transactions
        """
        file_path = input_data.get("file_path")
        if not file_path:
            raise ValueError("file_path is required")

        transactions = self.read_transactions(file_path)

        return {
            "transactions": [txn.model_dump() for txn in transactions],
            "count": len(transactions),
        }
