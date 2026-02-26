from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import re


class ConversationAgent:
    """
    Agent for handling conversational refinement and what-if scenarios.

    This agent processes natural language commands to:
    - Adjust budget recommendations
    - Run what-if simulations
    - Generate predictive suggestions
    - Exclude specific transactions
    """

    def __init__(self, llm_provider: Optional[Any] = None):
        self.llm_provider = llm_provider

    def execute(self, session_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process conversational command.

        Args:
            session_id: Current session ID
            input_data: Must contain 'message', 'report', and optional 'transactions'

        Returns:
            Dict with 'message', 'action', 'suggestions', 'updated_metrics'
        """
        message = input_data.get("message", "")
        report = input_data.get("report", {})
        transactions = input_data.get("transactions", [])

        if not message:
            return {
                "message": "Please provide a command.",
                "action": "error",
                "suggestions": [],
                "updated_metrics": {},
            }

        message_lower = message.lower()

        # Route to appropriate handler
        if "save" in message_lower and "%" in message:
            return self._handle_save_command(message, report)
        elif "ignore" in message_lower:
            return self._handle_ignore_command(message, report)
        elif "what if" in message_lower or "simulate" in message_lower:
            return self._handle_whatif_command(message, report)
        elif (
            "reduce" in message_lower
            or "cut" in message_lower
            or "lower" in message_lower
        ):
            return self._handle_reduce_command(message, report)
        elif "increase" in message_lower:
            return self._handle_increase_command(message, report)
        else:
            return self._generate_suggestions(report)

    def _extract_percentage(self, message: str) -> Optional[int]:
        """Extract percentage from message."""
        match = re.search(r"(\d+)\s*%", message)
        return int(match.group(1)) if match else None

    def _extract_amount(self, message: str) -> Optional[float]:
        """Extract dollar amount from message."""
        match = re.search(r"\$?(\d+(?:\.\d+)?)", message)
        return float(match.group(1)) if match else None

    def _extract_category(self, message: str) -> Optional[str]:
        """Extract category from message."""
        categories = [
            "housing",
            "food",
            "transportation",
            "utilities",
            "entertainment",
            "shopping",
            "healthcare",
            "insurance",
            "fitness",
            "income",
        ]
        message_lower = message.lower()
        for cat in categories:
            if cat in message_lower:
                return cat.title()
        return None

    def _handle_save_command(self, message: str, report: Dict) -> Dict[str, Any]:
        """Handle 'Save X% of income' command."""
        target_pct = self._extract_percentage(message)

        if not target_pct:
            return {
                "message": "Please specify a percentage to save (e.g., 'Save 20% of income').",
                "action": "clarify",
                "suggestions": ["Save 10% of income", "Save 20% of income"],
                "updated_metrics": {},
            }

        current_income = report.get("total_income", 0)
        current_expenses = report.get("total_expenses", 0)

        if current_income == 0:
            return {
                "message": "No income data available. Please run analysis first.",
                "action": "error",
                "suggestions": [],
                "updated_metrics": {},
            }

        target_savings_amt = current_income * (target_pct / 100)
        current_savings = current_income - current_expenses
        adjustment_needed = target_savings_amt - current_savings

        if adjustment_needed > 0:
            # Need to reduce expenses
            non_essential = [
                "Entertainment",
                "Shopping",
                "Food",
                "Transportation",
                "Fitness",
            ]
            budget_changes = []
            reduction_needed = adjustment_needed

            for rec in report.get("budget_recommendations", []):
                if rec.get("category") in non_essential and reduction_needed > 0:
                    reduction = min(
                        rec.get("suggested_amount", 0) * 0.3, reduction_needed
                    )
                    new_amount = max(0, rec.get("suggested_amount", 0) - reduction)
                    reduction_needed -= reduction
                    budget_changes.append(
                        {
                            "category": rec.get("category"),
                            "previous": rec.get("suggested_amount"),
                            "new": new_amount,
                            "reduction": reduction,
                        }
                    )

            new_savings_rate = (
                (
                    current_income
                    - (current_expenses - (adjustment_needed - reduction_needed))
                )
                / current_income
            ) * 100

            return {
                "message": f"Done. I've adjusted your budget to save {target_pct}%. Your projected savings is now {new_savings_rate:.1f}% (was {report.get('savings_rate', 0):.1f}%).",
                "action": "adjust_savings",
                "budget_changes": budget_changes,
                "updated_metrics": {
                    "savings_rate": new_savings_rate,
                    "target_savings": target_pct,
                },
            }
        else:
            return {
                "message": f"You're already saving {report.get('savings_rate', 0):.1f}%, which exceeds your {target_pct}% target!",
                "action": "info",
                "suggestions": [],
                "updated_metrics": {},
            }

    def _handle_ignore_command(self, message: str, report: Dict) -> Dict[str, Any]:
        """Handle 'Ignore the $X charge' command."""
        amount = self._extract_amount(message)

        if not amount:
            return {
                "message": "Which transaction would you like to ignore? Please specify the amount (e.g., 'Ignore the $500 charge').",
                "action": "clarify",
                "suggestions": [],
                "updated_metrics": {},
            }

        # Find matching category
        for cat in report.get("category_breakdown", []):
            if abs(cat.get("amount", 0) - amount) < 10:
                new_expenses = report.get("total_expenses", 0) - cat.get("amount", 0)
                new_savings = (
                    (report.get("total_income", 0) - new_expenses)
                    / report.get("total_income", 1)
                ) * 100

                return {
                    "message": f"I've excluded the ${cat.get('amount'):.2f} {cat.get('category')} charge. Your expenses are now ${new_expenses:.2f} and savings rate is {new_savings:.1f}%.",
                    "action": "exclude_transaction",
                    "excluded_category": cat.get("category"),
                    "excluded_amount": cat.get("amount"),
                    "updated_metrics": {
                        "total_expenses": new_expenses,
                        "savings_rate": new_savings,
                    },
                }

        return {
            "message": f"Could not find a transaction for ${amount}. Please check the amount.",
            "action": "error",
            "suggestions": [],
            "updated_metrics": {},
        }

    def _handle_whatif_command(self, message: str, report: Dict) -> Dict[str, Any]:
        """Handle what-if simulation commands."""
        message_lower = message.lower()

        sim_type = None
        params = {}

        # Check for various what-if patterns
        less_match = re.search(r"\$(\d+)\s*less\s*on\s*(\w+)", message_lower)
        if less_match:
            sim_type = "reduce_category"
            params["category"] = less_match.group(2).title()
            params["amount"] = float(less_match.group(1))

        income_match = re.search(r"income.*(\d+)\s*%", message_lower)
        if income_match and "reduce" in message_lower:
            sim_type = "reduce_income"
            params["percentage"] = float(income_match.group(1))

        increase_match = re.search(r"increase.*(\w+).*\$(\d+)", message_lower)
        if increase_match:
            sim_type = "increase_category"
            params["category"] = increase_match.group(1).title()
            params["amount"] = float(increase_match.group(2))

        if not sim_type:
            return {
                "message": "I can simulate scenarios like:\n• 'What if I spend $200 less on rent?'\n• 'What if my income drops 15%?'\n• 'What if I increase food by $100?'",
                "action": "suggest",
                "suggestions": [
                    "What if I spend $200 less on rent?",
                    "What if my income drops 15%?",
                    "What if I increase entertainment by $50?",
                ],
                "updated_metrics": {},
            }

        # Run simulation
        sim_income = report.get("total_income", 0)
        sim_expenses = report.get("total_expenses", 0)

        if sim_type == "reduce_category":
            sim_expenses = max(0, sim_expenses - params.get("amount", 0))
        elif sim_type == "increase_category":
            sim_expenses = sim_expenses + params.get("amount", 0)
        elif sim_type == "reduce_income":
            sim_income = sim_income * (1 - params.get("percentage", 0) / 100)

        sim_savings = (
            ((sim_income - sim_expenses) / sim_income * 100) if sim_income > 0 else 0
        )

        return {
            "message": f"Simulation: With these changes, your new totals would be:\n• Income: ${sim_income:,.0f}\n• Expenses: ${sim_expenses:,.0f}\n• Savings Rate: {sim_savings:.1f}%",
            "action": "what_if",
            "simulation": {
                "type": sim_type,
                "params": params,
                "results": {
                    "income": sim_income,
                    "expenses": sim_expenses,
                    "savings_rate": sim_savings,
                },
            },
            "updated_metrics": {
                "is_simulation": True,
                "total_income": sim_income,
                "total_expenses": sim_expenses,
                "savings_rate": sim_savings,
            },
        }

    def _handle_reduce_command(self, message: str, report: Dict) -> Dict[str, Any]:
        """Handle budget reduction commands."""
        category = self._extract_category(message)
        pct = self._extract_percentage(message)

        if not category:
            return {
                "message": "Which category would you like to reduce? (Housing, Food, Transportation, Utilities, Entertainment, Shopping, Healthcare)",
                "action": "clarify",
                "suggestions": ["Reduce Housing by 20%", "Reduce Food by 15%"],
                "updated_metrics": {},
            }

        if not pct:
            return {
                "message": f"How much would you like to reduce {category} by? (e.g., 'Reduce {category} by 20%')",
                "action": "clarify",
                "suggestions": [
                    f"Reduce {category} by 10%",
                    f"Reduce {category} by 20%",
                ],
                "updated_metrics": {},
            }

        # Find and update category
        for rec in report.get("budget_recommendations", []):
            if rec.get("category") == category:
                old_amount = rec.get("suggested_amount", 0)
                new_amount = old_amount * (1 - pct / 100)

                return {
                    "message": f"Done. I've reduced your {category} budget by {pct}% from ${old_amount:.2f} to ${new_amount:.2f}.",
                    "action": "adjust_budget",
                    "budget_changes": [
                        {
                            "category": category,
                            "previous": old_amount,
                            "new": new_amount,
                            "reduction_pct": pct,
                        }
                    ],
                    "updated_metrics": {f"{category.lower()}_budget": new_amount},
                }

        return {
            "message": f"Category '{category}' not found in budget recommendations.",
            "action": "error",
            "suggestions": [],
            "updated_metrics": {},
        }

    def _handle_increase_command(self, message: str, report: Dict) -> Dict[str, Any]:
        """Handle budget increase commands."""
        category = self._extract_category(message)
        amount = self._extract_amount(message)

        if not category:
            return {
                "message": "Which category would you like to increase?",
                "action": "clarify",
                "suggestions": ["Increase Housing by $100", "Increase Food by $50"],
                "updated_metrics": {},
            }

        if not amount:
            return {
                "message": f"How much would you like to increase {category} by? (e.g., 'Increase {category} by $100')",
                "action": "clarify",
                "suggestions": [
                    f"Increase {category} by $50",
                    f"Increase {category} by $100",
                ],
                "updated_metrics": {},
            }

        # Find and update category
        for rec in report.get("budget_recommendations", []):
            if rec.get("category") == category:
                old_amount = rec.get("suggested_amount", 0)
                new_amount = old_amount + amount

                return {
                    "message": f"Done. I've increased your {category} budget by ${amount:.2f} to ${new_amount:.2f}.",
                    "action": "adjust_budget",
                    "budget_changes": [
                        {
                            "category": category,
                            "previous": old_amount,
                            "new": new_amount,
                            "increase": amount,
                        }
                    ],
                    "updated_metrics": {f"{category.lower()}_budget": new_amount},
                }

        return {
            "message": f"Category '{category}' not found in budget recommendations.",
            "action": "error",
            "suggestions": [],
            "updated_metrics": {},
        }

    def _generate_suggestions(self, report: Dict) -> Dict[str, Any]:
        """Generate AI-powered suggestions based on current data."""
        suggestions = []

        for cat in report.get("category_breakdown", []):
            if cat.get("percent", 0) > 30:
                suggestions.append(
                    f"You're spending {cat.get('percent', 0):.0f}% on {cat.get('category')}. Try: 'Reduce {cat.get('category')} to 25%'"
                )

        savings_rate = report.get("savings_rate", 0)
        if savings_rate < 10:
            suggestions.append(
                f"Current savings is {savings_rate:.1f}%. Try: 'Save 15% of income'"
            )
        elif savings_rate < 20:
            suggestions.append(
                f"Great savings rate of {savings_rate:.1f}%! Try: 'Save 20% of income'"
            )

        risk_score = report.get("risk_score", 0)
        if risk_score > 0.5:
            suggestions.append(
                f"High risk score ({risk_score:.1f}). Review anomalies in the report."
            )

        if suggestions:
            return {
                "message": "Here are some suggestions based on your data:\n"
                + "\n".join(f"• {s}" for s in suggestions),
                "action": "suggestions",
                "suggestions": suggestions,
                "updated_metrics": {},
            }
        else:
            return {
                "message": "Your budget looks balanced! Would you like to try a simulation? (e.g., 'What if I spend $200 less on rent?')",
                "action": "general",
                "suggestions": [
                    "What if I spend $200 less on rent?",
                    "Save 20% of income",
                    "Reduce Food by 15%",
                ],
                "updated_metrics": {},
            }


# Singleton instance
_conversation_agent: Optional[ConversationAgent] = None


def get_conversation_agent() -> ConversationAgent:
    """Get the conversation agent singleton."""
    global _conversation_agent
    if _conversation_agent is None:
        _conversation_agent = ConversationAgent()
    return _conversation_agent
