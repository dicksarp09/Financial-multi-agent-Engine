'use client';

import { useState, useCallback } from 'react';
import { useAppStore } from '@/store';
import { Upload as UploadIcon, File, Check, X, AlertCircle, Play, ArrowRight } from 'lucide-react';
import clsx from 'clsx';

const schemaColumns = [
  { name: 'date', type: 'string', required: true, description: 'Transaction date (YYYY-MM-DD)' },
  { name: 'description', type: 'string', required: true, description: 'Transaction description' },
  { name: 'amount', type: 'number', required: true, description: 'Positive for income, negative for expense' },
  { name: 'category', type: 'string', required: false, description: 'Optional category tag' },
];

export function UploadSession() {
  const { 
    setCurrentPage, 
    uploadValidation, 
    setUploadValidation,
    uploadedTransactions,
    setUploadedTransactions,
    isExecuting,
    setIsExecuting,
    addAgentLog,
    clearAgentLogs,
    workflowSteps,
    setWorkflowSteps,
    setCurrentAgentState
  } = useAppStore();

  const [isDragging, setIsDragging] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file && file.name.endsWith('.csv')) {
      setFileName(file.name);
      validateFile(file);
    }
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setFileName(file.name);
      validateFile(file);
    }
  };

  const validateFile = (file: File) => {
    // Simulate validation
    setTimeout(() => {
      setUploadValidation({
        valid: true,
        errors: [],
      });
      
      // Sample transactions
      setUploadedTransactions([
        { id: '1', date: '2024-02-01', description: 'Salary', amount: 5000 },
        { id: '2', date: '2024-02-02', description: 'Apartment Rent', amount: -1500 },
        { id: '3', date: '2024-02-05', description: 'Grocery Store', amount: -150 },
        { id: '4', date: '2024-02-10', description: 'Gas Station', amount: -50 },
        { id: '5', date: '2024-02-15', description: 'Electric Bill', amount: -100 },
      ]);
    }, 500);
  };

  const startAnalysis = async () => {
    setIsExecuting(true);
    setCurrentPage('execution');
    clearAgentLogs();
    
    // Simulate workflow execution
    const states = ['INIT', 'INGEST', 'CATEGORIZE', 'ANALYZE', 'BUDGET', 'EVALUATE', 'COMPLETE'];
    
    for (let i = 0; i < states.length; i++) {
      const state = states[i] as any;
      
      // Update workflow steps
      const steps = workflowSteps.map((step, idx) => ({
        ...step,
        completed: idx < i,
        running: idx === i,
      }));
      setWorkflowSteps(steps);
      setCurrentAgentState(state);
      
      // Add log entry
      addAgentLog({
        id: `log-${i}`,
        timestamp: new Date().toISOString(),
        agent: state.toLowerCase(),
        action: `Executing ${state}`,
        duration: Math.floor(Math.random() * 500) + 100,
        tokens: state === 'CATEGORIZE' || state === 'BUDGET' ? Math.floor(Math.random() * 500) + 300 : 0,
        cost: state === 'CATEGORIZE' || state === 'BUDGET' ? parseFloat((Math.random() * 0.001).toFixed(6)) : 0,
        details: `${state} step completed successfully`,
      });
      
      await new Promise(resolve => setTimeout(resolve, 800));
    }
    
    setIsExecuting(false);
  };

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-2xl font-semibold text-white">Upload Session</h1>
        <p className="text-gray-500">Upload your transaction data to begin analysis</p>
      </div>

      {/* Step 1: Upload */}
      <div className="glass-card p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Step 1 — Upload Data</h2>
        
        {/* Drop Zone */}
        <div 
          className={clsx(
            'drop-zone rounded-xl p-12 text-center cursor-pointer',
            isDragging && 'active'
          )}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => document.getElementById('file-input')?.click()}
        >
          <input 
            type="file" 
            id="file-input"
            accept=".csv"
            className="hidden"
            onChange={handleFileSelect}
          />
          
          {fileName ? (
            <div className="flex flex-col items-center gap-3">
              <div className="w-16 h-16 rounded-full bg-emerald-500/20 flex items-center justify-center">
                <File className="w-8 h-8 text-emerald-500" />
              </div>
              <div>
                <p className="text-white font-medium">{fileName}</p>
                <p className="text-sm text-gray-500">Click to replace file</p>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3">
              <div className="w-16 h-16 rounded-full bg-fintech-border flex items-center justify-center">
                <UploadIcon className="w-8 h-8 text-gray-400" />
              </div>
              <div>
                <p className="text-white font-medium">Drop CSV file here</p>
                <p className="text-sm text-gray-500">or click to browse</p>
              </div>
            </div>
          )}
        </div>

        {/* Schema Preview */}
        <div className="mt-6">
          <h3 className="text-sm font-medium text-gray-400 mb-3">Expected Schema</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500">
                  <th className="pb-2 font-medium">Column</th>
                  <th className="pb-2 font-medium">Type</th>
                  <th className="pb-2 font-medium">Required</th>
                  <th className="pb-2 font-medium">Description</th>
                </tr>
              </thead>
              <tbody>
                {schemaColumns.map((col) => (
                  <tr key={col.name} className="border-t border-fintech-border">
                    <td className="py-2 mono-number text-emerald-400">{col.name}</td>
                    <td className="py-2 text-gray-400">{col.type}</td>
                    <td className="py-2">
                      {col.required ? (
                        <span className="text-emerald-400">Required</span>
                      ) : (
                        <span className="text-gray-500">Optional</span>
                      )}
                    </td>
                    <td className="py-2 text-gray-500">{col.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Validation Status */}
        {uploadValidation && (
          <div className={clsx(
            'mt-6 p-4 rounded-xl border',
            uploadValidation.valid 
              ? 'bg-emerald-500/10 border-emerald-500/30' 
              : 'bg-red-500/10 border-red-500/30'
          )}>
            {uploadValidation.valid ? (
              <div className="flex items-center gap-2 text-emerald-400">
                <Check className="w-5 h-5" />
                <span>File validated successfully</span>
              </div>
            ) : (
              <div className="flex items-start gap-2 text-red-400">
                <AlertCircle className="w-5 h-5 mt-0.5" />
                <div>
                  <p>Validation failed</p>
                  <ul className="mt-1 text-sm text-red-300">
                    {uploadValidation.errors.map((err, i) => (
                      <li key={i}>• {err}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Transaction Preview */}
        {uploadedTransactions.length > 0 && (
          <div className="mt-6">
            <h3 className="text-sm font-medium text-gray-400 mb-3">
              Preview ({uploadedTransactions.length} transactions)
            </h3>
            <div className="overflow-x-auto bg-fintech-darker rounded-xl border border-fintech-border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 border-b border-fintech-border">
                    <th className="px-4 py-3 font-medium">Date</th>
                    <th className="px-4 py-3 font-medium">Description</th>
                    <th className="px-4 py-3 font-medium text-right">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {uploadedTransactions.slice(0, 5).map((txn) => (
                    <tr key={txn.id} className="border-b border-fintech-border last:border-0">
                      <td className="px-4 py-3 text-gray-300">{txn.date}</td>
                      <td className="px-4 py-3 text-gray-300">{txn.description}</td>
                      <td className={clsx(
                        'px-4 py-3 text-right mono-number',
                        txn.amount >= 0 ? 'text-emerald-400' : 'text-red-400'
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

        {/* Start Button */}
        <div className="mt-6 flex justify-end">
          <button
            onClick={startAnalysis}
            disabled={!uploadValidation?.valid || isExecuting}
            className="btn-primary flex items-center gap-2"
          >
            Start Analysis
            <ArrowRight className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
