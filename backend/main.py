"""
FastAPI Backend for Financial Agent
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import json
import asyncio
from enum import Enum

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
            id="sess-003", date="2024-02-22", status=SessionStatus.AWAITING_APPROVAL,
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
    system_status.activeSessions += 1
    return session


# File Upload & Validation
@app.post("/api/upload/validate")
async def validate_file(file: UploadFile = File(...)):
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
        
        for idx, (state, label) in enumerate(states):
            # Update workflow state
            for i, step in enumerate(workflow_state[session_id]):
                step.completed = i < idx
                step.running = i == idx
                step.error = False
            
            # Add log entry
            tokens = 0
            cost = 0.0
            if state in [AgentState.CATEGORIZE, AgentState.BUDGET]:
                tokens = 400
                cost = 0.0002
            
            log = AgentLog(
                id=f"log-{idx}",
                timestamp=datetime.utcnow().isoformat(),
                agent=state.value.lower(),
                action=f"Executing {label}",
                duration=350,
                tokens=tokens,
                cost=cost,
                details=f"{label} step completed successfully"
            )
            execution_logs[session_id].append(log)
            
            # Check for anomaly in CATEGORIZE
            if state == AgentState.CATEGORIZE:
                approval = ApprovalRequest(
                    id=f"approval-{uuid.uuid4().hex[:8]}",
                    type="ANOMALY_DETECTED",
                    description="Large anomaly detected: 1,200 transaction",
                    amount=-1200.0,
                    riskScore=0.85,
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
            
            await asyncio.sleep(0.8)
        
        # Mark complete
        for step in workflow_state[session_id]:
            step.completed = step.state != AgentState.WAITING_APPROVAL
            step.running = False
        
        # Update session status
        if session_id in sessions_db:
            sessions_db[session_id].status = SessionStatus.COMPLETE
            sessions_db[session_id].totalIncome = 11000
            sessions_db[session_id].totalExpenses = 5010
            sessions_db[session_id].savingsRate = 54.5
        
        system_status.activeSessions = max(0, system_status.activeSessions - 1)
    
    background_tasks.add_task(run_workflow)
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
                if state in [AgentState.BUDGET]:
                    tokens = 400
                    cost = 0.0002
                
                log = AgentLog(
                    id=f"log-resume-{idx}",
                    timestamp=datetime.utcnow().isoformat(),
                    agent=state.value.lower(),
                    action=f"Executing {label}",
                    duration=350,
                    tokens=tokens,
                    cost=cost,
                    details=f"{label} step completed successfully"
                )
                execution_logs[session_id].append(log)
                await asyncio.sleep(0.8)
            
            # Mark complete
            for step in workflow_state[session_id]:
                step.completed = True
                step.running = False
            
            if session_id in sessions_db:
                sessions_db[session_id].status = SessionStatus.COMPLETE
            
            system_status.activeSessions = max(0, system_status.activeSessions - 1)
        
        asyncio.create_task(resume_workflow())
        
    elif action == "reject":
        approval.status = "REJECTED"
        if session_id in sessions_db:
            sessions_db[session_id].status = SessionStatus.FAILED
        system_status.activeSessions = max(0, system_status.activeSessions - 1)
    
    return {"status": approval.status, "approval": approval}


# Reports
@app.get("/api/reports/{session_id}", response_model=ReportData)
async def get_report(session_id: str):
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


# Conversation
@app.post("/api/conversation/{session_id}")
async def send_message(session_id: str, message: str):
    """Process conversational refinement"""
    
    # Simple intent parsing
    response = {
        "message": "",
        "action": None,
        "details": {}
    }
    
    message_lower = message.lower()
    
    if "increase" in message_lower and "food" in message_lower:
        response["message"] = "I'll increase your food budget by 10%."
        response["action"] = "adjust_budget"
        response["details"] = {"category": "food", "adjustment": 0.1}
    elif "reduce" in message_lower and "entertainment" in message_lower:
        response["message"] = "I'll reduce your entertainment budget."
        response["action"] = "adjust_budget"
        response["details"] = {"category": "entertainment", "adjustment": -0.1}
    elif "what if" in message_lower and "income" in message_lower:
        response["message"] = "If your income drops by 15%, your savings rate would decrease from 54.5% to approximately 39.5%."
        response["action"] = "scenario_analysis"
    else:
        response["message"] = "I understand. Let me process that request."
        response["action"] = "general"
    
    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
