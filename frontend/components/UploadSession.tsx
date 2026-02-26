'use client';

import { useState, useCallback } from 'react';
import { useAppStore } from '@/store';
import { createSession, validateFile, executeWorkflow } from '@/lib/api';
import { Upload as UploadIcon, File, Check, AlertCircle, ArrowRight, Loader2 } from 'lucide-react';
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
    setCurrentAgentState,
    currentSessionId,
    setCurrentSessionId,
    startExecution
  } = useAppStore();

  const [isDragging, setIsDragging] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

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
      handleValidateFile(file);
    }
  };

  const handleValidateFile = async (file: File) => {
    setIsUploading(true);
    try {
      const session = await createSession();
      setCurrentSessionId(session.id);
      
      const result = await validateFile(file, session.id);
      
      if (result.valid) {
        setUploadValidation({
          valid: true,
          errors: result.errors || [],
        });
        
        setUploadedTransactions(result.transactions || []);
      } else {
        setUploadValidation({
          valid: false,
          errors: result.errors || ['Validation failed'],
        });
      }
    } catch (error) {
      console.error('Upload failed:', error);
      setUploadValidation({
        valid: false,
        errors: ['Failed to upload and validate file'],
      });
    } finally {
      setIsUploading(false);
    }
  };

  const handleStartAnalysis = async () => {
    if (!currentSessionId) {
      console.error('No session ID');
      return;
    }
    await startExecution(currentSessionId);
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
            onClick={handleStartAnalysis}
            disabled={!uploadValidation?.valid || isExecuting || isUploading || !currentSessionId}
            className="btn-primary flex items-center gap-2"
          >
            {isUploading ? (
              <>Processing...</>
            ) : isExecuting ? (
              <>Running...</>
            ) : (
              <>
                Start Analysis
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
