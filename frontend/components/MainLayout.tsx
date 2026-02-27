'use client';

import { useState, useEffect, useRef } from 'react';
import { useAppStore } from '@/store';
import { 
  createSession,
  validateFile,
  executeWorkflow,
  sendMessage
} from '@/lib/api';
import { 
  Upload, 
  FileText, 
  Settings, 
  History,
  Send,
  Loader2,
  Sparkles,
  ChevronRight,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Clock,
  TrendingUp,
  TrendingDown,
  DollarSign,
  PieChart,
  Target,
  MessageSquare,
  Bot,
  X,
  BarChart3,
  Activity
} from 'lucide-react';
import clsx from 'clsx';

const defaultWorkflowSteps = [
  { state: 'INIT' as const, label: 'Initialize', completed: false, running: false },
  { state: 'INGEST' as const, label: 'Ingest Data', completed: false, running: false },
  { state: 'CATEGORIZE' as const, label: 'Categorize', completed: false, running: false },
  { state: 'ANALYZE' as const, label: 'Analyze', completed: false, running: false },
  { state: 'BUDGET' as const, label: 'Budget', completed: false, running: false },
  { state: 'EVALUATE' as const, label: 'Evaluate', completed: false, running: false },
  { state: 'COMPLETE' as const, label: 'Complete', completed: false, running: false },
];

