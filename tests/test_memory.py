"""
Memory & Context Tests - PHASE 3 Test Suite
===========================================

Tests:
1. Memory Separation - STM/LTM layers
2. Retrieval Agent - Historical context
3. Context Compression - LLM-ready summaries
4. User Scoping - Cross-user prevention
"""

import unittest
from memory.memory_manager import (
    get_memory_manager,
    MonthlySummary,
    TransactionRecord,
    UserScopeViolation,
)
from memory.context_compressor import get_context_compressor
from agents.retrieval_agent import RetrievalAgent, RetrievalRequest


class TestMemorySeparation(unittest.TestCase):
    """Test STM/LTM memory separation."""

    def setUp(self):
        self.memory = get_memory_manager()
        self.user_id = "test_user_memory"
        self.session_id = "test_session_memory"

    def test_store_monthly_summary(self):
        """Test storing monthly summary in LTM."""
        summary = MonthlySummary(
            user_id=self.user_id,
            month="2026-02",
            total_income=5000.0,
            total_expense=3500.0,
            savings_rate=30.0,
            category_breakdown={"Food": 500, "Housing": 1500},
            transaction_count=25,
            anomaly_count=1,
            risk_alerts=0,
            created_at="2026-02-28T00:00:00",
        )

        result = self.memory.store_monthly_summary(summary)
        self.assertTrue(result)

    def test_get_monthly_summaries(self):
        """Test retrieving monthly summaries."""
        summaries = self.memory.get_monthly_summaries(self.user_id, 6)
        self.assertIsInstance(summaries, list)

    def test_short_term_memory_update(self):
        """Test STM update."""
        state = self.memory.update_short_term_state(
            session_id=self.session_id,
            user_id=self.user_id,
            workflow_state="ANALYZE",
            current_transactions=[{"id": "tx1"}],
        )

        self.assertEqual(state.workflow_state, "ANALYZE")
        self.assertEqual(len(state.current_transactions), 1)

    def test_short_term_memory_get_nonexistent(self):
        """Test STM retrieval for nonexistent session."""
        result = self.memory.get_short_term_state("nonexistent_session", self.user_id)
        self.assertIsNone(result)

    def test_short_term_memory_clear(self):
        """Test STM clear."""
        unique_session = f"{self.session_id}_clear"
        self.memory.update_short_term_state(
            session_id=unique_session,
            user_id=self.user_id,
            workflow_state="TEST",
            current_transactions=[],
        )

        result = self.memory.clear_short_term(unique_session, self.user_id)
        self.assertTrue(result)


class TestUserScoping(unittest.TestCase):
    """Test user scoping enforcement."""

    def setUp(self):
        self.memory = get_memory_manager()
        self.user_id = "owner_user"
        self.session_id = "owner_session"

        self.memory.update_short_term_state(
            session_id=self.session_id, user_id=self.user_id, workflow_state="INIT"
        )

    def test_cross_user_access_blocked(self):
        """Test that cross-user access is blocked."""
        with self.assertRaises(UserScopeViolation):
            self.memory.get_short_term_state(self.session_id, "attacker_user")

    def test_cross_user_update_blocked(self):
        """Test that cross-user update is blocked."""
        with self.assertRaises(UserScopeViolation):
            self.memory.update_short_term_state(
                session_id=self.session_id,
                user_id="attacker_user",
                workflow_state="HACKED",
            )

    def test_cross_user_clear_blocked(self):
        """Test that cross-user clear is blocked."""
        with self.assertRaises(UserScopeViolation):
            self.memory.clear_short_term(self.session_id, "attacker_user")


