import { create } from 'zustand';
import { 
  AgentState, 
  Session, 
  ReportData, 
  WorkflowStep, 
  AgentLog, 
  ApprovalRequest,
  ConversationMessage,
  SystemStatus,
  Settings,
  Transaction
} from '@/lib/types';
import * as api from '@/lib/api';

interface AppState {
  // Navigation
  currentPage: 'dashboard' | 'upload' | 'execution' | 'report' | 'history' | 'settings';
  setCurrentPage: (page: AppState['currentPage']) => void;
  
  // Session
  sessions: Session[];
  currentSessionId: string | null;
  setCurrentSessionId: (id: string | null) => void;
  loadSessions: () => Promise<void>;
  
  // Workflow
  workflowSteps: WorkflowStep[];
  setWorkflowSteps: (steps: WorkflowStep[]) => void;
  updateWorkflowStep: (state: AgentState, updates: Partial<WorkflowStep>) => void;
  currentAgentState: AgentState;
  setCurrentAgentState: (state: AgentState) => void;
  loadWorkflow: (sessionId: string) => Promise<void>;
  
  // Execution
  agentLogs: AgentLog[];
  addAgentLog: (log: AgentLog) => void;
  setAgentLogs: (logs: AgentLog[]) => void;
  clearAgentLogs: () => void;
  loadExecutionLogs: (sessionId: string) => Promise<void>;
  isExecuting: boolean;
  setIsExecuting: (executing: boolean) => void;
  totalTokens: number;
  totalCost: number;
  
  // Report
  currentReport: ReportData | null;
  reportVersions: ReportData[];
  setCurrentReport: (report: ReportData | null) => void;
  loadReport: (sessionId: string) => Promise<void>;
  addReportVersion: (report: ReportData) => void;
  
  // Approval
  pendingApproval: ApprovalRequest | null;
  setPendingApproval: (approval: ApprovalRequest | null) => void;
  loadApproval: (sessionId: string) => Promise<void>;
  
  // Conversation
  conversationMessages: ConversationMessage[];
  addConversationMessage: (message: ConversationMessage) => void;
  clearConversationMessages: () => void;
  isConversationOpen: boolean;
  setIsConversationOpen: (open: boolean) => void;
  
  // System Status
  systemStatus: SystemStatus;
  setSystemStatus: (status: SystemStatus) => void;
  loadSystemStatus: () => Promise<void>;
  
  // Settings
  settings: Settings;
  setSettings: (settings: Settings) => void;
  loadSettings: () => Promise<void>;
  
  // Upload
  uploadedTransactions: Transaction[];
  setUploadedTransactions: (transactions: Transaction[]) => void;
  uploadValidation: { valid: boolean; errors: string[]; totalCount?: number } | null;
  setUploadValidation: (validation: { valid: boolean; errors: string[]; totalCount?: number } | null) => void;
  validateFile: (file: File) => Promise<void>;
  
  // Actions
  startExecution: (sessionId: string) => Promise<void>;
  pollWorkflow: (sessionId: string) => Promise<void>;
  approveRequest: (sessionId: string) => Promise<void>;
  rejectRequest: (sessionId: string) => Promise<void>;
}

const defaultWorkflowSteps: WorkflowStep[] = [
  { state: 'INIT', label: 'Initialize', completed: false, running: false },
  { state: 'INGEST', label: 'Ingest Data', completed: false, running: false },
  { state: 'CATEGORIZE', label: 'Categorize', completed: false, running: false },
  { state: 'ANALYZE', label: 'Analyze', completed: false, running: false },
  { state: 'BUDGET', label: 'Budget', completed: false, running: false },
  { state: 'EVALUATE', label: 'Evaluate', completed: false, running: false },
  { state: 'COMPLETE', label: 'Complete', completed: false, running: false },
];

