"""
FastAPI Backend for Financial Agent
"""

import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import json
import asyncio
import re
from enum import Enum

# Import database and LLM
from database import get_database
from llm_client import get_llm_client

app = FastAPI(title="Financial Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Enums
class AgentState(str, Enum):
    INIT = "INIT"
    INGEST = "INGEST"
    CATEGORIZE = "CATEGORIZE"
    ANALYZE = "ANALYZE"
    BUDGET = "BUDGET"
    EVALUATE = "EVALUATE"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class SessionStatus(str, Enum):
    COMPLETE = "Complete"
    AWAITING_APPROVAL = "Awaiting Approval"
    FAILED = "Failed"
    RUNNING = "Running"


# Models
class Transaction(BaseModel):
    id: str
    date: str
    description: str
    amount: float
    category: Optional[str] = None
    isAnomaly: Optional[bool] = False
    riskScore: Optional[float] = 0.0


class Session(BaseModel):
    id: str
    date: str
    status: SessionStatus
    anomaliesCount: int
    budgetChangePercent: float
    version: int
    riskScore: float
    totalIncome: float
    totalExpenses: float
    savingsRate: float


class WorkflowStep(BaseModel):
    state: AgentState
    label: str
    completed: bool
    running: bool
    error: Optional[bool] = False


class AgentLog(BaseModel):
    id: str
    timestamp: str
    agent: str
    action: str
    duration: int
    tokens: Optional[int] = 0
    cost: Optional[float] = 0.0
    details: Optional[str] = ""


class CategoryBreakdown(BaseModel):
    category: str
    amount: float
    percent: float
    previousMonth: Optional[float] = None
    change: Optional[float] = None


class Anomaly(BaseModel):
    id: str
    transactionId: str
    description: str
    amount: float
    reason: str
    riskScore: float
    severity: str


class BudgetRecommendation(BaseModel):
    category: str
    currentAmount: float
    suggestedAmount: float
    rationale: str
    impact: str


class ReportData(BaseModel):
    sessionId: str
    version: int
    totalIncome: float
    totalExpenses: float
    savingsRate: float
    riskScore: float
    categoryBreakdown: List[CategoryBreakdown]
    anomalies: List[Anomaly]
    budgetRecommendations: List[BudgetRecommendation]
    executionTrace: List[AgentLog]
    createdAt: str


class ApprovalRequest(BaseModel):
    id: str
    type: str
    description: str
    amount: Optional[float] = None
    riskScore: Optional[float] = None
    status: str
    requestedAt: str


class SystemStatus(BaseModel):
    agentHealth: str
    llmAvailable: bool
    tokensUsedToday: int
    tokensLimit: int
    activeSessions: int


class Settings(BaseModel):
    approvalThreshold: float
    anomalySensitivity: str
    llmModel: str
    tokenLimitDaily: int
    dataRetentionDays: int


class ConversationMessage(BaseModel):
    role: str
    content: str
    timestamp: str


# In-memory storage
sessions_db: Dict[str, Session] = {}
reports_db: Dict[str, ReportData] = {}
workflow_state: Dict[str, List[WorkflowStep]] = {}
execution_logs: Dict[str, List[AgentLog]] = {}
current_approvals: Dict[str, ApprovalRequest] = {}
transactions_db: Dict[str, List[Transaction]] = {}
system_status = SystemStatus(
    agentHealth="healthy",
    llmAvailable=True,
    tokensUsedToday=45000,
    tokensLimit=100000,
    activeSessions=0,
)
settings = Settings(
    approvalThreshold=0.7,
    anomalySensitivity="medium",
    llmModel="llama-3.1-70b-versatile",
    tokenLimitDaily=100000,
    dataRetentionDays=90,
)

# Initialize sample data
def init_sample_data():
    sample_sessions = [
        Session(
            id="sess-001", date="2024-02-24", status=SessionStatus.COMPLETE,
            anomaliesCount=2, budgetChangePercent=5.2, version=3, riskScore=0.3,
            totalIncome=11000, totalExpenses=5010, savingsRate=54.5
        ),
        Session(
            id="sess-002", date="2024-02-23", status=SessionStatus.COMPLETE,
            anomaliesCount=1, budgetChangePercent=-2.1, version=2, riskScore=0.2,
            totalIncome=10500, totalExpenses=4800, savingsRate=54.3
        ),
        Session(
            id="sess-003", date="2024-02-22", status=SessionStatus.COMPLETE,
            anomaliesCount=3, budgetChangePercent=12.5, version=1, riskScore=0.8,
            totalIncome=11000, totalExpenses=5200, savingsRate=52.7
        ),
        Session(
            id="sess-004", date="2024-02-20", status=SessionStatus.FAILED,
            anomaliesCount=0, budgetChangePercent=0, version=1, riskScore=0.0,
            totalIncome=0, totalExpenses=0, savingsRate=0
        ),
    ]
    for session in sample_sessions:
        sessions_db[session.id] = session

init_sample_data()


# Health check
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# System Status
@app.get("/api/system/status", response_model=SystemStatus)
async def get_system_status():
    return system_status


@app.get("/api/system/settings", response_model=Settings)
async def get_settings():
    return settings


@app.post("/api/system/settings")
async def update_settings(new_settings: Settings):
    global settings
    settings = new_settings
    return {"status": "updated", "settings": settings}


# Sessions
@app.get("/api/sessions", response_model=List[Session])
async def get_sessions():
    return list(sessions_db.values())


@app.get("/api/sessions/{session_id}", response_model=Session)
async def get_session(session_id: str):
    if session_id not in sessions_db:
        raise HTTPException(status_code=404, detail="Session not found")
    return sessions_db[session_id]


@app.post("/api/sessions")
async def create_session():
    session_id = f"sess-{uuid.uuid4().hex[:8]}"
    session = Session(
        id=session_id,
        date=datetime.now().strftime("%Y-%m-%d"),
        status=SessionStatus.RUNNING,
        anomaliesCount=0,
        budgetChangePercent=0,
        version=1,
        riskScore=0.0,
        totalIncome=0,
        totalExpenses=0,
        savingsRate=0.0,
    )
    sessions_db[session_id] = session
    
    # Also save to database for persistence
    try:
        db = get_database()
        db.create_session(session_id, session.date, "Running")
        print(f"[DEBUG] Session saved to database: {session_id}")
    except Exception as e:
        print(f"[ERROR] Failed to save session to database: {e}")
    
    system_status.activeSessions += 1
    return session


# File Upload & Validation
@app.post("/api/upload/validate")
async def validate_file(file: UploadFile = File(...), session_id: Optional[str] = None):
    content = await file.read()
    
    try:
        text = content.decode("utf-8")
        lines = text.strip().split("\n")
        
        if len(lines) < 2:
            return {"valid": False, "errors": ["File must have a header row and at least one data row"]}
        
        header = lines[0].lower()
        required_cols = ["date", "description", "amount"]
        missing = [col for col in required_cols if col not in header]
        
        if missing:
            return {"valid": False, "errors": [f"Missing required columns: {', '.join(missing)}"]}
        
        transactions = []
        errors = []
        
        for i, line in enumerate(lines[1:], start=2):
            try:
                parts = line.split(",")
                if len(parts) < 3:
                    errors.append(f"Line {i}: Not enough columns")
                    continue
                
                txn = Transaction(
                    id=f"txn-{i}",
                    date=parts[0].strip(),
                    description=parts[1].strip(),
                    amount=float(parts[2].strip()),
                )
                transactions.append(txn)
            except ValueError as e:
                errors.append(f"Line {i}: {str(e)}")
        
        if errors and not transactions:
            return {"valid": False, "errors": errors}
        
        # Store transactions if session_id provided
        if session_id:
            transactions_db[session_id] = transactions
            print(f"[DEBUG] validate_file: stored {len(transactions)} transactions for session_id={session_id}")
            
            # Also save to database for persistence
            try:
                db = get_database()
                db.save_transactions(session_id, [
                    {"id": t.id, "date": t.date, "description": t.description, "amount": t.amount, "category": getattr(t, 'category', None)}
                    for t in transactions
                ])
                print(f"[DEBUG] Transactions saved to database")
            except Exception as e:
                print(f"[ERROR] Failed to save transactions to database: {e}")
        
        return {
            "valid": True,
            "transactions": [t.model_dump() for t in transactions[:10]],
            "totalCount": len(transactions),
            "errors": errors[:5] if errors else []
        }
        
    except UnicodeDecodeError:
        return {"valid": False, "errors": ["File must be UTF-8 encoded"]}


# Workflow Execution
@app.get("/api/workflow/{session_id}")
async def get_workflow(session_id: str):
    if session_id not in workflow_state:
        workflow_state[session_id] = [
            WorkflowStep(state=AgentState.INIT, label="Initialize", completed=False, running=False),
            WorkflowStep(state=AgentState.INGEST, label="Ingest Data", completed=False, running=False),
            WorkflowStep(state=AgentState.CATEGORIZE, label="Categorize", completed=False, running=False),
            WorkflowStep(state=AgentState.ANALYZE, label="Analyze", completed=False, running=False),
            WorkflowStep(state=AgentState.BUDGET, label="Budget", completed=False, running=False),
            WorkflowStep(state=AgentState.EVALUATE, label="Evaluate", completed=False, running=False),
            WorkflowStep(state=AgentState.COMPLETE, label="Complete", completed=False, running=False),
        ]
    return workflow_state[session_id]


@app.post("/api/workflow/{session_id}/execute")
async def execute_workflow(session_id: str, background_tasks: BackgroundTasks):
    """Start workflow execution"""
    
    if session_id not in workflow_state:
        await get_workflow(session_id)  # Initialize
    
    execution_logs[session_id] = []
    
    # Get transactions for this session
    transactions = transactions_db.get(session_id, [])
    print(f"[DEBUG] execute_workflow: session_id={session_id}, transactions_count={len(transactions)}")
    
    # Run workflow in background
    async def run_workflow():
        states = [
            (AgentState.INIT, "Initialize"),
            (AgentState.INGEST, "Ingest Data"),
            (AgentState.CATEGORIZE, "Categorize"),
            (AgentState.ANALYZE, "Analyze"),
            (AgentState.BUDGET, "Budget"),
            (AgentState.EVALUATE, "Evaluate"),
            (AgentState.COMPLETE, "Complete"),
        ]
        
        # Processing state
        categorized_txns = []
        anomalies_detected = []
        total_income = 0.0
        total_expenses = 0.0
        category_totals = {}
        
        # Initial delay before starting
        await asyncio.sleep(0.5)
        
        for idx, (state, label) in enumerate(states):
            # Update workflow state
            for i, step in enumerate(workflow_state[session_id]):
                step.completed = i < idx
                step.running = i == idx
                step.error = False
            
            # Add log entry with real data
            tokens = 0
            cost = 0.0
            details = f"{label} step completed successfully"
            
            if state == AgentState.INGEST:
                details = f"Ingested {len(transactions)} transactions"
            
            elif state == AgentState.CATEGORIZE:
                tokens = 400
                cost = 0.0002
                # Categorize transactions based on description keywords
                category_keywords = {
                    "Housing": ["rent", "mortgage", "housing"],
                    "Food": ["grocery", "restaurant", "food", "coffee", "cafe", "supermarket"],
                    "Transportation": ["gas", "fuel", "uber", "lyft", "car", "transport"],
                    "Utilities": ["electric", "water", "internet", "phone", "utility"],
                    "Entertainment": ["netflix", "spotify", "movie", "concert", "entertainment"],
                    "Healthcare": ["doctor", "pharmacy", "medical", "health", "dentist"],
                    "Shopping": ["amazon", "shopping", "clothing", "gift"],
                    "Insurance": ["insurance", "policy"],
                    "Fitness": ["gym", "fitness"],
                    "Income": ["salary", "bonus", "freelance", "consulting", "deposit"],
                }
                
                for txn in transactions:
                    category = "Other"
                    for cat, keywords in category_keywords.items():
                        if any(kw in txn.description.lower() for kw in keywords):
                            category = cat
                            break
                    
                    # Override if user provided category
                    if txn.category:
                        category = txn.category
                    
                    txn.category = category
                    categorized_txns.append(txn)
                    
                    if txn.amount > 0:
                        total_income += txn.amount
                    else:
                        total_expenses += abs(txn.amount)
                    
                    category_totals[category] = category_totals.get(category, 0) + txn.amount
                
                details = f"Categorized {len(categorized_txns)} transactions into {len(category_totals)} categories"
            
            elif state == AgentState.ANALYZE:
                # Detect anomalies (transactions > 3x average expense or > 50% of income)
                avg_expense = total_expenses / len(transactions) if transactions else 0
                for txn in categorized_txns:
                    if txn.amount < 0:
                        abs_amount = abs(txn.amount)
                        if abs_amount > avg_expense * 3 or abs_amount > total_income * 0.3:
                            risk_score = min(1.0, abs_amount / total_income)
                            anomalies_detected.append({
                                "id": txn.id,
                                "transactionId": txn.id,
                                "description": txn.description,
                                "amount": txn.amount,
                                "reason": f"Unusual transaction amount: ${abs_amount:.2f}",
                                "riskScore": risk_score,
                                "severity": "high" if risk_score > 0.5 else "medium"
                            })
                            txn.isAnomaly = True
                            txn.riskScore = risk_score
                
                details = f"Analysis complete: ${total_income:.2f} income, ${total_expenses:.2f} expenses, {len(anomalies_detected)} anomalies"
            
            elif state == AgentState.BUDGET:
                tokens = 400
                cost = 0.0002
                details = f"Generated budget recommendations based on {len(category_totals)} categories"
            
            log = AgentLog(
                id=f"log-{idx}",
                timestamp=datetime.utcnow().isoformat(),
                agent=state.value.lower(),
                action=f"Executing {label}",
                duration=350,
                tokens=tokens,
                cost=cost,
                details=details
            )
            execution_logs[session_id].append(log)
            
            # Check for anomaly in CATEGORIZE - trigger approval for high-risk anomalies
            if state == AgentState.CATEGORIZE and anomalies_detected:
                high_risk = [a for a in anomalies_detected if a["riskScore"] > 0.5]
                if high_risk:
                    approval = ApprovalRequest(
                        id=f"approval-{uuid.uuid4().hex[:8]}",
                        type="ANOMALY_DETECTED",
                        description=f"High-risk anomaly detected: {high_risk[0]['description']}",
                        amount=high_risk[0]["amount"],
                        riskScore=high_risk[0]["riskScore"],
                        status="PENDING",
                        requestedAt=datetime.utcnow().isoformat()
                    )
                    current_approvals[session_id] = approval
                    
                    # Set to waiting approval
                    for step in workflow_state[session_id]:
                        if step.state == AgentState.CATEGORIZE:
                            step.completed = True
                            step.running = False
                        elif step.state == AgentState.WAITING_APPROVAL:
                            step.running = True
                    
                    # Add waiting approval step if not exists
                    if not any(s.state == AgentState.WAITING_APPROVAL for s in workflow_state[session_id]):
                        workflow_state[session_id].insert(
                            idx + 1,
                            WorkflowStep(state=AgentState.WAITING_APPROVAL, label="Awaiting Approval", completed=False, running=True)
                        )
                    
                    return  # Stop here until approved
            
            # Add delay between steps to make processing visible
            await asyncio.sleep(1.5)
        
        # Mark all steps as complete including COMPLETE
        for step in workflow_state[session_id]:
            step.completed = True
            step.running = False
        
        # Compute savings rate
        savings_rate = ((total_income - total_expenses) / total_income * 100) if total_income > 0 else 0
        
        # Update session status
        if session_id in sessions_db:
            sessions_db[session_id].status = SessionStatus.COMPLETE
            sessions_db[session_id].totalIncome = total_income
            sessions_db[session_id].totalExpenses = total_expenses
            sessions_db[session_id].savingsRate = savings_rate
            sessions_db[session_id].anomaliesCount = len(anomalies_detected)
        
        # Generate report
        category_breakdown = []
        for cat, amount in category_totals.items():
            if amount < 0:
                category_breakdown.append(CategoryBreakdown(
                    category=cat,
                    amount=abs(amount),
                    percent=round(abs(amount) / total_expenses * 100, 1) if total_expenses > 0 else 0
                ))
        
        # Budget recommendations
        budget_recommendations = []
        for cat, amount in category_totals.items():
            if amount < 0:
                suggested = abs(amount) * 0.9  # Suggest 10% reduction
                budget_recommendations.append(BudgetRecommendation(
                    category=cat,
                    currentAmount=abs(amount),
                    suggestedAmount=suggested,
                    rationale=f"Current spending ${abs(amount):.2f} - recommend ${suggested:.2f} (10% reduction)",
                    impact=f"-${abs(amount) - suggested:.2f}"
                ))
        
        # Create report
        report = ReportData(
            sessionId=session_id,
            version=1,
            totalIncome=total_income,
            totalExpenses=total_expenses,
            savingsRate=savings_rate,
            riskScore=sum(a["riskScore"] for a in anomalies_detected) / len(anomalies_detected) if anomalies_detected else 0,
            categoryBreakdown=category_breakdown,
            anomalies=[Anomaly(**a) for a in anomalies_detected],
            budgetRecommendations=budget_recommendations,
            executionTrace=execution_logs.get(session_id, []),
            createdAt=datetime.utcnow().isoformat()
        )
        reports_db[session_id] = report
        
        # Also save to database for persistence
        try:
            db = get_database()
            db.save_report(session_id, {
                "totalIncome": report.totalIncome,
                "totalExpenses": report.totalExpenses,
                "savingsRate": report.savingsRate,
                "riskScore": report.riskScore,
                "categoryBreakdown": [{"category": c.category, "amount": c.amount, "percent": c.percent} for c in report.categoryBreakdown],
                "anomalies": [{"id": a.id, "transactionId": a.transactionId, "description": a.description, "amount": a.amount, "reason": a.reason, "riskScore": a.riskScore, "severity": a.severity} for a in report.anomalies],
                "budgetRecommendations": [{"category": b.category, "currentAmount": b.currentAmount, "suggestedAmount": b.suggestedAmount, "rationale": b.rationale, "impact": b.impact} for b in report.budgetRecommendations],
                "executionTrace": []
            })
            print(f"[DEBUG] Report saved to database for session {session_id}")
        except Exception as e:
            print(f"[ERROR] Failed to save to database: {e}")
        
        # Clear approval after completion
        if session_id in current_approvals:
            del current_approvals[session_id]
        
        system_status.activeSessions = max(0, system_status.activeSessions - 1)
        print(f"[DEBUG] Workflow completed for session {session_id}")
    
    # Add error handling wrapper
    async def run_workflow_safe():
        try:
            await run_workflow()
        except Exception as e:
            print(f"[ERROR] Workflow failed: {e}")
            import traceback
            traceback.print_exc()
    
    background_tasks.add_task(run_workflow_safe)
    return {"status": "started", "session_id": session_id}


# Execution Logs
@app.get("/api/workflow/{session_id}/logs")
async def get_execution_logs(session_id: str):
    return execution_logs.get(session_id, [])


# Approval
@app.get("/api/approvals/{session_id}")
async def get_approval(session_id: str):
    return current_approvals.get(session_id)


@app.post("/api/approvals/{session_id}/respond")
async def respond_to_approval(session_id: str, action: str):
    """Respond to approval request (approve/reject)"""
    
    if session_id not in current_approvals:
        raise HTTPException(status_code=404, detail="No pending approval")
    
    approval = current_approvals[session_id]
    
    if action == "approve":
        approval.status = "APPROVED"
        
        # Resume workflow
        async def resume_workflow():
            # Get transactions
            transactions = transactions_db.get(session_id, [])
            
            # Re-process to get totals (same logic as before)
            category_keywords = {
                "Housing": ["rent", "mortgage", "housing"],
                "Food": ["grocery", "restaurant", "food", "coffee", "cafe", "supermarket"],
                "Transportation": ["gas", "fuel", "uber", "lyft", "car", "transport"],
                "Utilities": ["electric", "water", "internet", "phone", "utility"],
                "Entertainment": ["netflix", "spotify", "movie", "concert", "entertainment"],
                "Healthcare": ["doctor", "pharmacy", "medical", "health", "dentist"],
                "Shopping": ["amazon", "shopping", "clothing", "gift"],
                "Insurance": ["insurance", "policy"],
                "Fitness": ["gym", "fitness"],
                "Income": ["salary", "bonus", "freelance", "consulting", "deposit"],
            }
            
            categorized_txns = []
            total_income = 0.0
            total_expenses = 0.0
            category_totals = {}
            anomalies_detected = []
            
            for txn in transactions:
                category = "Other"
                for cat, keywords in category_keywords.items():
                    if any(kw in txn.description.lower() for kw in keywords):
                        category = cat
                        break
                if txn.category:
                    category = txn.category
                txn.category = category
                categorized_txns.append(txn)
                
                if txn.amount > 0:
                    total_income += txn.amount
                else:
                    total_expenses += abs(txn.amount)
                category_totals[category] = category_totals.get(category, 0) + txn.amount
            
            # Detect anomalies
            avg_expense = total_expenses / len(transactions) if transactions else 0
            for txn in categorized_txns:
                if txn.amount < 0:
                    abs_amount = abs(txn.amount)
                    if abs_amount > avg_expense * 3 or abs_amount > total_income * 0.3:
                        risk_score = min(1.0, abs_amount / total_income)
                        anomalies_detected.append({
                            "id": txn.id,
                            "transactionId": txn.id,
                            "description": txn.description,
                            "amount": txn.amount,
                            "reason": f"Unusual transaction amount: ${abs_amount:.2f}",
                            "riskScore": risk_score,
                            "severity": "high" if risk_score > 0.5 else "medium"
                        })
            
            states = [
                (AgentState.ANALYZE, "Analyze"),
                (AgentState.BUDGET, "Budget"),
                (AgentState.EVALUATE, "Evaluate"),
                (AgentState.COMPLETE, "Complete"),
            ]
            
            # Find where we left off
            current_idx = 0
            for i, step in enumerate(workflow_state[session_id]):
                if step.state == AgentState.WAITING_APPROVAL:
                    current_idx = i
                    break
            
            for idx, (state, label) in enumerate(states):
                step_idx = current_idx + idx + 1
                if step_idx < len(workflow_state[session_id]):
                    workflow_state[session_id][step_idx].completed = False
                    workflow_state[session_id][step_idx].running = True
                
                tokens = 0
                cost = 0.0
                details = f"{label} step completed successfully"
                
                if state == AgentState.ANALYZE:
                    details = f"Analysis complete: ${total_income:.2f} income, ${total_expenses:.2f} expenses, {len(anomalies_detected)} anomalies"
                elif state == AgentState.BUDGET:
                    tokens = 400
                    cost = 0.0002
                    details = f"Generated budget recommendations based on {len(category_totals)} categories"
                
                log = AgentLog(
                    id=f"log-resume-{idx}",
                    timestamp=datetime.utcnow().isoformat(),
                    agent=state.value.lower(),
                    action=f"Executing {label}",
                    duration=350,
                    tokens=tokens,
                    cost=cost,
                    details=details
                )
                execution_logs[session_id].append(log)
                await asyncio.sleep(0.8)
            # Mark complete
            for step in workflow_state[session_id]:
                step.completed = True
                step.running = False
            
            # Compute savings rate
            savings_rate = ((total_income - total_expenses) / total_income * 100) if total_income > 0 else 0
            
            print(f"[DEBUG] Report: total_income={total_income}, total_expenses={total_expenses}, savings_rate={savings_rate}")
            print(f"[DEBUG] Category totals: {category_totals}")
            
            # Update session status
            if session_id in sessions_db:
                sessions_db[session_id].status = SessionStatus.COMPLETE
                sessions_db[session_id].totalIncome = total_income
                sessions_db[session_id].totalExpenses = total_expenses
                sessions_db[session_id].savingsRate = savings_rate
                sessions_db[session_id].anomaliesCount = len(anomalies_detected)
            
            # Generate report
            category_breakdown = []
            for cat, amount in category_totals.items():
                if amount < 0:
                    category_breakdown.append(CategoryBreakdown(
                        category=cat,
                        amount=abs(amount),
                        percent=round(abs(amount) / total_expenses * 100, 1) if total_expenses > 0 else 0
                    ))
            
            # Budget recommendations
            budget_recommendations = []
            for cat, amount in category_totals.items():
                if amount < 0:
                    suggested = abs(amount) * 0.9
                    budget_recommendations.append(BudgetRecommendation(
                        category=cat,
                        currentAmount=abs(amount),
                        suggestedAmount=suggested,
                        rationale=f"Current spending ${abs(amount):.2f} - recommend ${suggested:.2f} (10% reduction)",
                        impact=f"-${abs(amount) - suggested:.2f}"
                    ))
            
            # Create report
            report = ReportData(
                sessionId=session_id,
                version=1,
                totalIncome=total_income,
                totalExpenses=total_expenses,
                savingsRate=savings_rate,
                riskScore=sum(a["riskScore"] for a in anomalies_detected) / len(anomalies_detected) if anomalies_detected else 0,
                categoryBreakdown=category_breakdown,
                anomalies=[Anomaly(**a) for a in anomalies_detected],
                budgetRecommendations=budget_recommendations,
                executionTrace=execution_logs.get(session_id, []),
                createdAt=datetime.utcnow().isoformat()
            )
            reports_db[session_id] = report
            
            # Clear approval after completion
            if session_id in current_approvals:
                del current_approvals[session_id]
            
            system_status.activeSessions = max(0, system_status.activeSessions - 1)
        
        asyncio.create_task(resume_workflow())
        
    elif action == "reject":
        approval.status = "REJECTED"
        if session_id in sessions_db:
            sessions_db[session_id].status = SessionStatus.FAILED
        # Clear approval after reject
        if session_id in current_approvals:
            del current_approvals[session_id]
        system_status.activeSessions = max(0, system_status.activeSessions - 1)
    
    return {"status": approval.status, "approval": approval}


# Reports
@app.get("/api/reports/{session_id}", response_model=ReportData)
async def get_report(session_id: str):
    print(f"[DEBUG] get_report: session_id={session_id}")
    
    # Try to get from database first
    try:
        db = get_database()
        db_report = db.get_report(session_id)
        if db_report:
            print(f"[DEBUG] Found report in database")
            return ReportData(
                sessionId=session_id,
                version=db_report.get("version", 1),
                totalIncome=db_report.get("total_income", 0),
                totalExpenses=db_report.get("total_expenses", 0),
                savingsRate=db_report.get("savings_rate", 0),
                riskScore=db_report.get("risk_score", 0),
                categoryBreakdown=[CategoryBreakdown(**c) for c in db_report.get("categoryBreakdown", [])],
                anomalies=[Anomaly(**a) for a in db_report.get("anomalies", [])],
                budgetRecommendations=[BudgetRecommendation(**b) for b in db_report.get("budgetRecommendations", [])],
                executionTrace=db_report.get("executionTrace", []),
                createdAt=db_report.get("created_at", datetime.utcnow().isoformat())
            )
    except Exception as e:
        print(f"[DEBUG] Database error: {e}")
    
    # Fallback to memory
    if session_id not in reports_db:
        # Generate a sample report
        report = ReportData(
            sessionId=session_id,
            version=1,
            totalIncome=11000,
            totalExpenses=5010,
            savingsRate=54.5,
            riskScore=0.3,
            categoryBreakdown=[
                CategoryBreakdown(category="Housing", amount=3000, percent=27.3),
                CategoryBreakdown(category="Food", amount=775, percent=7.0),
                CategoryBreakdown(category="Transportation", amount=235, percent=2.1),
                CategoryBreakdown(category="Utilities", amount=200, percent=1.8),
                CategoryBreakdown(category="Entertainment", amount=55, percent=0.5),
                CategoryBreakdown(category="Shopping", amount=200, percent=1.8),
                CategoryBreakdown(category="Other", amount=545, percent=5.0),
            ],
            anomalies=[
                Anomaly(
                    id="1", transactionId="txn_002", description="Apartment Rent",
                    amount=-1500, reason="IQR outlier: amount 1500.00 exceeds upper bound 432.50",
                    riskScore=1.0, severity="critical"
                ),
                Anomaly(
                    id="2", transactionId="txn_005", description="Cash Advance",
                    amount=-500, reason="IQR outlier: amount 500.00 exceeds upper bound 432.50",
                    riskScore=0.16, severity="low"
                ),
            ],
            budgetRecommendations=[
                BudgetRecommendation(
                    category="Housing", currentAmount=3000, suggestedAmount=2750,
                    rationale="Current spending 3000.00 exceeds recommended 2750.00 (25% of income)",
                    impact="-$250"
                ),
                BudgetRecommendation(
                    category="Food", currentAmount=775, suggestedAmount=1320,
                    rationale="Current spending 775.00 is below recommended 1320.00",
                    impact="+$545"
                ),
            ],
            executionTrace=execution_logs.get(session_id, []),
            createdAt=datetime.utcnow().isoformat()
        )
        reports_db[session_id] = report
        return report
    
    return reports_db[session_id]


@app.post("/api/reports/{session_id}/refine")
async def refine_report(session_id: str, instruction: str):
    """Refine report based on user instruction"""
    
    # Parse instruction and generate new version
    if session_id in reports_db:
        existing = reports_db[session_id]
        new_version = existing.version + 1
        
        # Simple refinement logic
        if "increase" in instruction.lower() and "food" in instruction.lower():
            for rec in existing.budgetRecommendations:
                if rec.category == "Food":
                    rec.suggestedAmount = rec.suggestedAmount * 1.1
                    rec.impact = f"+${int(rec.suggestedAmount - rec.currentAmount)}"
        
        new_report = ReportData(
            sessionId=session_id,
            version=new_version,
            totalIncome=existing.totalIncome,
            totalExpenses=existing.totalExpenses,
            savingsRate=existing.savingsRate,
            riskScore=existing.riskScore,
            categoryBreakdown=existing.categoryBreakdown,
            anomalies=existing.anomalies,
            budgetRecommendations=existing.budgetRecommendations,
            executionTrace=existing.executionTrace,
            createdAt=datetime.utcnow().isoformat()
        )
        reports_db[session_id] = new_report
        return new_report
    
    raise HTTPException(status_code=404, detail="Report not found")


# Export
@app.get("/api/reports/{session_id}/export")
async def export_report(session_id: str, format: str = "json"):
    """Export report in specified format"""
    
    report = await get_report(session_id)
    
    if format == "json":
        return report.model_dump_json()
    elif format == "csv":
        lines = ["category,amount,percent"]
        for cat in report.categoryBreakdown:
            lines.append(f"{cat.category},{cat.amount},{cat.percent}")
        return "\n".join(lines)
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")


# Conversation / NLP Processing using Groq LLM
class ConversationRequest(BaseModel):
    message: str

@app.post("/api/conversation/{session_id}")
async def send_message(session_id: str, request: ConversationRequest):
    """Process conversational refinement using Groq LLM"""
    
    message = request.message
    
    # Get database and LLM
    db = get_database()
    
    # Get report from database
    report_data = db.get_report(session_id)
    
    # Get transactions from database
    transactions_data = db.get_transactions(session_id)
    
    # Get conversation history
    history = db.get_conversation_history(session_id, limit=5)
    
    # Save user message
    db.add_message(session_id, "user", message)
    
    print(f"[DEBUG] Conversation: session_id={session_id}, transactions={len(transactions_data)}, report={'found' if report_data else 'NOT FOUND'}")
    
    if not report_data:
        response_msg = "Please run the analysis first before using conversational refinement. Upload a CSV file and start the analysis."
        db.add_message(session_id, "assistant", response_msg)
        return {
            "message": response_msg,
            "action": "error",
            "details": {},
            "suggestions": ["Upload a CSV and run analysis first"],
            "updatedMetrics": {}
        }
    
    # Try to use Groq LLM
    updated_metrics = {}
    try:
        print("[DEBUG] Getting LLM client...")
        llm = get_llm_client()
        print("[DEBUG] LLM client created successfully")
        
        # Convert to dict format for LLM
        report_dict = {
            "total_income": report_data.get("total_income", 0),
            "total_expenses": report_data.get("total_expenses", 0),
            "savings_rate": report_data.get("savings_rate", 0),
            "risk_score": report_data.get("risk_score", 0),
            "category_breakdown": report_data.get("categoryBreakdown", []),
            "budget_recommendations": report_data.get("budgetRecommendations", [])
        }
        
        transactions_list = [
            {"id": t.get("id"), "date": t.get("date"), "description": t.get("description"), 
             "amount": t.get("amount"), "category": t.get("category")}
            for t in transactions_data
        ]
        
        # Check if user wants to make changes
        message_lower = message.lower()
        updated_metrics = {}
        
        # Handle "cut [category]" or "reduce [category]" requests
        if "cut" in message_lower or "reduce" in message_lower or "increase" in message_lower:
            for cat in report_dict.get("category_breakdown", []):
                cat_name = cat.get("category", "").lower()
                if cat_name in message_lower:
                    # Extract percentage if mentioned
                    import re
                    pct_match = re.search(r'(\d+)\s*%', message)
                    amount_match = re.search(r'\$(\d+)', message)
                    
                    old_amount = cat.get("amount", 0)
                    new_amount = old_amount
                    
                    if pct_match:
                        pct = int(pct_match.group(1)) / 100
                        if "increase" in message_lower:
                            new_amount = old_amount * (1 + pct)
                        else:
                            new_amount = old_amount * (1 - pct)
                    elif amount_match:
                        amount_change = int(amount_match.group(1))
                        if "increase" in message_lower:
                            new_amount = old_amount + amount_change
                        else:
                            new_amount = max(0, old_amount - amount_change)
                    
                    # Update expenses and savings
                    expense_diff = old_amount - new_amount
                    new_total_expenses = report_dict["total_expenses"] - expense_diff
                    new_savings = ((report_dict["total_income"] - new_total_expenses) / report_dict["total_income"]) * 100
                    
                    # Update the category amount in the list
                    cat["amount"] = new_amount
                    
                    # Also update in report_data for saving
                    for cat_data in report_data.get("categoryBreakdown", []):
                        if cat_data.get("category", "").lower() == cat_name:
                            cat_data["amount"] = new_amount
                            break
                    
                    updated_metrics = {
                        "total_expenses": new_total_expenses,
                        "savings_rate": new_savings,
                        "category_changed": cat.get("category"),
                        "old_amount": old_amount,
                        "new_amount": new_amount
                    }
                    
                    # Update in memory
                    report_data["total_expenses"] = new_total_expenses
                    report_data["savings_rate"] = new_savings
                    
                    # Update in database
                    db.save_report(session_id, {
                        "totalIncome": report_dict["total_income"],
                        "totalExpenses": new_total_expenses,
                        "savingsRate": new_savings,
                        "riskScore": report_dict["risk_score"],
                        "categoryBreakdown": report_dict["category_breakdown"],
                        "budgetRecommendations": report_dict.get("budget_recommendations", []),
                        "anomalies": [],
                        "executionTrace": []
                    })
                    print(f"[DEBUG] Updated budget: {cat.get('category')} from {old_amount} to {new_amount}")
                    break
        
        # Get LLM response
        llm_response = llm.chat(
            message=message,
            report=report_dict,
            transactions=transactions_list,
            conversation_history=history
        )
        
        if llm_response.get("success"):
            response_msg = llm_response["message"]
            
            # If we made changes, add confirmation
            if updated_metrics:
                cat_name = updated_metrics.get("category_changed", "")
                old_amt = updated_metrics.get("old_amount", 0)
                new_amt = updated_metrics.get("new_amount", 0)
                response_msg = f"I've updated your budget. {cat_name} changed from ${old_amt:,.2f} to ${new_amt:,.2f}. The changes are now reflected on your dashboard.\n\n" + response_msg
        else:
            response_msg = f"I encountered an error: {llm_response.get('error')}. Let me try with the basic analysis instead."
        
    except Exception as e:
        print(f"[ERROR] LLM Error: {e}")
        response_msg = f"I'm having trouble connecting to the AI. Here's what I can tell you from your data:\n\n"
        response_msg += f"- Income: ${report_data.get('total_income', 0):,.2f}\n"
        response_msg += f"- Expenses: ${report_data.get('total_expenses', 0):,.2f}\n"
        response_msg += f"- Savings: {report_data.get('savings_rate', 0):.1f}%\n\n"
        response_msg += "Please try again in a moment."
    
    # Save assistant response
    db.add_message(session_id, "assistant", response_msg)
    
    return {
        "message": response_msg,
        "action": "completed",
        "details": {},
        "suggestions": [],
        "updatedMetrics": updated_metrics if updated_metrics else {}
    }
    
    try:
        # Use the agent architecture
        result = refine_session(
            session_id=session_id,
            message=message,
            report=report_dict,
            transactions=transactions_list
        )
        
        # Update report if metrics changed
        if result.get("updated_metrics"):
            updated = result["updated_metrics"]
            if "total_income" in updated:
                report.totalIncome = updated["total_income"]
            if "total_expenses" in updated:
                report.totalExpenses = updated["total_expenses"]
            if "savings_rate" in updated:
                report.savingsRate = updated["savings_rate"]
            reports_db[session_id] = report
        
        return {
            "message": result.get("message", ""),
            "action": result.get("action", ""),
            "details": result.get("details", {}),
            "suggestions": result.get("suggestions", []),
            "updatedMetrics": result.get("updated_metrics", {})
        }
        
    except Exception as e:
        print(f"Error in conversation agent: {e}")
        return await send_message_fallback(session_id, message)


async def send_message_fallback(session_id: str, message: str):
    """Fallback simple NLP processing if agent not available"""
    
    report = reports_db.get(session_id)
    
    response = {
        "message": "",
        "action": None,
        "details": {},
        "suggestions": [],
        "updatedMetrics": {}
    }
    
    message_lower = message.lower()
    
    # Simple fallback logic
    if "save" in message_lower and "%" in message:
        response["message"] = "Please run analysis first to use this feature."
        response["action"] = "error"
    elif "what if" in message_lower:
        response["message"] = "What-if simulations require an active session."
        response["action"] = "error"
    else:
        response["message"] = "I understand. Please run the analysis first."
        response["action"] = "general"
    
    return response
    
    message_lower = message.lower()
    
    # === COMMAND: Save X% of income ===
    if "save" in message_lower and ("%" in message or "percent" in message_lower):
        match = re.search(r'(\d+)\s*%', message)
        if match:
            target_savings = int(match.group(1))
            if report:
                current_income = report.totalIncome
                current_expenses = report.totalExpenses
                current_savings = current_income - current_expenses
                target_savings_amount = current_income * (target_savings / 100)
                adjustment_needed = target_savings_amount - current_savings
                
                if adjustment_needed > 0:
                    # Need to reduce expenses
                    reduction_needed = adjustment_needed
                    # Proportionally reduce non-essential categories
                    non_essential = ["Entertainment", "Shopping", "Food", "Transportation", "Fitness"]
                    new_budget = []
                    for rec in report.budgetRecommendations:
                        if rec.category in non_essential and reduction_needed > 0:
                            reduction = min(rec.suggestedAmount * 0.3, reduction_needed)  # Reduce up to 30%
                            new_amount = rec.suggestedAmount - reduction
                            reduction_needed -= reduction
                            new_budget.append({
                                "category": rec.category,
                                "previousAmount": rec.suggestedAmount,
                                "newAmount": max(0, new_amount),
                                "reduction": reduction
                            })
                    
                    new_savings_rate = (current_income - (current_expenses - (adjustment_needed - reduction_needed))) / current_income * 100
                    
                    response["message"] = f"Done. I've adjusted your budget to save {target_savings}%. Your projected savings is now {new_savings_rate:.1f}% (was {report.savingsRate:.1f}%)."
                    response["action"] = "adjust_savings"
                    response["details"] = {
                        "targetSavings": target_savings,
                        "newSavingsRate": new_savings_rate,
                        "budgetChanges": new_budget
                    }
                    response["updatedMetrics"] = {
                        "savingsRate": new_savings_rate
                    }
                else:
                    response["message"] = f"You're already saving {report.savingsRate:.1f}%, which exceeds your {target_savings}% target!"
                    response["action"] = "info"
            else:
                response["message"] = "Please run the analysis first before adjusting savings."
                response["action"] = "error"
    
    # === COMMAND: Ignore specific transaction ===
    elif "ignore" in message_lower:
        # Look for amount or description
        amount_match = re.search(r'\$?(\d+(?:\.\d+)?)', message)
        
        if report and amount_match:
            ignore_amount = float(amount_match.group(1))
            # Find matching transaction in categories
            for cat in report.categoryBreakdown:
                if abs(cat.amount - ignore_amount) < 10:
                    new_expenses = report.totalExpenses - cat.amount
                    new_savings = (report.totalIncome - new_expenses) / report.totalIncome * 100
                    
                    response["message"] = f"I've excluded the ${cat.amount:.2f} {cat.category} charge. Your expenses are now ${new_expenses:.2f} and savings rate is {new_savings:.1f}%."
                    response["action"] = "exclude_transaction"
                    response["details"] = {
                        "excludedCategory": cat.category,
                        "excludedAmount": cat.amount,
                        "newTotalExpenses": new_expenses,
                        "newSavingsRate": new_savings
                    }
                    response["updatedMetrics"] = {
                        "totalExpenses": new_expenses,
                        "savingsRate": new_savings
                    }
                    break
        else:
            response["message"] = "Which transaction would you like to ignore? Please specify the amount (e.g., 'Ignore the $500 charge')."
            response["action"] = "clarify"
    
    # === COMMAND: What-if scenario ===
    elif "what if" in message_lower or "simulate" in message_lower or "what happens" in message_lower:
        if not report:
            response["message"] = "Please run the analysis first."
            response["action"] = "error"
        else:
            # Parse what-if scenarios
            scenario_details = {}
            
            # "spend $X less on rent"
            less_match = re.search(r'\$(\d+)\s*less\s*on\s*(\w+)', message_lower)
            if less_match:
                amount = float(less_match.group(1))
                category = less_match.group(2).title()
                scenario_details["type"] = "reduce_category"
                scenario_details["category"] = category
                scenario_details["amount"] = amount
            
            # "reduce income by X%"
            income_match = re.search(r'reduce.*income.*(\d+)\s*%', message_lower)
            if income_match:
                amount = float(income_match.group(1))
                scenario_details["type"] = "reduce_income"
                scenario_details["percentage"] = amount
            
            # "increase rent by $X"
            increase_match = re.search(r'increase.*(\w+).*\$(\d+)', message_lower)
            if increase_match:
                category = increase_match.group(1).title()
                amount = float(increase_match.group(2))
                scenario_details["type"] = "increase_category"
                scenario_details["category"] = category
                scenario_details["amount"] = amount
            
            if scenario_details:
                # Calculate simulation
                sim_income = report.totalIncome
                sim_expenses = report.totalExpenses
                
                if scenario_details.get("type") == "reduce_category":
                    cat = scenario_details["category"]
                    amt = scenario_details["amount"]
                    sim_expenses = max(0, sim_expenses - amt)
                    scenario_details["newExpenses"] = sim_expenses
                    
                elif scenario_details.get("type") == "reduce_income":
                    pct = scenario_details["percentage"]
                    sim_income = sim_income * (1 - pct/100)
                    scenario_details["newIncome"] = sim_income
                    
                elif scenario_details.get("type") == "increase_category":
                    sim_expenses = sim_expenses + scenario_details["amount"]
                    scenario_details["newExpenses"] = sim_expenses
                
                sim_savings = (sim_income - sim_expenses) / sim_income * 100 if sim_income > 0 else 0
                
                response["message"] = f"Simulation: With these changes, your new totals would be:\n• Income: ${sim_income:,.0f}\n• Expenses: ${sim_expenses:,.0f}\n• Savings Rate: {sim_savings:.1f}%"
                response["action"] = "what_if"
                response["details"] = scenario_details
                response["updatedMetrics"] = {
                    "totalIncome": sim_income,
                    "totalExpenses": sim_expenses,
                    "savingsRate": sim_savings,
                    "isSimulation": True
                }
            else:
                response["message"] = "I can simulate scenarios like:\n• 'What if I spend $200 less on rent?'\n• 'What if my income drops 15%?'\n• 'What if I increase food budget by $100?'"
                response["action"] = "suggest"
    
    # === COMMAND: Adjust category budget ===
    elif "reduce" in message_lower or "lower" in message_lower or "cut" in message_lower:
        if report:
            # Find category mentioned
            categories = ["housing", "food", "transportation", "utilities", "entertainment", "shopping", "healthcare", "insurance", "fitness"]
            found_category = None
            for cat in categories:
                if cat in message_lower:
                    found_category = cat.title()
                    break
            
            # Find percentage
            pct_match = re.search(r'(\d+)\s*%', message)
            
            if found_category and pct_match:
                pct = int(pct_match.group(1))
                for rec in report.budgetRecommendations:
                    if rec.category == found_category:
                        old_amount = rec.suggestedAmount
                        new_amount = old_amount * (1 - pct/100)
                        
                        response["message"] = f"Done. I've reduced your {found_category} budget by {pct}% from ${old_amount:.2f} to ${new_amount:.2f}."
                        response["action"] = "adjust_budget"
                        response["details"] = {
                            "category": found_category,
                            "reduction": pct,
                            "previousAmount": old_amount,
                            "newAmount": new_amount
                        }
                        break
            elif found_category:
                response["message"] = f"How much would you like to reduce {found_category} by? (e.g., 'Reduce {found_category} by 20%')"
                response["action"] = "clarify"
            else:
                response["message"] = "Which category would you like to adjust? (Housing, Food, Transportation, Utilities, Entertainment, Shopping, Healthcare)"
                response["action"] = "clarify"
        else:
            response["message"] = "Please run the analysis first."
            response["action"] = "error"
    
    # === COMMAND: Increase category ===
    elif "increase" in message_lower:
        if report:
            categories = ["housing", "food", "transportation", "utilities", "entertainment", "shopping", "healthcare", "insurance", "fitness"]
            found_category = None
            for cat in categories:
                if cat in message_lower:
                    found_category = cat.title()
                    break
            
            import re
            amount_match = re.search(r'\$(\d+)', message)
            
            if found_category and amount_match:
                amount = float(amount_match.group(1))
                for rec in report.budgetRecommendations:
                    if rec.category == found_category:
                        old_amount = rec.suggestedAmount
                        new_amount = old_amount + amount
                        
                        response["message"] = f"Done. I've increased your {found_category} budget by ${amount:.2f} to ${new_amount:.2f}."
                        response["action"] = "adjust_budget"
                        response["details"] = {
                            "category": found_category,
                            "increase": amount,
                            "previousAmount": old_amount,
                            "newAmount": new_amount
                        }
                        break
            elif found_category:
                response["message"] = f"How much would you like to increase {found_category} by? (e.g., 'Increase {found_category} by $100')"
                response["action"] = "clarify"
            else:
                response["message"] = "Which category would you like to increase?"
                response["action"] = "clarify"
        else:
            response["message"] = "Please run the analysis first."
            response["action"] = "error"
    
    # === Default: Generate suggestions ===
    else:
        if report:
            suggestions = []
            
            # Analyze spending patterns
            for cat in report.categoryBreakdown:
                if cat.percent > 30:
                    suggestions.append(f"You're spending {cat.percent:.0f}% on {cat.category}. Try: 'Reduce {cat.category} to 25%'")
                elif cat.category == "Housing" and cat.percent > 25:
                    suggestions.append(f"Housing at {cat.percent:.0f}% is above the recommended 25%. Try: 'Reduce Housing by 10%'")
            
            if report.savingsRate < 10:
                suggestions.append(f"Current savings is {report.savingsRate:.1f}%. Try: 'Save 15% of income'")
            elif report.savingsRate < 20:
                suggestions.append(f"Great savings rate of {report.savingsRate:.1f}%! Try: 'Save 20% of income'")
            
            if report.riskScore > 0.5:
                suggestions.append(f"High risk score ({report.riskScore:.1f}). Review anomalies in the report.")
            
            if suggestions:
                response["message"] = "Here are some suggestions based on your data:\n" + "\n".join(f"• {s}" for s in suggestions)
                response["action"] = "suggestions"
                response["suggestions"] = suggestions
            else:
                response["message"] = "Your budget looks balanced! Would you like to try a simulation? (e.g., 'What if I spend $200 less on rent?')"
                response["action"] = "general"
        else:
            response["message"] = "Upload a CSV file and run the analysis first, then I can help you optimize your budget."
            response["action"] = "ready"
    
    return response


# What-If Simulation Endpoint
@app.post("/api/simulation/{session_id}")
async def run_simulation(session_id: str, simulation: dict):
    """Run a what-if simulation without saving"""
    
    report = reports_db.get(session_id)
    if not report:
        raise HTTPException(status_code=404, detail="No report found. Run analysis first.")
    
    sim_type = simulation.get("type")
    params = simulation.get("params", {})
    
    # Copy current values
    sim_income = report.totalIncome
    sim_expenses = report.totalExpenses
    
    if sim_type == "reduce_category":
        category = params.get("category")
        amount = params.get("amount", 0)
        sim_expenses = max(0, sim_expenses - amount)
        
    elif sim_type == "increase_category":
        category = params.get("category")
        amount = params.get("amount", 0)
        sim_expenses = sim_expenses + amount
        
    elif sim_type == "reduce_income":
        percentage = params.get("percentage", 0)
        sim_income = sim_income * (1 - percentage/100)
        
    elif sim_type == "increase_income":
        percentage = params.get("percentage", 0)
        sim_income = sim_income * (1 + percentage/100)
    
    sim_savings = (sim_income - sim_expenses) / sim_income * 100 if sim_income > 0 else 0
    
    return {
        "original": {
            "income": report.totalIncome,
            "expenses": report.totalExpenses,
            "savingsRate": report.savingsRate
        },
        "simulation": {
            "income": sim_income,
            "expenses": sim_expenses,
            "savingsRate": sim_savings
        },
        "changes": {
            "incomeDiff": sim_income - report.totalIncome,
            "expensesDiff": sim_expenses - report.totalExpenses,
            "savingsRateDiff": sim_savings - report.savingsRate
        }
    }


# Predictive Suggestions Endpoint
@app.get("/api/suggestions/{session_id}")
async def get_suggestions(session_id: str):
    """Get AI-powered suggestions based on current data"""
    
    report = reports_db.get(session_id)
    if not report:
        return {"suggestions": [], "message": "No data available"}
    
    suggestions = []
    
    # Category-based suggestions
    for cat in report.categoryBreakdown:
        if cat.percent > 30:
            suggestions.append({
                "type": "warning",
                "message": f"You're spending {cat.percent:.0f}% on {cat.category}",
                "suggestedAction": f"Reduce {cat.category} to 25%",
                "command": f"Reduce {cat.category} by 20%"
            })
    
    # Housing is typically recommended at 25-30%
    housing_cat = next((c for c in report.categoryBreakdown if c.category == "Housing"), None)
    if housing_cat and housing_cat.percent > 28:
        suggestions.append({
            "type": "warning",
            "message": f"Housing at {housing_cat.percent:.0f}% is above the recommended 25%",
            "suggestedAction": "Consider reducing rent or looking for alternatives",
            "command": "Reduce Housing by 15%"
        })
    
    # Savings suggestions
    if report.savingsRate < 10:
        suggestions.append({
            "type": "alert",
            "message": f"Current savings rate is only {report.savingsRate:.1f}%",
            "suggestedAction": "Aim for at least 20% savings",
            "command": "Save 20% of income"
        })
    elif report.savingsRate < 20:
        suggestions.append({
            "type": "info",
            "message": f"Good savings rate of {report.savingsRate:.1f}%",
            "suggestedAction": "Try to increase to 25%",
            "command": "Save 25% of income"
        })
    else:
        suggestions.append({
            "type": "success",
            "message": f"Excellent savings rate of {report.savingsRate:.1f}%!",
            "suggestedAction": "Consider investing or increasing emergency fund",
            "command": "What if I save 30%?"
        })
    
    # Risk-based suggestions
    if report.riskScore > 0.7:
        suggestions.append({
            "type": "alert",
            "message": f"High risk score: {report.riskScore:.1f}",
            "suggestedAction": "Review flagged transactions",
            "command": "Show anomalies"
        })
    
    # What-if suggestions
    suggestions.append({
        "type": "simulation",
        "message": "Explore scenarios",
        "suggestedAction": "Try what-if simulations",
        "command": "What if I spend $200 less on rent?"
    })
    
    return {
        "suggestions": suggestions,
        "summary": {
            "totalIncome": report.totalIncome,
            "totalExpenses": report.totalExpenses,
            "savingsRate": report.savingsRate,
            "riskScore": report.riskScore
        }
    }


if __name__ == "__main__":
    import uvicorn
    import sys
    
    port = 8000
    if len(sys.argv) > 2 and sys.argv[1] == '--port':
        port = int(sys.argv[2])
    
    uvicorn.run(app, host="0.0.0.0", port=port)
