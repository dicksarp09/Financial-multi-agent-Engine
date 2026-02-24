// API Service for connecting frontend to backend

const API_BASE = 'http://localhost:8000/api';

async function fetchJSON(url: string, options?: RequestInit) {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || 'Request failed');
  }
  
  const text = await response.text();
  return text ? JSON.parse(text) : null;
}

// System
export async function getSystemStatus() {
  return fetchJSON(`${API_BASE}/system/status`);
}

export async function getSettings() {
  return fetchJSON(`${API_BASE}/system/settings`);
}

export async function updateSettings(settings: any) {
  return fetchJSON(`${API_BASE}/system/settings`, {
    method: 'POST',
    body: JSON.stringify(settings),
  });
}

// Sessions
export async function getSessions() {
  return fetchJSON(`${API_BASE}/sessions`);
}

export async function getSession(sessionId: string) {
  return fetchJSON(`${API_BASE}/sessions/${sessionId}`);
}

export async function createSession() {
  return fetchJSON(`${API_BASE}/sessions`, { method: 'POST' });
}

// Upload
export async function validateFile(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(`${API_BASE}/upload/validate`, {
    method: 'POST',
    body: formData,
  });
  
  return response.json();
}

// Workflow
export async function getWorkflow(sessionId: string) {
  return fetchJSON(`${API_BASE}/workflow/${sessionId}`);
}

export async function executeWorkflow(sessionId: string) {
  return fetchJSON(`${API_BASE}/workflow/${sessionId}/execute`, {
    method: 'POST',
  });
}

export async function getExecutionLogs(sessionId: string) {
  return fetchJSON(`${API_BASE}/workflow/${sessionId}/logs`);
}

// Approval
export async function getApproval(sessionId: string) {
  return fetchJSON(`${API_BASE}/approvals/${sessionId}`);
}

export async function respondToApproval(sessionId: string, action: 'approve' | 'reject') {
  return fetchJSON(`${API_BASE}/approvals/${sessionId}/respond?action=${action}`, {
    method: 'POST',
  });
}

// Reports
export async function getReport(sessionId: string) {
  return fetchJSON(`${API_BASE}/reports/${sessionId}`);
}

export async function refineReport(sessionId: string, instruction: string) {
  return fetchJSON(`${API_BASE}/reports/${sessionId}/refine`, {
    method: 'POST',
    body: JSON.stringify({ instruction }),
  });
}

export async function exportReport(sessionId: string, format: 'json' | 'csv' | 'pdf') {
  const response = await fetch(`${API_BASE}/reports/${sessionId}/export?format=${format}`);
  return response.text();
}

// Conversation
export async function sendMessage(sessionId: string, message: string) {
  return fetchJSON(`${API_BASE}/conversation/${sessionId}`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  });
}