export const useAppStore = create<AppState>((set, get) => ({
  // Navigation
  currentPage: 'dashboard',
  setCurrentPage: (page) => set({ currentPage: page }),
  
  // Session
  sessions: [],
  currentSessionId: null,
  setCurrentSessionId: (id) => set({ currentSessionId: id }),
  loadSessions: async () => {
    try {
      const sessions = await api.getSessions();
      set({ sessions });
    } catch (e) {
      console.error('Failed to load sessions:', e);
    }
  },
  
  // Workflow
  workflowSteps: [...defaultWorkflowSteps],
  setWorkflowSteps: (steps) => set({ workflowSteps: steps }),
  updateWorkflowStep: (state, updates) => set((s) => ({
    workflowSteps: s.workflowSteps.map((step) =>
      step.state === state ? { ...step, ...updates } : step
    ),
  })),
  currentAgentState: 'INIT',
  setCurrentAgentState: (state) => set({ currentAgentState: state }),
  loadWorkflow: async (sessionId) => {
    try {
      const workflow = await api.getWorkflow(sessionId);
      set({ workflowSteps: workflow });
    } catch (e) {
      console.error('Failed to load workflow:', e);
    }
  },
  
  // Execution
  agentLogs: [],
  addAgentLog: (log) => set((s) => ({ agentLogs: [...s.agentLogs, log] })),
  setAgentLogs: (logs) => set({ agentLogs: logs }),
  clearAgentLogs: () => set({ agentLogs: [], totalTokens: 0, totalCost: 0 }),
  loadExecutionLogs: async (sessionId) => {
    try {
      const logs = await api.getExecutionLogs(sessionId);
      const totalTokens = logs.reduce((sum: number, log: AgentLog) => sum + (log.tokens || 0), 0);
      const totalCost = logs.reduce((sum: number, log: AgentLog) => sum + (log.cost || 0), 0);
      set({ agentLogs: logs, totalTokens, totalCost });
    } catch (e) {
      console.error('Failed to load logs:', e);
    }
  },
  isExecuting: false,
  setIsExecuting: (executing) => set({ isExecuting: executing }),
  totalTokens: 0,
  totalCost: 0,
  
  // Report
  currentReport: null,
  reportVersions: [],
  setCurrentReport: (report) => set({ currentReport: report }),
  addReportVersion: (report) => set((s) => ({ 
    reportVersions: [...s.reportVersions, report] 
  })),
  loadReport: async (sessionId) => {
    try {
      const report = await api.getReport(sessionId);
      set({ currentReport: report });
    } catch (e) {
      console.error('Failed to load report:', e);
    }
  },
  
  // Approval
  pendingApproval: null,
  setPendingApproval: (approval) => set({ pendingApproval: approval }),
  loadApproval: async (sessionId) => {
    try {
      const approval = await api.getApproval(sessionId);
      set({ pendingApproval: approval });
    } catch (e) {
      set({ pendingApproval: null });
    }
  },
  
  // Conversation
  conversationMessages: [],
  addConversationMessage: (message) => set((s) => ({ 
    conversationMessages: [...s.conversationMessages, message] 
  })),
  clearConversationMessages: () => set({ conversationMessages: [] }),
  isConversationOpen: false,
  setIsConversationOpen: (open) => set({ isConversationOpen: open }),
  
  // System Status
  systemStatus: {
    agentHealth: 'healthy',
    llmAvailable: true,
    tokensUsedToday: 45000,
    tokensLimit: 100000,
    activeSessions: 3,
  },
  setSystemStatus: (status) => set({ systemStatus: status }),
  loadSystemStatus: async () => {
    try {
      const status = await api.getSystemStatus();
      set({ systemStatus: status });
    } catch (e) {
      console.error('Failed to load system status:', e);
    }
  },
  
  // Settings
  settings: {
    approvalThreshold: 0.7,
    anomalySensitivity: 'medium',
    llmModel: 'llama-3.1-70b-versatile',
    tokenLimitDaily: 100000,
    dataRetentionDays: 90,
  },
  setSettings: (settings) => set({ settings }),
  loadSettings: async () => {
    try {
      const settings = await api.getSettings();
      set({ settings });
    } catch (e) {
      console.error('Failed to load settings:', e);
    }
  },
  
  // Upload
  uploadedTransactions: [],
  setUploadedTransactions: (transactions) => set({ uploadedTransactions: transactions }),
  uploadValidation: null,
  setUploadValidation: (validation) => set({ uploadValidation: validation }),
  validateFile: async (file) => {
    try {
      const result = await api.validateFile(file);
      set({ 
        uploadValidation: { valid: result.valid, errors: result.errors || [], totalCount: result.totalCount },
        uploadedTransactions: result.transactions || []
      });
    } catch (e) {
      set({ 
        uploadValidation: { valid: false, errors: ['Validation failed'] }
      });
    }
  },
  
  // Actions
  startExecution: async (sessionId) => {
    const { loadWorkflow, loadExecutionLogs, loadApproval, loadReport, setIsExecuting, setCurrentPage } = get();
    setIsExecuting(true);
    setCurrentPage('execution');
    
    try {
      await api.executeWorkflow(sessionId);
      
      // Start polling for updates
      const pollInterval = setInterval(async () => {
        await loadWorkflow(sessionId);
        await loadExecutionLogs(sessionId);
        await loadApproval(sessionId);
        
        const { workflowSteps, pendingApproval, isExecuting } = get();
        const running = workflowSteps.some(s => s.running);
        const complete = workflowSteps.some(s => s.completed && s.state === 'COMPLETE');
        
        if (complete) {
          await loadReport(sessionId);
        }
        
        if (!running && !pendingApproval) {
          clearInterval(pollInterval);
          setIsExecuting(false);
          if (complete) {
            await loadReport(sessionId);
          }
        }
      }, 1000);
      
    } catch (e) {
      console.error('Execution failed:', e);
      setIsExecuting(false);
    }
  },
  
  pollWorkflow: async (sessionId) => {
    const { loadWorkflow, loadExecutionLogs, loadApproval, setIsExecuting } = get();
    await loadWorkflow(sessionId);
    await loadExecutionLogs(sessionId);
    await loadApproval(sessionId);
    
    const { workflowSteps, pendingApproval } = get();
    const running = workflowSteps.some(s => s.running);
    
    if (!running && !pendingApproval) {
      setIsExecuting(false);
    }
  },
  
  approveRequest: async (sessionId) => {
    try {
      await api.respondToApproval(sessionId, 'approve');
      set({ pendingApproval: null });
    } catch (e) {
      console.error('Failed to approve:', e);
    }
  },
  
  rejectRequest: async (sessionId) => {
    try {
      await api.respondToApproval(sessionId, 'reject');
      set({ pendingApproval: null });
    } catch (e) {
      console.error('Failed to reject:', e);
    }
  },
}));
