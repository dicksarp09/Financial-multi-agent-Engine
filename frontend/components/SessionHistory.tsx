'use client';

import { useAppStore } from '@/store';
import { useState } from 'react';
import { History, TrendingUp, TrendingDown, AlertTriangle, CheckCircle, Clock, XCircle, Eye, RotateCcw } from 'lucide-react';
import clsx from 'clsx';

export function SessionHistory() {
  const { sessions, setCurrentSessionId, setCurrentPage } = useAppStore();
  const [selectedSession, setSelectedSession] = useState<string | null>(null);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'Complete': return <CheckCircle className="w-4 h-4 text-emerald-500" />;
      case 'Awaiting Approval': return <Clock className="w-4 h-4 text-yellow-500" />;
      case 'Failed': return <XCircle className="w-4 h-4 text-red-500" />;
      default: return <History className="w-4 h-4 text-gray-500" />;
    }
  };

  const viewSession = (sessionId: string) => {
    setCurrentSessionId(sessionId);
    setCurrentPage('report');
  };

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Session History</h1>
          <p className="text-gray-500">View and manage past analysis sessions</p>
        </div>
      </div>

      <div className="glass-card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="text-left text-xs text-gray-500 uppercase tracking-wider bg-fintech-card">
              <th className="px-5 py-4">Session ID</th>
              <th className="px-5 py-4">Date</th>
              <th className="px-5 py-4">Version</th>
              <th className="px-5 py-4">Risk Score</th>
              <th className="px-5 py-4">Status</th>
              <th className="px-5 py-4">Savings Rate</th>
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
                  <span className="px-2 py-1 rounded bg-fintech-border text-sm text-gray-300">
                    v{session.version}
                  </span>
                </td>
                <td className="px-5 py-4">
                  <span className={clsx(
                    'mono-number',
                    session.riskScore < 0.3 ? 'text-emerald-400' :
                    session.riskScore < 0.7 ? 'text-yellow-400' : 'text-red-400'
                  )}>
                    {session.riskScore.toFixed(2)}
                  </span>
                </td>
                <td className="px-5 py-4">
                  <span className={clsx(
                    'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium',
                    session.status === 'Complete' && 'text-emerald-400 bg-emerald-500/10',
                    session.status === 'Awaiting Approval' && 'text-yellow-400 bg-yellow-500/10',
                    session.status === 'Failed' && 'text-red-400 bg-red-500/10'
                  )}>
                    {getStatusIcon(session.status)}
                    {session.status}
                  </span>
                </td>
                <td className="px-5 py-4">
                  <span className="mono-number text-white">{session.savingsRate.toFixed(1)}%</span>
                </td>
                <td className="px-5 py-4">
                  <div className="flex gap-2">
                    <button 
                      onClick={() => viewSession(session.id)}
                      className="p-2 hover:bg-fintech-border rounded-lg transition-colors"
                      title="View Report"
                    >
                      <Eye className="w-4 h-4 text-gray-400 hover:text-white" />
                    </button>
                    <button 
                      className="p-2 hover:bg-fintech-border rounded-lg transition-colors"
                      title="Revert to this version"
                    >
                      <RotateCcw className="w-4 h-4 text-gray-400 hover:text-white" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
