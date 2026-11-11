import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import { AlertCircle, CheckCircle } from 'lucide-react';

export const Header: React.FC<{
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}> = ({ title, subtitle, actions }) => {
  const { data: faultsData } = useQuery({
    queryKey: ['faults'],
    queryFn: api.getFaults,
    refetchInterval: 3000,
  });

  const activeFaults = faultsData?.active_faults || [];

  return (
    <header className="h-12 border-b border-border-subtle bg-bg-app px-6 flex items-center justify-between sticky top-0 z-20">
      <div className="flex items-center gap-3">
        <h1 className="text-xs font-semibold text-text-primary tracking-tight">{title}</h1>
        {subtitle && (
          <>
            <span className="text-border-primary text-xs">/</span>
            <span className="text-[11px] text-text-muted">{subtitle}</span>
          </>
        )}
      </div>

      <div className="flex items-center gap-3">
        {/* Status indicator */}
        {activeFaults.length > 0 ? (
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-sm bg-status-coral/10 border border-status-coral/25 text-status-coral text-[11px] font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-status-coral" />
            <span>{activeFaults.length} Active Fault Injected</span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-sm bg-bg-surface border border-border-subtle text-text-secondary text-[11px] font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-status-sage" />
            <span>Baseline Operational</span>
          </div>
        )}

        {actions}
      </div>
    </header>
  );
};
