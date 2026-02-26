import os
import sqlite3
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "financial_agent.db")

# Ensure data directory exists
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)


class Database:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                status TEXT NOT NULL,
                anomalies_count INTEGER DEFAULT 0,
                budget_change_percent REAL DEFAULT 0,
                version INTEGER DEFAULT 1,
                risk_score REAL DEFAULT 0,
                total_income REAL DEFAULT 0,
                total_expenses REAL DEFAULT 0,
                savings_rate REAL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                date TEXT NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT,
                is_anomaly INTEGER DEFAULT 0,
                risk_score REAL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)
        
        # Reports table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                version INTEGER DEFAULT 1,
                total_income REAL DEFAULT 0,
                total_expenses REAL DEFAULT 0,
                savings_rate REAL DEFAULT 0,
                risk_score REAL DEFAULT 0,
                category_breakdown TEXT,
                anomalies TEXT,
                budget_recommendations TEXT,
                execution_trace TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)
        
        # Conversation history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    # Session methods
    def create_session(self, session_id: str, date: str, status: str = "Running") -> None:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (id, date, status) VALUES (?, ?, ?)",
            (session_id, date, status)
        )
        conn.commit()
        conn.close()
    
    def update_session(self, session_id: str, **kwargs) -> None:
        conn = self.get_connection()
        cursor = conn.cursor()
        fields = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [session_id]
        cursor.execute(f"UPDATE sessions SET {fields}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", values)
        conn.commit()
        conn.close()
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def get_all_sessions(self) -> List[Dict]:
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    # Transaction methods
    def save_transactions(self, session_id: str, transactions: List[Dict]) -> None:
        conn = self.get_connection()
        cursor = conn.cursor()
        for txn in transactions:
            cursor.execute(
                """INSERT OR REPLACE INTO transactions 
                   (id, session_id, date, description, amount, category, is_anomaly, risk_score) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (txn.get("id"), session_id, txn.get("date"), txn.get("description"),
                 txn.get("amount"), txn.get("category"), 
                 1 if txn.get("isAnomaly") else 0, txn.get("riskScore", 0))
            )
        conn.commit()
        conn.close()
    
    def get_transactions(self, session_id: str) -> List[Dict]:
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transactions WHERE session_id = ?", (session_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    # Report methods
    def save_report(self, session_id: str, report_data: Dict) -> None:
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if report exists
        cursor.execute("SELECT id FROM reports WHERE session_id = ? ORDER BY version DESC LIMIT 1", (session_id,))
        existing = cursor.fetchone()
        
        version = (existing[0] + 1) if existing else 1
        
        cursor.execute(
            """INSERT INTO reports 
               (session_id, version, total_income, total_expenses, savings_rate, risk_score,
                category_breakdown, anomalies, budget_recommendations, execution_trace)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, version, report_data.get("totalIncome", 0),
             report_data.get("totalExpenses", 0), report_data.get("savingsRate", 0),
             report_data.get("riskScore", 0),
             json.dumps(report_data.get("categoryBreakdown", [])),
             json.dumps(report_data.get("anomalies", [])),
             json.dumps(report_data.get("budgetRecommendations", [])),
             json.dumps(report_data.get("executionTrace", [])))
        )
        conn.commit()
        conn.close()
    
    def get_report(self, session_id: str) -> Optional[Dict]:
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM reports WHERE session_id = ? ORDER BY version DESC LIMIT 1",
            (session_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        result = dict(row)
        result["categoryBreakdown"] = json.loads(result.get("category_breakdown", "[]"))
        result["anomalies"] = json.loads(result.get("anomalies", "[]"))
        result["budgetRecommendations"] = json.loads(result.get("budget_recommendations", "[]"))
        result["executionTrace"] = json.loads(result.get("execution_trace", "[]"))
        return result
    
    # Conversation history
    def add_message(self, session_id: str, role: str, message: str) -> None:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversation_history (session_id, role, message) VALUES (?, ?, ?)",
            (session_id, role, message)
        )
        conn.commit()
        conn.close()
    
    def get_conversation_history(self, session_id: str, limit: int = 10) -> List[Dict]:
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """SELECT * FROM conversation_history 
               WHERE session_id = ? 
               ORDER BY created_at DESC 
               LIMIT ?""",
            (session_id, limit)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]


# Singleton instance
_db: Optional[Database] = None

def get_database() -> Database:
    global _db
    if _db is None:
        _db = Database()
    return _db
