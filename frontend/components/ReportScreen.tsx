'use client';

import { useState } from 'react';
import { useAppStore } from '@/store';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell
} from 'recharts';
import { 
  FileText, 
  TrendingUp, 
  TrendingDown, 
  AlertTriangle,
  DollarSign,
  Activity,
  Download,
  MessageSquare,
  ChevronRight,
  ChevronDown,
  FileJson,
  File
} from 'lucide-react';
import clsx from 'clsx';

const COLORS = ['#10b981', '#34d399', '#6ee7b7', '#a7f3d0', '#d1fae5', '#ecfdf5', '#047857'];

type TabType = 'summary' | 'categories' | 'anomalies' | 'budget' | 'trace';

export function ReportScreen() {
  const { currentReport, isConversationOpen, setIsConversationOpen, reportVersions, addReportVersion } = useAppStore();
  const [activeTab, setActiveTab] = useState<TabType>('summary');
  const [expandedLogs, setExpandedLogs] = useState<string[]>([]);
  const [showComparison, setShowComparison] = useState(false);

  const tabs = [
    { id: 'summary', label: 'Summary', icon: FileText },
    { id: 'categories', label: 'Categories', icon: TrendingUp },
    { id: 'anomalies', label: 'Anomalies', icon: AlertTriangle },
    { id: 'budget', label: 'Budget', icon: DollarSign },
    { id: 'trace', label: 'Trace', icon: Activity },
  ] as const;

  const createNewVersion = () => {
    if (currentReport) {
      const newVersion = {
        ...currentReport,
        version: currentReport.version + 1,
        createdAt: new Date().toISOString(),
      };
      addReportVersion(newVersion);
    }
  };

  const toggleLogExpanded = (id: string) => {
    setExpandedLogs(prev => 
      prev.includes(id) 
        ? prev.filter(i => i !== id)
        : [...prev, id]
    );
  };

  if (!currentReport) {
    return (
      <div className="max-w-7xl mx-auto p-6">
        <div className="glass-card p-12 text-center">
          <FileText className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-white mb-2">No Report Selected</h2>
          <p className="text-gray-500">Upload a session or select a previous report to view</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="flex gap-6">
        {/* Main Content */}
        <div className="flex-1 space-y-4">
          {/* Header */}
          <div className="glass-card p-5">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-semibold text-white">Financial Report</h1>
                <p className="text-gray-500">
                  Session {currentReport.sessionId} • Version {currentReport.version}
                </p>
              </div>
              <div className="flex gap-2">
                <button 
                  onClick={() => setShowComparison(!showComparison)}
                  className="btn-secondary flex items-center gap-2"
                >
                  {showComparison ? 'Hide' : 'Compare'} Versions
                </button>
                <button className="btn-secondary flex items-center gap-2">
                  <Download className="w-4 h-4" />
                  PDF
                </button>
                <button className="btn-secondary flex items-center gap-2">
                  <File className="w-4 h-4" />
                  CSV
                </button>
                <button className="btn-secondary flex items-center gap-2">
                  <FileJson className="w-4 h-4" />
                  JSON
                </button>
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="glass-card">
            <div className="flex border-b border-fintech-border">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={clsx(
                      'flex items-center gap-2 px-5 py-4 text-sm font-medium transition-colors',
                      activeTab === tab.id
                        ? 'text-emerald-400 border-b-2 border-emerald-500 bg-emerald-500/5'
                        : 'text-gray-400 hover:text-white hover:bg-fintech-cardHover'
                    )}
                  >
                    <Icon className="w-4 h-4" />
                    {tab.label}
                  </button>
                );
              })}
            </div>

            {/* Tab Content */}
            <div className="p-5">
              {/* Summary Tab */}
              {activeTab === 'summary' && (
                <div className="grid grid-cols-4 gap-4">
                  <div className="glass-card p-4 text-center">
                    <p className="text-gray-400 text-sm">Total Income</p>
                    <p className="text-2xl mono-number text-emerald-400 mt-1">
                      ${currentReport.totalIncome.toLocaleString()}
                    </p>
                  </div>
                  <div className="glass-card p-4 text-center">
                    <p className="text-gray-400 text-sm">Total Expenses</p>
                    <p className="text-2xl mono-number text-red-400 mt-1">
                      ${currentReport.totalExpenses.toLocaleString()}
                    </p>
                  </div>
                  <div className="glass-card p-4 text-center">
                    <p className="text-gray-400 text-sm">Savings Rate</p>
                    <p className="text-2xl mono-number text-white mt-1">
                      {currentReport.savingsRate.toFixed(1)}%
                    </p>
                  </div>
                  <div className="glass-card p-4 text-center">
                    <p className="text-gray-400 text-sm">Risk Score</p>
                    <p className={clsx(
                      'text-2xl mono-number mt-1',
                      currentReport.riskScore < 0.3 ? 'text-emerald-400' :
                      currentReport.riskScore < 0.7 ? 'text-yellow-400' : 'text-red-400'
                    )}>
                      {currentReport.riskScore.toFixed(2)}
                    </p>
                  </div>
                </div>
              )}

              {/* Categories Tab */}
              {activeTab === 'categories' && (
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={currentReport.categoryBreakdown} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" stroke="#1a2540" />
                      <XAxis type="number" stroke="#6b7280" />
                      <YAxis dataKey="category" type="category" stroke="#6b7280" width={100} />
                      <Tooltip 
                        contentStyle={{ 
                          backgroundColor: '#0d1424', 
                          border: '1px solid #1a2540',
                          borderRadius: '8px'
                        }}
                      />
                      <Bar dataKey="amount" fill="#10b981" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* Anomalies Tab */}
              {activeTab === 'anomalies' && (
                <div className="space-y-3">
                  {currentReport.anomalies.map((anomaly) => (
                    <div 
                      key={anomaly.id}
                      className={clsx(
                        'p-4 rounded-lg border',
                        anomaly.severity === 'critical' && 'bg-red-500/10 border-red-500/30',
                        anomaly.severity === 'high' && 'bg-orange-500/10 border-orange-500/30',
                        anomaly.severity === 'medium' && 'bg-yellow-500/10 border-yellow-500/30',
                        anomaly.severity === 'low' && 'bg-fintech-card border-fintech-border'
                      )}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-white font-medium">{anomaly.description}</p>
                          <p className="text-sm text-gray-400 mt-1">{anomaly.reason}</p>
                        </div>
                        <div className="text-right">
                          <p className="mono-number text-red-400">
                            ${Math.abs(anomaly.amount).toLocaleString()}
                          </p>
                          <span className={clsx(
                            'text-xs px-2 py-1 rounded-full',
                            anomaly.severity === 'critical' && 'bg-red-500/20 text-red-400',
                            anomaly.severity === 'high' && 'bg-orange-500/20 text-orange-400',
                            anomaly.severity === 'medium' && 'bg-yellow-500/20 text-yellow-400',
                            anomaly.severity === 'low' && 'bg-gray-500/20 text-gray-400'
                          )}>
                            {anomaly.severity}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Budget Tab */}
              {activeTab === 'budget' && (
                <div className="space-y-4">
                  {currentReport.budgetRecommendations.map((rec, idx) => (
                    <div key={idx} className="glass-card p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-white font-medium">{rec.category}</p>
                          <p className="text-sm text-gray-400 mt-1">{rec.rationale}</p>
                        </div>
                        <div className="text-right">
                          <div className="flex items-center gap-2">
                            <span className="mono-number text-gray-400 line-through">
                              ${rec.currentAmount}
                            </span>
                            <ChevronRight className="w-4 h-4 text-gray-600" />
                            <span className="mono-number text-emerald-400">
                              ${rec.suggestedAmount}
                            </span>
                          </div>
                          <span className="text-xs text-emerald-400">{rec.impact}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Trace Tab */}
              {activeTab === 'trace' && (
                <div className="space-y-2">
                  {currentReport.executionTrace.map((log) => (
                    <div key={log.id} className="glass-card">
                      <button
                        onClick={() => toggleLogExpanded(log.id)}
                        className="w-full p-4 flex items-center justify-between text-left"
                      >
                        <div className="flex items-center gap-3">
                          {expandedLogs.includes(log.id) ? (
                            <ChevronDown className="w-4 h-4 text-gray-400" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-gray-400" />
                          )}
                          <Activity className="w-4 h-4 text-emerald-500" />
                          <span className="text-white capitalize">{log.agent}</span>
                          <span className="text-gray-500">•</span>
                          <span className="text-gray-400">{log.action}</span>
                        </div>
                        <div className="flex items-center gap-4">
                          <span className="mono-number text-gray-500">{log.duration}ms</span>
                          {log.tokens && (
                            <span className="mono-number text-emerald-400">{log.tokens} tokens</span>
                          )}
                        </div>
                      </button>
                      {expandedLogs.includes(log.id) && (
                        <div className="px-4 pb-4 pt-2 border-t border-fintech-border">
                          <pre className="text-sm text-gray-400 whitespace-pre-wrap">
                            {JSON.stringify({
                              agent: log.agent,
                              action: log.action,
                              duration: log.duration,
                              tokens: log.tokens,
                              cost: log.cost,
                              details: log.details,
                            }, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Conversation Panel */}
        <div className={clsx(
          'transition-all duration-300',
          isConversationOpen ? 'w-96' : 'w-0'
        )}>
          {isConversationOpen && (
            <div className="glass-card h-full flex flex-col">
              <div className="p-4 border-b border-fintech-border">
                <div className="flex items-center justify-between">
                  <h3 className="text-white font-medium">Ask the Agent</h3>
                  <button 
                    onClick={() => setIsConversationOpen(false)}
                    className="text-gray-400 hover:text-white"
                  >
                    ×
                  </button>
                </div>
              </div>
              
              <div className="flex-1 p-4 overflow-y-auto space-y-3">
                <div className="bg-fintech-darker p-3 rounded-lg">
                  <p className="text-sm text-gray-300">
                    Ask questions about your finances or request changes to your budget.
                  </p>
                </div>
              </div>
              
              <div className="p-4 border-t border-fintech-border">
                <input
                  type="text"
                  placeholder="Type a message..."
                  className="input-field"
                />
                <button className="btn-primary w-full mt-3">
                  Send
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Floating Toggle Button */}
        {!isConversationOpen && (
          <button
            onClick={() => setIsConversationOpen(true)}
            className="fixed right-6 bottom-6 w-14 h-14 rounded-full bg-emerald-600 hover:bg-emerald-500 flex items-center justify-center shadow-lg hover:shadow-emerald-500/30 transition-all"
          >
            <MessageSquare className="w-6 h-6 text-white" />
          </button>
        )}
      </div>
    </div>
  );
}
