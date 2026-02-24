'use client';

import { useEffect } from 'react';
import { useAppStore } from '@/store';
import { Dashboard } from '@/components/Dashboard';
import { UploadSession } from '@/components/UploadSession';
import { ExecutionView } from '@/components/ExecutionView';
import { ReportScreen } from '@/components/ReportScreen';
import { SessionHistory } from '@/components/SessionHistory';
import { SettingsScreen } from '@/components/SettingsScreen';

export default function Home() {
  const { 
    currentPage, 
    loadSessions, 
    loadSystemStatus, 
    loadSettings,
    currentSessionId,
    loadWorkflow,
    loadExecutionLogs,
    loadApproval,
    loadReport,
    setCurrentReport,
    setIsExecuting,
    pendingApproval,
    workflowSteps,
    isExecuting
  } = useAppStore();

  useEffect(() => {
    loadSystemStatus();
    loadSettings();
    loadSessions();
  }, []);

  // Poll for workflow updates when executing
  useEffect(() => {
    if (currentSessionId && isExecuting) {
      const interval = setInterval(() => {
        loadWorkflow(currentSessionId);
        loadExecutionLogs(currentSessionId);
        loadApproval(currentSessionId);
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [currentSessionId, isExecuting]);

  // Load report when workflow completes
  useEffect(() => {
    const complete = workflowSteps.some(s => s.completed && s.state === 'COMPLETE');
    if (complete && currentSessionId) {
      loadReport(currentSessionId);
      setIsExecuting(false);
    }
  }, [workflowSteps, currentSessionId]);

  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return <Dashboard />;
      case 'upload':
        return <UploadSession />;
      case 'execution':
        return <ExecutionView />;
      case 'report':
        return <ReportScreen />;
      case 'history':
        return <SessionHistory />;
      case 'settings':
        return <SettingsScreen />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <div className="min-h-screen bg-fintech-darker">
      {renderPage()}
    </div>
  );
}
