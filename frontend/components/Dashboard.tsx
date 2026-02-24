'use client';

import { useAppStore } from '@/store';
import { 
  Upload, 
  FileText, 
  TrendingUp, 
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  Clock,
  XCircle,
  Activity,
  Cpu
} from 'lucide-react';
import clsx from 'clsx';

export function Dashboard() {
  const { sessions, systemStatus, setCurrentPage, setCurrentSessionId } = useAppStore();

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'Complete': return <CheckCircle className="w-4 h-4 text-emerald-500" />;
      case 'Awaiting Approval': return <Clock className="w-4 h-4 text-yellow-500" />;
      case 'Failed': return <XCircle className="w-4 h-4 text-red-500" />;
      default: return <Activity className="w-4 h-4 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Complete': return 'text-emerald-400 bg-emerald-500/10';
      case 'Awaiting Approval': return 'text-yellow-400 bg-yellow-500/10';
      case 'Failed': return 'text-red-400 bg-red-500/10';
      default: return 'text-gray-400 bg-gray-500/10';
    }
  };

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Dashboard</h1>
          <p className="text-gray-500">Monitor your financial analysis sessions</p>
        </div>
        <button 
          onClick={() => setCurrentPage('upload')}
          className="btn-primary flex items-center gap-2"
        >
          <Upload className="w-5 h-5" />
          Upload CSV
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-4 gap-4">
        {/* Total Sessions */}
        <div className="glass-card p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-gray-400 text-sm">Total Sessions</span>
            <FileText className="w-5 h-5 text-emerald-500" />
          </div>
          <p className="text-3xl mono-number text-white">{sessions.length}</p>
          <p className="text-xs text-gray-500 mt-1">All time</p>
        </div>

        {/* Success Rate */}
        <div className="glass-card p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-gray-400 text-sm">Success Rate</span>
            <CheckCircle className="w-5 h-5 text-emerald-500" />
          </div>
          <p className="text-3xl mono-number text-white">75%</p>
          <p className="text-xs text-emerald-500 mt-1 flex items-center gap-1">
            <TrendingUp className="w-3 h-3" /> +5% this month
          </p>
        </div>

        {/* Avg Savings */}
        <div className="glass-card p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-gray-400 text-sm">Avg Savings Rate</span>
            <TrendingDown className="w-5 h-5 text-emerald-500" />
          </div>
          <p className="text-3xl mono-number text-white">54.2%</p>
          <p className="text-xs text-gray-500 mt-1">Last 30 days</p>
        </div>

        {/* Pending Approvals */}
        <div className="glass-card p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-gray-400 text-sm">Pending</span>
            <Clock className="w-5 h-5 text-yellow-500" />
          </div>
          <p className="text-3xl mono-number text-white">1</p>
          <p className="text-xs text-yellow-500 mt-1">Awaiting action</p>
        </div>
      </div>

      {/* System Status */}
      <div className="glass-card p-5">
        <h2 className="text-lg font-semibold text-white mb-4">System Status</h2>
        <div className="grid grid-cols-4 gap-4">
          {/* Agent Health */}
          <div className="flex items-center gap-3">
            <div className={clsx(
              'w-3 h-3 rounded-full',
              systemStatus.agentHealth === 'healthy' && 'bg-emerald-500',
              systemStatus.agentHealth === 'degraded' && 'bg-yellow-500',
              systemStatus.agentHealth === 'unhealthy' && 'bg-red-500'
            )} />
            <div>
              <p className="text-sm text-gray-300">Agent Health</p>
              <p className="text-xs text-gray-500 capitalize">{systemStatus.agentHealth}</p>
            </div>
          </div>

          {/* LLM Availability */}
          <div className="flex items-center gap-3">
            <div className={clsx(
              'w-3 h-3 rounded-full',
              systemStatus.llmAvailable ? 'bg-emerald-500' : 'bg-red-500'
            )} />
            <div>
              <p className="text-sm text-gray-300">LLM Service</p>
              <p className="text-xs text-gray-500">{systemStatus.llmAvailable ? 'Available' : 'Offline'}</p>
            </div>
          </div>

          {/* Active Sessions */}
          <div className="flex items-center gap-3">
            <Cpu className="w-4 h-4 text-emerald-500" />
            <div>
              <p className="text-sm text-gray-300">Active Sessions</p>
              <p className="text-xs text-gray-500">{systemStatus.activeSessions} running</p>
            </div>
          </div>

          {/* Token Usage */}
          <div className="flex items-center gap-3">
            <Activity className="w-4 h-4 text-emerald-500" />
            <div>
              <p className="text-sm text-gray-300">Tokens Today</p>
              <p className="text-xs text-gray-500">
                <span className="mono-number text-emerald-400">{systemStatus.tokensUsedToday.toLocaleString()}</span>
                {' / '}
                {systemStatus.tokensLimit.toLocaleString()}
              </p>
            </div>
          </div>
        </div>

        {/* Token Progress Bar */}
        <div className="mt-4">
          <div className="h-2 bg-fintech-border rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-emerald-600 to-emerald-400 transition-all duration-500"
              style={{ width: `${(systemStatus.tokensUsedToday / systemStatus.tokensLimit) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Recent Sessions Table */}
      <div className="glass-card">
        <div className="p-5 border-b border-fintech-border">
          <h2 className="text-lg font-semibold text-white">Recent Sessions</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-xs text-gray-500 uppercase tracking-wider">
                <th className="px-5 py-4">Session ID</th>
                <th className="px-5 py-4">Date</th>
                <th className="px-5 py-4">Status</th>
                <th className="px-5 py-4">Anomalies</th>
                <th className="px-5 py-4">Budget Change</th>
                <th className="px-5 py-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((session) => (
                <tr key={session.id} className="table-row">
                  <td className="px-5 py-4">
                    <span className="mono-number text-emerald-400">{session.id}</span>
                  </td>
                  <td className="px-5 py-4 text-gray-300">{session.date}</td>
                  <td className="px-5 py-4">
                    <span className={clsx(
                      'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium',
                      getStatusColor(session.status)
                    )}>
                      {getStatusIcon(session.status)}
                      {session.status}
                    </span>
                  </td>
                  <td className="px-5 py-4">
                    {session.anomaliesCount > 0 ? (
                      <span className="flex items-center gap-1 text-yellow-400">
                        <AlertTriangle className="w-4 h-4" />
                        {session.anomaliesCount}
                      </span>
                    ) : (
                      <span className="text-gray-500">0</span>
                    )}
                  </td>
                  <td className="px-5 py-4">
                    <span className={clsx(
                      'mono-number',
                      session.budgetChangePercent > 0 ? 'text-emerald-400' : 'text-red-400'
                    )}>
                      {session.budgetChangePercent > 0 ? '+' : ''}{session.budgetChangePercent}%
                    </span>
                  </td>
                  <td className="px-5 py-4">
                    <button 
                      onClick={() => {
                        setCurrentSessionId(session.id);
                        setCurrentPage('report');
                      }}
                      className="text-emerald-400 hover:text-emerald-300 text-sm font-medium"
                    >
                      View Report
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="flex gap-4">
        <button 
          onClick={() => setCurrentPage('upload')}
          className="btn-secondary flex items-center gap-2"
        >
          <Upload className="w-4 h-4" />
          Upload New Session
        </button>
        <button 
          onClick={() => setCurrentPage('history')}
          className="btn-secondary flex items-center gap-2"
        >
          <FileText className="w-4 h-4" />
          View All Reports
        </button>
      </div>
    </div>
  );
}