class TestRetrievalAgent(unittest.TestCase):
    """Test retrieval agent functionality."""

    def setUp(self):
        self.retrieval = RetrievalAgent()
        self.memory = get_memory_manager()
        self.user_id = "retrieval_user"

        self.memory.store_monthly_summary(
            MonthlySummary(
                user_id=self.user_id,
                month="2026-01",
                total_income=5000.0,
                total_expense=3500.0,
                savings_rate=30.0,
                category_breakdown={"Food": 500, "Housing": 1500},
                transaction_count=25,
                anomaly_count=1,
                risk_alerts=0,
                created_at="2026-01-31T00:00:00",
            )
        )

    def test_retrieve_historical_context(self):
        """Test historical context retrieval."""
        request = RetrievalRequest(user_id=self.user_id, session_id="test", months=6)

        context = self.retrieval.retrieve_historical_context(request)

        self.assertEqual(context.user_id, self.user_id)
        self.assertGreater(context.months_analyzed, 0)
        self.assertEqual(context.average_income, 5000.0)

    def test_retrieval_request_schema(self):
        """Test retrieval request validation."""
        request = RetrievalRequest(
            user_id="user123",
            session_id="session123",
            months=3,
            include_transactions=True,
            include_trends=True,
        )

        self.assertEqual(request.months, 3)
        self.assertTrue(request.include_transactions)


class TestContextCompressor(unittest.TestCase):
    """Test context compression."""

    def setUp(self):
        self.compressor = get_context_compressor()

    def test_compress_historical_data(self):
        """Test compressing historical data."""
        historical = {
            "average_income": 4500.0,
            "average_expense": 3200.0,
            "category_trends": {"Food": 600, "Housing": 1400, "Transport": 350},
            "savings_trend": 0.15,
            "risk_alerts_count": 2,
            "period_start": "2025-08",
            "period_end": "2026-01",
        }

        compressed = self.compressor.compress_historical_context(
            user_id="user123", session_id="session123", historical_data=historical
        )

        self.assertEqual(compressed.avg_income, 4500.0)
        self.assertEqual(compressed.avg_expense, 3200.0)
        self.assertEqual(compressed.savings_trend, 0.15)
        self.assertEqual(compressed.risk_flags_count, 2)
        self.assertIn("Housing", compressed.top_categories)

    def test_to_json_string(self):
        """Test JSON serialization."""
        from memory.context_compressor import CompressedContext

        context = CompressedContext(
            avg_income=4000.0,
            avg_expense=3000.0,
            top_categories={"Food": 500},
            savings_trend=0.1,
            risk_flags_count=1,
            period="2026-01",
            compressed_at="2026-01-31T00:00:00",
        )

        json_str = self.compressor.to_json_string(context)
        self.assertIsInstance(json_str, str)
        self.assertIn("avg_income", json_str)

    def test_to_llm_prompt(self):
        """Test LLM prompt formatting."""
        from memory.context_compressor import CompressedContext

        context = CompressedContext(
            avg_income=4000.0,
            avg_expense=3000.0,
            top_categories={"Food": 500},
            savings_trend=0.1,
            risk_flags_count=1,
            period="2026-01",
            compressed_at="2026-01-31T00:00:00",
        )

        prompt = self.compressor.to_llm_prompt(context)
        self.assertIn("Historical Context Summary", prompt)
        self.assertIn("$4,000.00", prompt)
        self.assertIn("Risk Alerts", prompt)

    def test_token_limit_check(self):
        """Test token limit validation."""
        from memory.context_compressor import CompressedContext

        context = CompressedContext(
            avg_income=4000.0,
            avg_expense=3000.0,
            top_categories={"Food": 500},
            savings_trend=0.1,
            risk_flags_count=1,
            period="2026-01",
            compressed_at="2026-01-31T00:00:00",
        )

        self.assertTrue(self.compressor.is_within_limit(context))


def run_memory_tests():
    """Run all memory tests."""
    print("=" * 70)
    print("RUNNING MEMORY & CONTEXT TEST SUITE")
    print("=" * 70)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestMemorySeparation))
    suite.addTests(loader.loadTestsFromTestCase(TestUserScoping))
    suite.addTests(loader.loadTestsFromTestCase(TestRetrievalAgent))
    suite.addTests(loader.loadTestsFromTestCase(TestContextCompressor))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success: {result.wasSuccessful()}")

    return result.wasSuccessful()


if __name__ == "__main__":
    run_memory_tests()
