// Types for the Financial Agent System

export type AgentState = 
  | 'INIT' 
  | 'INGEST' 
  | 'CATEGORIZE' 
  | 'ANALYZE' 
  | 'BUDGET' 
  | 'EVALUATE' 
  | 'WAITING_APPROVAL' 
  | 'COMPLETE' 
  | 'FAILED';

export type SessionStatus = 'Complete' | 'Awaiting Approval' | 'Failed' | 'Running';

export interface Transaction {
  id: string;
  date: string;
  description: string;
  amount: number;
  category?: string;
  isAnomaly?: boolean;
  riskScore?: number;
}

export interface Session {
  id: string;
  date: string;
  status: SessionStatus;
  anomaliesCount: number;
  budgetChangePercent: number;
  version: number;
  riskScore: number;
  totalIncome: number;
  totalExpenses: number;
  savingsRate: number;
}

export interface WorkflowStep {
  state: AgentState;
  label: string;
  completed: boolean;
  running: boolean;
  error?: boolean;
}

export interface AgentLog {
  id: string;
  timestamp: string;
  agent: string;
  action: string;
  duration: number;
  tokens?: number;
  cost?: number;
  details?: string;
}

export interface Anomaly {
  id: string;
  transactionId: string;
  description: string;
  amount: number;
  reason: string;
  riskScore: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
}

export interface CategoryBreakdown {
  category: string;
  amount: number;
  percent: number;
  previousMonth?: number;
  change?: number;
}

export interface BudgetRecommendation {
  category: string;
  currentAmount: number;
  suggestedAmount: number;
  rationale: string;
  impact: string;
}

export interface ReportData {
  sessionId: string;
  version: number;
  totalIncome: number;
  totalExpenses: number;
  savingsRate: number;
  riskScore: number;
  categoryBreakdown: CategoryBreakdown[];
  anomalies: Anomaly[];
  budgetRecommendations: BudgetRecommendation[];
  executionTrace: AgentLog[];
  createdAt: string;
}

export interface ApprovalRequest {
  id: string;
  type: 'HIGH_VALUE_TRANSACTION' | 'ANOMALY_DETECTED' | 'BUDGET_CHANGE';
  description: string;
  amount?: number;
  riskScore?: number;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  requestedAt: string;
  resolvedAt?: string;
  resolvedBy?: string;
}

export interface ConversationMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  intent?: string;
  action?: string;
}

export interface SystemStatus {
  agentHealth: 'healthy' | 'degraded' | 'unhealthy';
  llmAvailable: boolean;
  tokensUsedToday: number;
  tokensLimit: number;
  activeSessions: number;
}

export interface Settings {
  approvalThreshold: number;
  anomalySensitivity: 'low' | 'medium' | 'high';
  llmModel: string;
  tokenLimitDaily: number;
  dataRetentionDays: number;
}

// Conversation / NLP Types
export interface ConversationResponse {
  message: string;
  action: string;
  details: Record<string, any>;
  suggestions: string[];
  updatedMetrics?: {
    totalIncome?: number;
    totalExpenses?: number;
    savingsRate?: number;
  };
}

export interface Suggestion {
  type: 'warning' | 'alert' | 'info' | 'success' | 'simulation';
  message: string;
  suggestedAction: string;
  command: string;
}

export interface SimulationResult {
  original: {
    income: number;
    expenses: number;
    savingsRate: number;
  };
  simulation: {
    income: number;
    expenses: number;
    savingsRate: number;
  };
  changes: {
    incomeDiff: number;
    expensesDiff: number;
    savingsRateDiff: number;
  };
}

// UI Types
export type TabId = 'ingestion' | 'processing' | 'dashboard';

export interface TerminalLog {
  id: string;
  status: 'ok' | 'running' | 'error' | 'warning';
  message: string;
  timestamp: Date;
}
