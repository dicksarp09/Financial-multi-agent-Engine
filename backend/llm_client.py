import os
from typing import List, Dict, Any, Optional
from groq import Groq
import logging

logger = logging.getLogger(__name__)

# System prompt for the financial agent
FINANCIAL_AGENT_SYSTEM_PROMPT = """You are a Financial Analysis Agent. Your role is to help users analyze their financial data, 
optimize budgets, and understand spending patterns.

You can:
1. Answer questions about their financial data
2. Suggest budget optimizations (e.g., "Reduce housing to 30%")
3. Run what-if simulations (e.g., "What if I spend $200 less on rent?")
4. Explain anomalies in transactions
5. Provide financial advice based on the data

When responding:
- Be specific about amounts and percentages
- Use the user's actual data when available
- Suggest actionable changes
- Format numbers with currency symbols and commas
- Always confirm when you've made changes to their budget

Current context:
- Report data: {report_summary}
- Recent transactions: {recent_transactions}

Conversation history:
{conversation_history}

Respond in a helpful, professional manner. If you need to clarify something, ask follow-up questions."""


class LLMClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not set")
        self.client = Groq(api_key=self.api_key)
        self.model = "openai/gpt-oss-120b"
    
    def build_context(self, report: Optional[Dict], transactions: List[Dict], conversation_history: List[Dict]) -> str:
        """Build context string from report and transactions"""
        
        # Report summary
        if report:
            report_summary = f"""
- Total Income: ${report.get('total_income', 0):,.2f}
- Total Expenses: ${report.get('total_expenses', 0):,.2f}
- Savings Rate: {report.get('savings_rate', 0):.1f}%
- Risk Score: {report.get('risk_score', 0):.1f}

Category Breakdown:
{self._format_categories(report.get('category_breakdown', []))}

Budget Recommendations:
{self._format_budget_recs(report.get('budget_recommendations', []))}

Anomalies: {len(report.get('anomalies', []))} detected
"""
        else:
            report_summary = "No analysis data available. Please upload a CSV and run analysis first."
        
        # Recent transactions
        recent_txns = transactions[:10]
        recent_transactions = "\n".join([
            f"- {t.get('date')}: {t.get('description')} - ${t.get('amount'):,.2f} ({t.get('category', 'Uncategorized')})"
            for t in recent_txns
        ]) if recent_txns else "No transactions"
        
        # Conversation history
        conv_history = "\n".join([
            f"{'User' if m.get('role') == 'user' else 'Assistant'}: {m.get('message', '')}"
            for m in conversation_history[-5:]  # Last 5 messages
        ]) if conversation_history else "No previous conversation"
        
        return FINANCIAL_AGENT_SYSTEM_PROMPT.format(
            report_summary=report_summary,
            recent_transactions=recent_transactions,
            conversation_history=conv_history
        )
    
    def _format_categories(self, categories: List[Dict]) -> str:
        if not categories:
            return "No categories"
        return "\n".join([
            f"- {c.get('category')}: ${c.get('amount', 0):,.2f} ({c.get('percent', 0):.1f}%)"
            for c in categories[:8]
        ])
    
    def _format_budget_recs(self, recs: List[Dict]) -> str:
        if not recs:
            return "No recommendations"
        return "\n".join([
            f"- {r.get('category')}: ${r.get('current_amount', 0):,.2f} -> ${r.get('suggested_amount', 0):,.2f} ({r.get('impact')})"
            for r in recs[:5]
        ])
    
    def chat(
        self, 
        message: str, 
        report: Optional[Dict] = None, 
        transactions: List[Dict] = [],
        conversation_history: List[Dict] = []
    ) -> Dict[str, Any]:
        """Send a chat message and get response"""
        
        logger.info(f"GROQ_API_KEY present: {bool(self.api_key)}")
        logger.info(f"GROQ_API_KEY length: {len(self.api_key) if self.api_key else 0}")
        
        context = self.build_context(report, transactions, conversation_history)
        
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": context},
            {"role": "user", "content": message}
        ]
        
        try:
            logger.info(f"Calling Groq API with model: {self.model}")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1024
            )
            logger.info(f"Groq API response received")
            
            return {
                "success": True,
                "message": response.choices[0].message.content,
                "model": self.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                }
            }
        except Exception as e:
            logger.error(f"Groq API error: {type(e).__name__}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"I encountered an error: {str(e)}"
            }
    
    def extract_action(self, message: str) -> Dict[str, Any]:
        """Extract structured action from message using LLM"""
        
        extraction_prompt = f"""Analyze this user message and extract the intended action. 
Return a JSON object with:
- action_type: one of "reduce_category", "increase_category", "save_percent", "what_if", "ignore_transaction", "general"
- category: the category name if applicable (e.g., "Housing", "Food")
- amount: the dollar amount if applicable
- percentage: the percentage if applicable
- original_message: the user's message

User message: {message}

Return ONLY valid JSON, no other text."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You extract structured data from user messages. Return valid JSON only."},
                    {"role": "user", "content": extraction_prompt}
                ],
                temperature=0.1,
                max_tokens=256,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            return {"success": True, **result}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton
_llm_client: Optional[LLMClient] = None

def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