export function MainLayout() {
  const {
    currentSessionId,
    setCurrentSessionId,
    currentReport,
    setCurrentReport,
    pendingApproval,
    setPendingApproval,
    isExecuting,
    setIsExecuting,
    workflowSteps,
    setWorkflowSteps,
    agentLogs,
    setAgentLogs,
    clearAgentLogs,
    loadWorkflow,
    loadExecutionLogs,
    loadApproval,
    loadReport,
    approveRequest,
    rejectRequest,
    sessions,
    loadSessions
  } = useAppStore();

  const [activeTab, setActiveTab] = useState<'ingestion' | 'processing' | 'dashboard'>('ingestion');
  const [terminalLogs, setTerminalLogs] = useState<Array<{status: string; message: string; timestamp: Date}>>([]);
  const [chatMessages, setChatMessages] = useState<Array<{role: 'user' | 'assistant'; content: string; timestamp: Date}>>([]);
  const [chatInput, setChatInput] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [uploadedTransactions, setUploadedTransactions] = useState<any[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Poll for updates when executing
  useEffect(() => {
    if (isExecuting && currentSessionId) {
      const interval = setInterval(async () => {
        await loadWorkflow(currentSessionId);
        await loadExecutionLogs(currentSessionId);
        await loadApproval(currentSessionId);
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [isExecuting, currentSessionId]);

  // Check for completion
  useEffect(() => {
    const complete = workflowSteps.some(s => s.completed && s.state === 'COMPLETE');
    if (complete && isExecuting) {
      console.log('[Workflow] Complete detected, switching to dashboard');
      loadReport(currentSessionId!).then(() => {
        setActiveTab('dashboard');
        setIsExecuting(false);
      });
    }
  }, [workflowSteps, isExecuting, currentSessionId]);

  // Scroll chat to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  // Convert agent logs to terminal logs - show each step progressively
  useEffect(() => {
    const logs = agentLogs.map((log, idx) => {
      // Latest log is running, others are completed
      const isLatest = idx === agentLogs.length - 1;
      return {
        status: isLatest ? 'running' : 'ok',
        message: `${log.agent.toUpperCase()}: ${log.details || log.action}`,
        timestamp: new Date(log.timestamp)
      };
    });
    setTerminalLogs(logs);
  }, [agentLogs]);

  const handleFileSelect = async (file: File) => {
    setFileName(file.name);
    setIsUploading(true);
    try {
      const session = await createSession();
      setCurrentSessionId(session.id);
      
      const result = await validateFile(file, session.id);
      
      if (result.valid) {
        setUploadedTransactions(result.transactions || []);
        setActiveTab('processing');
        await runWorkflow(session.id);
      }
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setIsUploading(false);
    }
  };

  const runWorkflow = async (sessionId: string) => {
    setIsExecuting(true);
    setWorkflowSteps(defaultWorkflowSteps.map((s, i) => ({ ...s, running: i === 0 })));
    setTerminalLogs([]); // Clear previous terminal display
    clearAgentLogs(); // Clear store logs
    setChatMessages([{
      role: 'assistant',
      content: 'Starting analysis...',
      timestamp: new Date()
    }]);
    
    console.log('[Workflow] Starting for session:', sessionId);
    try {
      const result = await executeWorkflow(sessionId);
      console.log('[Workflow] Started:', result);
    } catch (error) {
      console.error('[Workflow] Error starting:', error);
    }
  };

  const handleChatSubmit = async () => {
    if (!chatInput.trim() || !currentSessionId || isChatLoading) return;
    
    const userMessage = chatInput;
    setChatInput('');
    setChatMessages(prev => [...prev, { role: 'user', content: userMessage, timestamp: new Date() }]);
    setIsChatLoading(true);
    
    try {
      console.log('[Chat] Sending message:', userMessage, 'to session:', currentSessionId);
      console.log('[Chat] Reports DB check - will verify on backend');
      const response = await sendMessage(currentSessionId, userMessage);
      console.log('[Chat] Response:', response);
      
      let messageContent = 'No response';
      if (response) {
        if (typeof response.message === 'string') {
          messageContent = response.message;
        } else if (response.message) {
          messageContent = JSON.stringify(response.message);
        } else if (response.error) {
          messageContent = 'Error: ' + response.error;
        }
      }
      
      setChatMessages(prev => [...prev, { 
        role: 'assistant', 
        content: messageContent, 
        timestamp: new Date() 
      }]);
      
      // Reload report if metrics changed
      if (response?.updatedMetrics && Object.keys(response.updatedMetrics).length > 0) {
        console.log('[Chat] Metrics changed, reloading report...');
        await loadReport(currentSessionId!);
      }
    } catch (error) {
      console.error('[Chat] Error:', error);
      const errorMsg = error instanceof Error ? error.message : String(error);
      setChatMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Error: ' + errorMsg, 
        timestamp: new Date() 
      }]);
    } finally {
      setIsChatLoading(false);
    }
  };

  const handleSuggestionClick = async (command: string) => {
    setChatInput(command);
    await handleChatSubmit();
  };

  return (
    <div className="app-layout">
      {/* Left Sidebar */}
      <div className="sidebar flex flex-col">
        <div className="p-4 border-b border-fintech-border">
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-emerald-400" />
            FinAgent
          </h1>
        </div>
        
        <nav className="flex-1 p-4 space-y-2">
          <button
            onClick={() => setActiveTab('ingestion')}
            className={clsx(
              'w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all',
              activeTab === 'ingestion' 
                ? 'bg-emerald-600/20 text-emerald-400 border border-emerald-500/30' 
                : 'text-gray-400 hover:bg-fintech-card hover:text-white'
            )}
          >
            <Upload className="w-5 h-5" />
            Upload
          </button>
          
          <button
            onClick={() => setActiveTab('processing')}
            disabled={!currentSessionId}
            className={clsx(
              'w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all',
              activeTab === 'processing' 
                ? 'bg-emerald-600/20 text-emerald-400 border border-emerald-500/30' 
                : 'text-gray-400 hover:bg-fintech-card hover:text-white',
              !currentSessionId && 'opacity-50 cursor-not-allowed'
            )}
          >
            <Activity className="w-5 h-5" />
            Processing
          </button>
          
          <button
            onClick={() => setActiveTab('dashboard')}
            disabled={!currentReport}
            className={clsx(
              'w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all',
              activeTab === 'dashboard' 
                ? 'bg-emerald-600/20 text-emerald-400 border border-emerald-500/30' 
                : 'text-gray-400 hover:bg-fintech-card hover:text-white',
              !currentReport && 'opacity-50 cursor-not-allowed'
            )}
          >
            <BarChart3 className="w-5 h-5" />
            Dashboard
          </button>
        </nav>
        
        {/* Session History */}
        <div className="p-4 border-t border-fintech-border">
          <h3 className="text-xs text-gray-500 uppercase tracking-wide mb-3">Recent Sessions</h3>
          <div className="space-y-2">
            {sessions.slice(0, 3).map(session => (
              <button
                key={session.id}
                onClick={() => setCurrentSessionId(session.id)}
                className="w-full text-left px-3 py-2 rounded-lg hover:bg-fintech-card transition-colors"
              >
                <p className="text-sm text-white truncate">{session.date}</p>
                <p className="text-xs text-gray-500">{session.status}</p>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Stage */}
      <div className="main-stage p-6">
        {/* Tab 1: Ingestion */}
        {activeTab === 'ingestion' && (
          <div className="max-w-4xl mx-auto">
            <h2 className="text-2xl font-semibold text-white mb-2">Upload Your Data</h2>
            <p className="text-gray-500 mb-8">Drop a CSV file to begin financial analysis</p>
            
            <div 
              className={clsx(
                'drop-zone rounded-2xl p-16 text-center cursor-pointer border-2 border-dashed',
                isDragging && 'border-emerald-500 bg-emerald-500/5'
              )}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsDragging(false);
                const file = e.dataTransfer.files[0];
                if (file?.name.endsWith('.csv')) handleFileSelect(file);
              }}
              onClick={() => document.getElementById('file-input')?.click()}
            >
              <input 
                type="file" 
                id="file-input"
                accept=".csv"
                className="hidden"
                onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
              />
              
              {fileName ? (
                <div className="flex flex-col items-center gap-3">
                  <div className="w-16 h-16 rounded-full bg-emerald-500/20 flex items-center justify-center">
                    <FileText className="w-8 h-8 text-emerald-500" />
                  </div>
                  <p className="text-white font-medium">{fileName}</p>
                  <p className="text-sm text-gray-500">Click to replace</p>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-3">
                  <div className="w-16 h-16 rounded-full bg-fintech-border flex items-center justify-center">
                    <Upload className="w-8 h-8 text-gray-400" />
                  </div>
                  <p className="text-white font-medium">Drop CSV file here</p>
                  <p className="text-sm text-gray-500">or click to browse</p>
                </div>
              )}
            </div>
            
            {/* Schema */}
            <div className="mt-8 glass-card p-6">
              <h3 className="text-sm font-medium text-gray-400 mb-4">Expected Format</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-500">
                      <th className="pb-2 font-medium">Column</th>
                      <th className="pb-2 font-medium">Type</th>
                      <th className="pb-2 font-medium">Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      { name: 'date', type: 'string', desc: 'YYYY-MM-DD' },
                      { name: 'description', type: 'string', desc: 'Transaction description' },
                      { name: 'amount', type: 'number', desc: 'Positive = income, Negative = expense' },
                      { name: 'category', type: 'string', desc: 'Optional category' },
                    ].map(col => (
                      <tr key={col.name} className="border-t border-fintech-border">
                        <td className="py-2 mono-number text-emerald-400">{col.name}</td>
                        <td className="py-2 text-gray-400">{col.type}</td>
                        <td className="py-2 text-gray-500">{col.desc}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Processing */}
        {activeTab === 'processing' && (
          <div className="max-w-4xl mx-auto">
            <h2 className="text-2xl font-semibold text-white mb-2">Analysis Engine</h2>
            <p className="text-gray-500 mb-8">Live processing feed</p>
            
            {/* Workflow Steps */}
            <div className="grid grid-cols-7 gap-2 mb-8">
              {workflowSteps.map((step, idx) => (
                <div
                  key={step.state}
                  className={clsx(
                    'flex flex-col items-center p-3 rounded-xl border',
                    step.running ? 'bg-emerald-500/10 border-emerald-500' :
                    step.completed ? 'bg-emerald-500/10 border-emerald-500/50' :
                    'bg-fintech-card border-fintech-border'
                  )}
                >
                  {step.completed ? (
                    <CheckCircle className="w-5 h-5 text-emerald-500 mb-1" />
                  ) : step.running ? (
                    <Loader2 className="w-5 h-5 text-emerald-500 animate-spin mb-1" />
                  ) : (
                    <Clock className="w-5 h-5 text-gray-500 mb-1" />
                  )}
                  <span className="text-xs text-center">{step.label}</span>
                </div>
              ))}
            </div>
            
            {/* Terminal Feed */}
            <div className="glass-card p-4 font-mono text-sm h-[400px] overflow-y-auto">
              {terminalLogs.length === 0 ? (
                <p className="text-gray-500">Waiting for processing...</p>
              ) : (
                terminalLogs.map((log, idx) => (
                  <div key={idx} className="py-1">
                    <span className={clsx(
                      log.status === 'ok' ? 'text-emerald-400' :
                      log.status === 'running' ? 'text-amber-400' :
                      log.status === 'error' ? 'text-rose-400' :
                      'text-gray-400'
                    )}>
                      [{log.status.toUpperCase()}]
                    </span>{' '}
                    <span className="text-gray-300">{log.message}</span>
                  </div>
                ))
              )}
            </div>
            
            {/* First Look Grid */}
            {uploadedTransactions.length > 0 && (
              <div className="mt-8">
                <h3 className="text-sm font-medium text-gray-400 mb-4">First Look</h3>
                <div className="glass-card overflow-hidden">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Description</th>
                        <th className="text-right">Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      {uploadedTransactions.slice(0, 10).map((txn, idx) => (
                        <tr key={idx}>
                          <td className="mono-number">{txn.date}</td>
                          <td>{txn.description}</td>
                          <td className={clsx(
                            'mono-number text-right',
                            txn.amount >= 0 ? 'text-emerald-400' : 'text-rose-400'
                          )}>
                            {txn.amount >= 0 ? '+' : ''}{txn.amount.toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Dashboard */}
        {activeTab === 'dashboard' && currentReport && (
          <div className="max-w-5xl mx-auto">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-2xl font-semibold text-white">Financial Overview</h2>
                <p className="text-gray-500">Analysis complete</p>
              </div>
              <button className="btn-primary flex items-center gap-2">
                <FileText className="w-4 h-4" />
                Export PDF
              </button>
            </div>
            
            {/* Metric Ribbons */}
            <div className="grid grid-cols-4 gap-4 mb-8">
              <div className="metric-ribbon">
                <span className="metric-label">Total Income</span>
                <span className="metric-value text-emerald-400 mono-number">
                  ${currentReport.totalIncome.toLocaleString()}
                </span>
              </div>
              <div className="metric-ribbon">
                <span className="metric-label">Total Expenses</span>
                <span className="metric-value text-rose-400 mono-number">
                  ${currentReport.totalExpenses.toLocaleString()}
                </span>
              </div>
              <div className="metric-ribbon">
                <span className="metric-label">Savings Rate</span>
                <span className={clsx(
                  'metric-value mono-number',
                  currentReport.savingsRate >= 20 ? 'text-emerald-400' :
                  currentReport.savingsRate >= 10 ? 'text-amber-400' : 'text-rose-400'
                )}>
                  {currentReport.savingsRate.toFixed(1)}%
                </span>
              </div>
              <div className="metric-ribbon">
                <span className="metric-label">Risk Score</span>
                <span className={clsx(
                  'metric-value mono-number',
                  currentReport.riskScore <= 0.3 ? 'text-emerald-400' :
                  currentReport.riskScore <= 0.6 ? 'text-amber-400' : 'text-rose-400'
                )}>
                  {currentReport.riskScore.toFixed(1)}
                </span>
              </div>
            </div>
            
            {/* Charts Row */}
            <div className="grid grid-cols-2 gap-6 mb-8">
              {/* Donut Chart */}
              <div className="glass-card p-6">
                <h3 className="text-sm font-medium text-gray-400 mb-4">Spending by Category</h3>
                <div className="flex items-center justify-center">
                  <div className="relative">
                    <PieChart className="w-32 h-32 text-gray-600" />
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className="text-lg font-bold text-white mono-number">
                        ${currentReport.totalExpenses.toLocaleString()}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="mt-4 grid grid-cols-2 gap-2">
                  {currentReport.categoryBreakdown.slice(0, 6).map((cat, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full" style={{
                        backgroundColor: ['#10B981', '#F43F5E', '#F59E0B', '#3B82F6', '#8B5CF6', '#EC4899'][idx % 6]
                      }} />
                      <span className="text-sm text-gray-300">{cat.category}</span>
                      <span className="text-sm mono-number text-gray-500 ml-auto">{cat.percent}%</span>
                    </div>
                  ))}
                </div>
              </div>
              
              {/* Budget Recommendations */}
              <div className="glass-card p-6">
                <h3 className="text-sm font-medium text-gray-400 mb-4">Budget Recommendations</h3>
                <div className="space-y-4">
                  {currentReport.budgetRecommendations.slice(0, 4).map((rec, idx) => (
                    <div key={idx} className="p-3 bg-fintech-darker rounded-lg">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-white font-medium">{rec.category}</span>
                        <span className={clsx(
                          'text-sm mono-number',
                          rec.impact.startsWith('+') ? 'text-emerald-400' : 'text-rose-400'
                        )}>
                          {rec.impact}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        <span className="mono-number">${rec.currentAmount.toLocaleString()}</span>
                        <ChevronRight className="w-3 h-3" />
                        <span className="mono-number">${rec.suggestedAmount.toLocaleString()}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            
            {/* Anomalies */}
            {currentReport.anomalies.length > 0 && (
              <div className="glass-card p-6">
                <h3 className="text-sm font-medium text-gray-400 mb-4">Detected Anomalies</h3>
                <div className="space-y-2">
                  {currentReport.anomalies.map((anomaly, idx) => (
                    <div key={idx} className="flex items-center gap-3 p-3 bg-fintech-darker rounded-lg">
                      <AlertTriangle className="w-5 h-5 text-amber-400" />
                      <div className="flex-1">
                        <p className="text-white text-sm">{anomaly.description}</p>
                        <p className="text-xs text-gray-500">{anomaly.reason}</p>
                      </div>
                      <span className="mono-number text-rose-400">${Math.abs(anomaly.amount).toLocaleString()}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Right Agent Panel */}
      <div className="agent-panel">
        <div className="p-4 border-b border-fintech-border">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-emerald-400" />
            Financial Agent
          </h2>
          {currentSessionId && (
            <p className="text-xs text-gray-500 mt-1">Session: {currentSessionId}</p>
          )}
        </div>
        
        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4" style={{ maxHeight: '60vh' }}>
          {chatMessages.length === 0 && (
            <div className="text-center py-8">
              <Bot className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-500 text-sm">
                Hi! Upload your financial data and I'll help you analyze and optimize your budget.
              </p>
            </div>
          )}
          
          {chatMessages.map((msg, idx) => (
            <div key={idx} className={clsx(
              'chat-message',
              msg.role === 'user' ? 'chat-message-user' : 'chat-message-agent'
            )}>
              <p className="text-sm text-white whitespace-pre-wrap">{msg.content}</p>
            </div>
          ))}
          
          {isChatLoading && (
            <div className="chat-message chat-message-agent">
              <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
            </div>
          )}
          
          <div ref={chatEndRef} />
        </div>
        
        {/* Suggestions */}
        {currentReport && chatMessages.length > 0 && (
          <div className="px-4 pb-2">
            <p className="text-xs text-gray-500 mb-2">Try these:</p>
            <div className="flex flex-wrap gap-2">
              {[
                { cmd: "Reduce Housing by 10%", label: "Cut Housing 10%" },
                { cmd: "Save 20% of income", label: "Save 20%" },
                { cmd: "What if I spend $200 less on rent?", label: "Simulate" },
              ].map((sug, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSuggestionClick(sug.cmd)}
                  className="text-xs px-2 py-1 bg-fintech-card border border-fintech-border rounded-full text-gray-400 hover:text-white hover:border-emerald-500/50 transition-all"
                >
                  {sug.label}
                </button>
              ))}
            </div>
          </div>
        )}
        
        {/* Chat Input */}
        <div className="p-4 border-t border-fintech-border">
          <div className="flex gap-2">
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleChatSubmit()}
              placeholder="Ask anything..."
              className="input-field flex-1"
              disabled={!currentSessionId}
            />
            <button
              onClick={handleChatSubmit}
              disabled={!chatInput.trim() || !currentSessionId || isChatLoading}
              className="btn-primary px-4"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Approval Modal */}
      {pendingApproval && (
        <div className="modal-overlay">
          <div className="focus-card animate-scale-in">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-amber-500/20 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white">Approval Required</h3>
                <p className="text-sm text-gray-500">High-risk anomaly detected</p>
              </div>
            </div>
            
            <div className="bg-fintech-darker rounded-lg p-4 mb-4">
              <p className="text-amber-400 font-medium">{pendingApproval.description}</p>
              {pendingApproval.amount && (
                <p className="text-white mono-number mt-2">
                  ${Math.abs(pendingApproval.amount).toLocaleString()}
                </p>
              )}
            </div>
            
            <div className="flex gap-3">
              <button
                onClick={() => currentSessionId && rejectRequest(currentSessionId)}
                className="flex-1 btn-secondary"
              >
                Reject
              </button>
              <button
                onClick={() => currentSessionId && approveRequest(currentSessionId)}
                className="flex-1 btn-primary"
              >
                Approve
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
