'use client';

import { useAppStore } from '@/store';
import { 
  CheckCircle, 
  Circle, 
  Loader2, 
  XCircle,
  Bot,
  Activity,
  Coins,
  ArrowRight,
  FileText
} from 'lucide-react';
import clsx from 'clsx';

export function ExecutionView() {
  const { 
    workflowSteps, 
    agentLogs, 
    isExecuting, 
    totalTokens, 
    totalCost,
    setCurrentPage,
    setCurrentReport,
    pendingApproval,
    setPendingApproval
  } = useAppStore();

  const getStepIcon = (step: typeof workflowSteps[0]) => {
    if (step.completed) return <CheckCircle className="w-5 h-5 text-emerald-500" />;
    if (step.running) return <Loader2 className="w-5 h-5 text-emerald-500 animate-spin" />;
    if (step.error) return <XCircle className="w-5 h-5 text-red-500" />;
    return <Circle className="w-5 h-5 text-gray-600" />;
  };

  const totalDuration = agentLogs.reduce((sum, log) => sum + log.duration, 0);
  const totalTokensUsed = agentLogs.reduce((sum, log) => sum + (log.tokens || 0), 0);
  const totalCostUsed = agentLogs.reduce((sum, log) => sum + (log.cost || 0), 0);

  // Calculate cumulative tokens
  let cumulativeTokens = 0;
  const logsWithCumulative = agentLogs.map(log => {
    cumulativeTokens += log.tokens || 0;
    return { ...log, cumulativeTokens };
  });

  // Handle completion
  const isComplete = workflowSteps.some(s => s.completed && s.state === 'COMPLETE');

  const viewReport = () => {
    setCurrentReport({
      sessionId: 'sess-new',
      version: 1,
      totalIncome: 11000,
      totalExpenses: 5010,
      savingsRate: 54.5,
      riskScore: 0.3,
      categoryBreakdown: [
        { category: 'Housing', amount: 3000, percent: 27.3 },
        { category: 'Food', amount: 775, percent: 7.0 },
        { category: 'Transportation', amount: 235, percent: 2.1 },
        { category: 'Utilities', amount: 200, percent: 1.8 },
        { category: 'Entertainment', amount: 55, percent: 0.5 },
        { category: 'Shopping', amount: 200, percent: 1.8 },
        { category: 'Other', amount: 545, percent: 5.0 },
      ],
      anomalies: [
        { id: '1', transactionId: 'txn_002', description: 'Apartment Rent', amount: -1500, reason: 'IQR outlier: amount 1500.00 exceeds upper bound 432.50', riskScore: 1.0, severity: 'critical' },
        { id: '2', transactionId: 'txn_005', description: 'Cash Advance', amount: -500, reason: 'IQR outlier: amount 500.00 exceeds upper bound 432.50', riskScore: 0.16, severity: 'low' },
      ],
      budgetRecommendations: [
        { category: 'Housing', currentAmount: 3000, suggestedAmount: 2750, rationale: 'Current spending 3000.00 exceeds recommended 2750.00 (25% of income)', impact: '-$250' },
        { category: 'Food', currentAmount: 775, suggestedAmount: 1320, rationale: 'Current spending 775.00 is below recommended 1320.00', impact: '+$545' },
      ],
      executionTrace: agentLogs,
      createdAt: new Date().toISOString(),
    });
    setCurrentPage('report');
  };

  // Simulate approval request after CATEGORIZE
  const hasAnomaly = agentLogs.some(log => log.agent === 'categorize');

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="flex gap-6">
        {/* Left Panel: Workflow Timeline */}
        <div className="w-80 flex-shrink-0">
          <div className="glass-card p-5 sticky top-20">
            <h2 className="text-lg font-semibold text-white mb-4">Workflow Timeline</h2>
            
            <div className="space-y-1">
              {workflowSteps.map((step, idx) => (
                <div 
                  key={step.state} 
                  className={clsx(
                    'workflow-step relative flex items-center gap-4 py-3',
                    step.running && 'bg-emerald-500/10 -mx-2 px-2 rounded-lg'
                  )}
                >
                  <div className="flex-shrink-0">
                    {getStepIcon(step)}
                  </div>
                  <div className="flex-1">
                    <p className={clsx(
                      'text-sm font-medium',
                      step.completed && 'text-emerald-400',
                      step.running && 'text-white',
                      !step.completed && !step.running && 'text-gray-500'
                    )}>
                      {step.label}
                    </p>
                    <p className="text-xs text-gray-600">{step.state}</p>
                  </div>
                  {step.running && (
                    <div className="flex items-center gap-1">
                      <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
                      <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse delay-75" />
                      <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse delay-150" />
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Summary Stats */}
            <div className="mt-6 pt-4 border-t border-fintech-border">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-400">Duration</span>
                <span className="mono-number text-white">{totalDuration}ms</span>
              </div>
              <div className="flex items-center justify-between text-sm mt-2">
                <span className="text-gray-400">Tokens</span>
                <span className="mono-number text-emerald-400">{totalTokensUsed}</span>
              </div>
              <div className="flex items-center justify-between text-sm mt-2">
                <span className="text-gray-400">Cost</span>
                <span className="mono-number text-emerald-400">${totalCostUsed.toFixed(6)}</span>
              </div>
            </div>

            {/* View Report Button */}
            {isComplete && (
              <button
                onClick={viewReport}
                className="btn-primary w-full mt-4 flex items-center justify-center gap-2"
              >
                View Report
                <ArrowRight className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* Right Panel: Live Execution Details */}
        <div className="flex-1 space-y-4">
          {/* Current Agent Info */}
          <div className="glass-card p-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-500/20 flex items-center justify-center">
                  <Bot className="w-5 h-5 text-emerald-500" />
                </div>
                <div>
                  <p className="text-white font-medium">
                    {workflowSteps.find(s => s.running)?.label || 'Idle'}
                  </p>
                  <p className="text-sm text-gray-500">
                    {isExecuting ? 'Processing...' : 'Waiting'}
                  </p>
                </div>
              </div>
              {isExecuting && (
                <div className="flex items-center gap-2 text-emerald-400">
                  <Activity className="w-4 h-4 animate-pulse" />
                  <span className="text-sm">Running</span>
                </div>
              )}
            </div>
          </div>

          {/* Agent Logs */}
          <div className="glass-card p-5">
            <h3 className="text-sm font-medium text-gray-400 mb-4">Execution Log</h3>
            
            <div className="space-y-3 max-h-[500px] overflow-y-auto">
              {logsWithCumulative.map((log, idx) => (
                <div 
                  key={log.id}
                  className="p-3 bg-fintech-darker rounded-lg border border-fintech-border"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Bot className="w-4 h-4 text-emerald-500" />
                      <span className="text-white text-sm capitalize">{log.agent}</span>
                    </div>
                    <div className="flex items-center gap-3 text-xs">
                      <span className="text-gray-500">{log.duration}ms</span>
                      {log.tokens && (
                        <span className="text-emerald-400 mono-number">{log.tokens} tokens</span>
                      )}
                    </div>
                  </div>
                  <p className="text-gray-400 text-sm mt-1">{log.details}</p>
                  {log.cumulativeTokens > 0 && (
                    <div className="mt-2 flex items-center gap-1 text-xs text-gray-500">
                      <Coins className="w-3 h-3" />
                      <span>Cumulative: {log.cumulativeTokens} tokens</span>
                    </div>
                  )}
                </div>
              ))}
              
              {agentLogs.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>Waiting for execution...</p>
                </div>
              )}
            </div>
          </div>

          {/* Cost Accumulation */}
          <div className="glass-card p-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Coins className="w-5 h-5 text-emerald-500" />
                <span className="text-white font-medium">Live Cost</span>
              </div>
              <span className="mono-number text-xl text-emerald-400">
                ${totalCostUsed.toFixed(6)}
              </span>
            </div>
            <div className="mt-3">
              <div className="h-2 bg-fintech-border rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-emerald-600 to-emerald-400 transition-all duration-300"
                  style={{ width: `${Math.min((totalTokensUsed / 2000) * 100, 100)}%` }}
                />
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {totalTokensUsed} / 2,000 tokens
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Approval Modal */}
      {pendingApproval && (
        <div className="modal-overlay">
          <div className="glass-card p-6 max-w-md w-full mx-4 animate-scale-in">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-yellow-500/20 flex items-center justify-center">
                <FileText className="w-5 h-5 text-yellow-500" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white">Approval Required</h3>
                <p className="text-sm text-gray-500">Large anomaly detected</p>
              </div>
            </div>
            
            <div className="bg-fintech-darker rounded-lg p-4 mb-4">
              <p className="text-yellow-400 font-medium">{pendingApproval.description}</p>
              {pendingApproval.amount && (
                <p className="text-white mono-number mt-2">
                  Amount: ${Math.abs(pendingApproval.amount).toLocaleString()}
                </p>
              )}
              {pendingApproval.riskScore && (
                <p className="text-gray-400 text-sm mt-1">
                  Risk Score: {pendingApproval.riskScore.toFixed(2)}
                </p>
              )}
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setPendingApproval(null)}
                className="flex-1 btn-secondary"
              >
                Reject
              </button>
              <button
                onClick={() => setPendingApproval(null)}
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
