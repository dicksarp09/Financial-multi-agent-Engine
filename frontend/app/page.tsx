'use client';

import { useEffect } from 'react';
import { useAppStore } from '@/store';
import { MainLayout } from '@/components/MainLayout';

export default function Home() {
  const { loadSessions, loadSystemStatus, loadSettings } = useAppStore();

  useEffect(() => {
    loadSystemStatus();
    loadSettings();
    loadSessions();
  }, []);

  return (
    <div className="min-h-screen bg-fintech-darker">
      <MainLayout />
    </div>
  );
}
