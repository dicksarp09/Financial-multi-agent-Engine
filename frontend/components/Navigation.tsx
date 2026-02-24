'use client';

import { useAppStore } from '@/store';
import { 
  LayoutDashboard, 
  Upload, 
  History, 
  FileText, 
  Settings,
  Bot
} from 'lucide-react';
import clsx from 'clsx';

const navItems = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'upload', label: 'Upload Session', icon: Upload },
  { id: 'history', label: 'Session History', icon: History },
  { id: 'settings', label: 'Settings', icon: Settings },
] as const;

export function Navigation() {
  const { currentPage, setCurrentPage, systemStatus, isExecuting } = useAppStore();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 h-16 bg-fintech-darker/95 backdrop-blur-md border-b border-fintech-border">
      <div className="max-w-7xl mx-auto h-full px-6 flex items-center justify-between">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-emerald-700 flex items-center justify-center">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-white">Financial Agent</h1>
            <p className="text-xs text-gray-500">Multi-Agent System</p>
          </div>
        </div>

        {/* Nav Items */}
        <div className="flex items-center gap-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentPage === item.id;
            
            return (
              <button
                key={item.id}
                onClick={() => setCurrentPage(item.id)}
                className={clsx(
                  'flex items-center gap-2 px-4 py-2 rounded-lg transition-all duration-200',
                  isActive 
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' 
                    : 'text-gray-400 hover:text-white hover:bg-fintech-card'
                )}
              >
                <Icon className="w-4 h-4" />
                <span className="text-sm font-medium">{item.label}</span>
              </button>
            );
          })}
        </div>

        {/* Status Indicators */}
        <div className="flex items-center gap-4">
          {/* Agent Health */}
          <div className="flex items-center gap-2">
            <div className={clsx(
              'w-2 h-2 rounded-full',
              systemStatus.agentHealth === 'healthy' && 'bg-emerald-500 animate-pulse',
              systemStatus.agentHealth === 'degraded' && 'bg-yellow-500',
              systemStatus.agentHealth === 'unhealthy' && 'bg-red-500'
            )} />
            <span className="text-xs text-gray-400">Agents</span>
          </div>

          {/* LLM Status */}
          <div className="flex items-center gap-2">
            <div className={clsx(
              'w-2 h-2 rounded-full',
              systemStatus.llmAvailable ? 'bg-emerald-500' : 'bg-red-500'
            )} />
            <span className="text-xs text-gray-400">LLM</span>
          </div>

          {/* Token Usage */}
          <div className="text-xs text-gray-500">
            <span className="mono-number text-emerald-400">{systemStatus.tokensUsedToday.toLocaleString()}</span>
            <span className="text-gray-600"> / </span>
            <span className="mono-number">{systemStatus.tokensLimit.toLocaleString()}</span>
          </div>

          {/* Execution Indicator */}
          {isExecuting && (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-500/20 border border-emerald-500/30 rounded-full">
              <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
              <span className="text-xs text-emerald-400">Running</span>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
