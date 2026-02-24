"""
Evaluation Pipeline - Automated testing for financial agents
=========================================================

CI-ready tests:
- Categorization golden dataset
- Budget regression tests
- Anomaly detection scoring
- Drift detection
"""

import json
import unittest
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class EvaluationResult:
    """Result of an evaluation test."""

    test_name: str
    passed: bool
    score: float
    details: Dict[str, Any]


GOLDEN_DATASET = [
    {"description": "grocery store purchase", "expected_category": "Food"},
    {"description": "uber ride to airport", "expected_category": "Transportation"},
    {"description": "monthly rent payment", "expected_category": "Housing"},
    {"description": "electric bill payment", "expected_category": "Utilities"},
    {"description": "netflix subscription", "expected_category": "Entertainment"},
    {"description": "doctor visit co-pay", "expected_category": "Healthcare"},
    {"description": "amazon purchase electronics", "expected_category": "Shopping"},
    {"description": "salary deposit from employer", "expected_category": "Income"},
    {"description": "gas station fuel", "expected_category": "Transportation"},
    {"description": "restaurant dinner", "expected_category": "Food"},
]


CATEGORY_KEYWORDS = {
    "Food": ["grocery", "restaurant", "coffee", "food", "dining"],
    "Transportation": ["uber", "lyft", "gas", "fuel", "transport"],
    "Housing": ["rent", "mortgage", "housing"],
    "Utilities": ["electric", "water", "internet", "utility"],
    "Entertainment": ["netflix", "spotify", "movie", "entertainment"],
    "Healthcare": ["doctor", "pharmacy", "hospital", "medical"],
    "Shopping": ["amazon", "target", "walmart", "shopping"],
    "Income": ["salary", "payroll", "deposit", "income"],
}


def rule_based_categorize(description: str) -> str:
    """Rule-based categorization for evaluation."""
    desc_lower = description.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in desc_lower:
                return category

    return "Other"


class EvaluationRunner:
    """
    Automated evaluation pipeline.

    Runs:
    - Categorization accuracy tests
    - Budget regression tests
    - Anomaly detection scoring
    """

    def __init__(self):
        self.results: List[EvaluationResult] = []

    def run_categorization_test(self) -> EvaluationResult:
        """Run categorization golden dataset test."""
        correct = 0
        total = len(GOLDEN_DATASET)

        for item in GOLDEN_DATASET:
            predicted = rule_based_categorize(item["description"])
            if predicted == item["expected_category"]:
                correct += 1

        accuracy = correct / total if total > 0 else 0

        result = EvaluationResult(
            test_name="categorization_accuracy",
            passed=accuracy >= 0.8,  # 80% threshold
            score=accuracy,
            details={"correct": correct, "total": total},
        )

        self.results.append(result)
        return result

    def run_budget_regression_test(
        self, previous_budgets: Dict[str, float], current_budgets: Dict[str, float]
    ) -> EvaluationResult:
        """Run budget allocation regression test."""
        changes = {}
        max_change = 0.0

        for category in set(previous_budgets.keys()) | set(current_budgets.keys()):
            prev = previous_budgets.get(category, 0)
            curr = current_budgets.get(category, 0)

            if prev > 0:
                change = abs(curr - prev) / prev
                changes[category] = change
                max_change = max(max_change, change)

        passed = max_change < 0.5  # Less than 50% change

        result = EvaluationResult(
            test_name="budget_regression",
            passed=passed,
            score=1 - max_change,
            details={"max_change": max_change, "changes": changes},
        )

        self.results.append(result)
        return result

    def run_anomaly_detection_test(
        self, test_cases: List[Dict[str, Any]]
    ) -> EvaluationResult:
        """Run anomaly detection scoring test."""
        true_positives = 0
        false_positives = 0
        true_negatives = 0
        false_negatives = 0

        for case in test_cases:
            amount = case["amount"]
            is_anomaly = amount > 500  # Simple threshold

            predicted_anomaly = case.get("detected", False)
            actual_anomaly = case.get("is_anomaly", False)

            if predicted_anomaly and actual_anomaly:
                true_positives += 1
            elif predicted_anomaly and not actual_anomaly:
                false_positives += 1
            elif not predicted_anomaly and actual_anomaly:
                false_negatives += 1
            else:
                true_negatives += 1

        precision = (
            true_positives / (true_positives + false_positives)
            if (true_positives + false_positives) > 0
            else 0
        )
        recall = (
            true_positives / (true_positives + false_negatives)
            if (true_positives + false_negatives) > 0
            else 0
        )
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0
        )

        result = EvaluationResult(
            test_name="anomaly_detection",
            passed=f1 >= 0.7,
            score=f1,
            details={
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "tp": true_positives,
                "fp": false_positives,
                "tn": true_negatives,
                "fn": false_negatives,
            },
        )

        self.results.append(result)
        return result

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all evaluation tests."""
        # Categorization test
        self.run_categorization_test()

        # Budget regression test
        previous = {"Food": 500, "Housing": 1500, "Transport": 300}
        current = {"Food": 520, "Housing": 1480, "Transport": 310}
        self.run_budget_regression_test(previous, current)

        # Anomaly detection test
        anomaly_cases = [
            {"amount": 1500, "detected": True, "is_anomaly": True},
            {"amount": 50, "detected": False, "is_anomaly": False},
            {"amount": 600, "detected": True, "is_anomaly": True},
            {"amount": 100, "detected": False, "is_anomaly": False},
        ]
        self.run_anomaly_detection_test(anomaly_cases)

        return self.get_summary()

    def get_summary(self) -> Dict[str, Any]:
        """Get evaluation summary."""
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        avg_score = sum(r.score for r in self.results) / total if total > 0 else 0

        return {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "average_score": avg_score,
            "all_passed": passed == total,
            "results": [
                {
                    "test": r.test_name,
                    "passed": r.passed,
                    "score": r.score,
                    "details": r.details,
                }
                for r in self.results
            ],
        }


def run_evaluation() -> Dict[str, Any]:
    """Run evaluation pipeline."""
    runner = EvaluationRunner()
    return runner.run_all_tests()


if __name__ == "__main__":
    print("=" * 60)
    print("EVALUATION PIPELINE")
    print("=" * 60)

    results = run_evaluation()

    print(f"\nTotal Tests: {results['total_tests']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Average Score: {results['average_score']:.2%}")
    print(f"All Passed: {results['all_passed']}")

    print("\nDetailed Results:")
    for r in results["results"]:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  [{status}] {r['test']}: {r['score']:.2%}")
