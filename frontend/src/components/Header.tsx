import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import { ShieldCheck, AlertCircle, RefreshCw } from 'lucide-react';

export const Header: React.FC<{ title: string; subtitle?: string; actions?: React.ReactNode }> = ({
  title,
  subtitle,
  actions,
}) => {
  const { data: faultsData } = useQuery({
    queryKey: ['faults'],
    queryFn: api.getFaults,
    refetchInterval: 3000,
  });

  const activeFaults = faultsData?.active_faults || [];

  return (
    <header className="h-14 border-b border-border-subtle bg-bg-app/80 backdrop-blur px-6 flex items-center justify-between sticky top-0 z-20">
      <div>
        <h1 className="text-sm font-semibold text-text-primary tracking-tight">{title}</h1>
        {subtitle && <p className="text-[11px] text-text-secondary">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-3">
        {/* Active Fault Indicator */}
        {activeFaults.length > 0 ? (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-status-critical/10 border border-status-critical/30 text-status-critical text-xs font-mono">
            <AlertCircle size={14} />
            <span>{activeFaults.length} Fault Injected</span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-status-success/10 border border-status-success/20 text-status-success text-[11px] font-mono">
            <ShieldCheck size={13} />
            <span>Normal Baseline</span>
          </div>
        )}

        {actions}
      </div>
    </header>
  );
};
