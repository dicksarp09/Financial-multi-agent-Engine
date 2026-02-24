'use client';

import { useAppStore } from '@/store';
import { Settings as SettingsIcon, Save, AlertCircle } from 'lucide-react';

export function SettingsScreen() {
  const { settings, setSettings } = useAppStore();

  const updateSetting = (key: string, value: any) => {
    setSettings({ ...settings, [key]: value });
  };

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Settings</h1>
        <p className="text-gray-500">Configure your financial agent preferences</p>
      </div>

      {/* Approval Settings */}
      <div className="glass-card p-5">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <SettingsIcon className="w-5 h-5 text-emerald-500" />
          Approval Thresholds
        </h2>
        
        <div className="space-y-4">
          <div>
            <label className="text-sm text-gray-400">Risk Score Threshold</label>
            <p className="text-xs text-gray-500 mb-2">Transactions with risk score above this require approval</p>
            <div className="flex items-center gap-4">
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={settings.approvalThreshold}
                onChange={(e) => updateSetting('approvalThreshold', parseFloat(e.target.value))}
                className="flex-1 h-2 bg-fintech-border rounded-lg appearance-none cursor-pointer"
              />
              <span className="mono-number text-emerald-400 w-12 text-right">
                {settings.approvalThreshold.toFixed(1)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Anomaly Detection */}
      <div className="glass-card p-5">
        <h2 className="text-lg font-semibold text-white mb-4">Anomaly Detection</h2>
        
        <div>
          <label className="text-sm text-gray-400">Sensitivity Level</label>
          <p className="text-xs text-gray-500 mb-2">Higher sensitivity detects more anomalies</p>
          <div className="flex gap-2">
            {['low', 'medium', 'high'].map((level) => (
              <button
                key={level}
                onClick={() => updateSetting('anomalySensitivity', level)}
                className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-colors ${
                  settings.anomalySensitivity === level
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : 'bg-fintech-border text-gray-400 hover:text-white'
                }`}
              >
                {level.charAt(0).toUpperCase() + level.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* LLM Settings */}
      <div className="glass-card p-5">
        <h2 className="text-lg font-semibold text-white mb-4">LLM Configuration</h2>
        
        <div>
          <label className="text-sm text-gray-400">Model Selection</label>
          <p className="text-xs text-gray-500 mb-2">Choose the LLM model for analysis</p>
          <select
            value={settings.llmModel}
            onChange={(e) => updateSetting('llmModel', e.target.value)}
            className="input-field"
          >
            <option value="llama-3.1-70b-versatile">Llama 3.1 70B Versatile</option>
            <option value="llama-3.1-8b-instant">Llama 3.1 8B Instant</option>
            <option value="mixtral-8x7b-32768">Mixtral 8x7B</option>
          </select>
        </div>
      </div>

      {/* Token Limits */}
      <div className="glass-card p-5">
        <h2 className="text-lg font-semibold text-white mb-4">Usage Limits</h2>
        
        <div>
          <label className="text-sm text-gray-400">Daily Token Limit</label>
          <p className="text-xs text-gray-500 mb-2">Maximum tokens allowed per day</p>
          <div className="flex items-center gap-4">
            <input
              type="range"
              min="10000"
              max="500000"
              step="10000"
              value={settings.tokenLimitDaily}
              onChange={(e) => updateSetting('tokenLimitDaily', parseInt(e.target.value))}
              className="flex-1 h-2 bg-fintech-border rounded-lg appearance-none cursor-pointer"
            />
            <span className="mono-number text-emerald-400 w-24 text-right">
              {settings.tokenLimitDaily.toLocaleString()}
            </span>
          </div>
        </div>
      </div>

      {/* Data Retention */}
      <div className="glass-card p-5">
        <h2 className="text-lg font-semibold text-white mb-4">Data Management</h2>
        
        <div>
          <label className="text-sm text-gray-400">Data Retention Period</label>
          <p className="text-xs text-gray-500 mb-2">How long to keep session data</p>
          <select
            value={settings.dataRetentionDays}
            onChange={(e) => updateSetting('dataRetentionDays', parseInt(e.target.value))}
            className="input-field"
          >
            <option value="30">30 days</option>
            <option value="60">60 days</option>
            <option value="90">90 days</option>
            <option value="180">180 days</option>
            <option value="365">1 year</option>
          </select>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end">
        <button className="btn-primary flex items-center gap-2">
          <Save className="w-4 h-4" />
          Save Settings
        </button>
      </div>

      {/* Warning */}
      <div className="flex items-start gap-3 p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
        <AlertCircle className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm text-yellow-400 font-medium">Configuration Notice</p>
          <p className="text-xs text-gray-400 mt-1">
            Some settings may require restarting the agent service to take effect.
          </p>
        </div>
      </div>
    </div>
  );
}
