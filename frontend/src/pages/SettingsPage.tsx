import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { Header } from '../components/Header';
import {
  Settings,
  ShieldCheck,
  CheckCircle2,
  Database,
  Sliders,
  Server,
  Zap,
} from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [trafficRps, setTrafficRps] = useState<number>(10);

  const { data: settingsData, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: api.getSettings,
  });

  const { data: trafficData } = useQuery({
    queryKey: ['traffic'],
    queryFn: api.getTraffic,
    select: (data) => {
      if (data?.target_rps && trafficRps === 10) {
        setTrafficRps(data.target_rps);
      }
      return data;
    },
  });

  const trafficMutation = useMutation({
    mutationFn: (rps: number) => api.updateTraffic(rps),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['traffic'] });
    },
  });

  const gemini = settingsData?.gemini;
  const obs = settingsData?.observability;
  const db = settingsData?.database;
  const safety = settingsData?.safety;

  return (
    <div className="flex-1 flex flex-col">
      <Header
        title="Platform Settings & Integration Status"
        subtitle="Manage LLM configuration, simulator traffic throughput, observability endpoints, and safety gates"
      />

      <div className="p-6 space-y-6 max-w-4xl">
        {/* Gemini API Card */}
        <div className="bg-bg-surface border border-border-subtle rounded-md p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-border-subtle">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded bg-accent/20 flex items-center justify-center text-accent">
                <Zap size={14} />
              </div>
              <div>
                <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                  Google Gemini Provider Configuration
                </h3>
                <span className="text-[11px] text-text-muted">Strict LLM Provider (No fallback providers allowed)</span>
              </div>
            </div>
            <span
              className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold ${
                gemini?.configured
                  ? 'bg-status-success/20 text-status-success'
                  : 'bg-status-warning/20 text-status-warning'
              }`}
            >
              {gemini?.configured ? 'API KEY CONFIGURED' : 'MISSING KEY'}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-4 text-xs font-mono">
            <div className="p-3 bg-bg-raised rounded border border-border-subtle">
              <span className="text-[10px] text-text-muted block">Target Model Identifier</span>
              <span className="text-sm font-bold text-accent">{gemini?.model_identifier || 'gemini-3.5-flash-lite'}</span>
            </div>
            <div className="p-3 bg-bg-raised rounded border border-border-subtle">
              <span className="text-[10px] text-text-muted block">API Key Status</span>
              <span className="text-sm font-bold text-text-primary">{gemini?.masked_key || 'Configured via .env'}</span>
            </div>
          </div>

          <p className="text-[11px] text-text-secondary leading-relaxed">
            All incident investigation hypotheses and remediation synthesis run strictly through Google Gen AI SDK
            using <code className="text-accent">gemini-3.5-flash-lite</code> with structured Pydantic schema validation.
          </p>
        </div>

        {/* Simulator Traffic Controller */}
        <div className="bg-bg-surface border border-border-subtle rounded-md p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-border-subtle">
            <div className="flex items-center gap-2">
              <Sliders size={15} className="text-accent" />
              <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                Microservice Simulator Traffic Generator
              </h3>
            </div>
            <span className="text-xs font-mono text-status-success font-semibold">
              RUNNING ({trafficRps} RPS)
            </span>
          </div>

          <div className="space-y-3">
            <div className="flex justify-between text-xs font-mono">
              <span className="text-text-secondary">Simulated Fleet Traffic Rate:</span>
              <span className="text-accent font-bold">{trafficRps} Requests / Second</span>
            </div>
            <input
              type="range"
              min="1"
              max="50"
              step="1"
              value={trafficRps}
              onChange={(e) => setTrafficRps(parseInt(e.target.value))}
              onMouseUp={() => trafficMutation.mutate(trafficRps)}
              className="w-full accent-accent cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-text-muted font-mono">
              <span>1 RPS (Low idle)</span>
              <span>25 RPS (Normal operational)</span>
              <span>50 RPS (High load)</span>
            </div>
          </div>
        </div>

        {/* Safety Gate Settings */}
        <div className="bg-bg-surface border border-border-subtle rounded-md p-5 space-y-3">
          <div className="flex items-center gap-2 pb-3 border-b border-border-subtle">
            <ShieldCheck size={16} className="text-status-success" />
            <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
              Autonomous Remediation Safety Policies
            </h3>
          </div>

          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between py-1.5 border-b border-border-subtle/50">
              <span className="text-text-secondary">Human-in-the-Loop Approval Requirement:</span>
              <span className="font-mono text-status-success font-bold">MANDATORY (Enforced)</span>
            </div>
            <div className="flex items-center justify-between py-1.5 border-b border-border-subtle/50">
              <span className="text-text-secondary">Arbitrary Shell / Code Execution:</span>
              <span className="font-mono text-status-critical font-bold">BLOCKED (Disabled)</span>
            </div>
            <div className="flex items-center justify-between py-1.5">
              <span className="text-text-secondary">Permitted Remediation Actions:</span>
              <span className="font-mono text-text-primary text-[11px]">
                RESTART_SERVICE, RESET_CONNECTION_POOL, ROLLBACK_DEPLOYMENT
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
