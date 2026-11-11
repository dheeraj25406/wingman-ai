import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { Header } from '../components/Header';
import { ShieldCheck, Zap } from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [trafficRps, setTrafficRps] = useState<number>(10);

  const { data: settingsData } = useQuery({
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
    <div className="flex-1 flex flex-col font-sans">
      <Header
        title="Settings & System Configuration"
        subtitle="LLM provider credentials, simulator throughput, and safety policies"
      />

      <div className="p-6 space-y-6 max-w-4xl mx-auto w-full">
        {/* Gemini Provider Status Strip */}
        <section className="border border-border-subtle bg-bg-surface rounded-sm p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-border-subtle">
            <div>
              <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider font-mono">
                Google Gemini API Provider
              </h3>
              <span className="text-[11px] text-text-muted">Strict LLM Provider (google-genai SDK)</span>
            </div>
            <span
              className={`text-[10px] font-mono px-2 py-0.5 rounded-sm uppercase ${
                gemini?.configured
                  ? 'text-status-sage bg-status-sage/10 border border-status-sage/20'
                  : 'text-status-amber bg-status-amber/10 border border-status-amber/20'
              }`}
            >
              {gemini?.configured ? 'Active' : 'Unconfigured'}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-4 text-xs font-mono">
            <div className="p-3 bg-bg-raised rounded-sm border border-border-subtle">
              <span className="text-[10px] uppercase text-text-muted block">Target Model Identifier</span>
              <span className="text-xs font-medium text-text-primary mt-1 block">
                {gemini?.model_identifier || 'gemini-3.5-flash-lite'}
              </span>
            </div>
            <div className="p-3 bg-bg-raised rounded-sm border border-border-subtle">
              <span className="text-[10px] uppercase text-text-muted block">API Key Credential Status</span>
              <span className="text-xs font-medium text-text-primary mt-1 block">
                {gemini?.masked_key || 'Configured via .env'}
              </span>
            </div>
          </div>

          <p className="text-[11px] text-text-secondary leading-relaxed">
            All incident investigations, hypothesis reasoning, and remediation proposals are structured with Pydantic schemas
            and parsed via <code className="text-text-primary font-mono">gemini-3.5-flash-lite</code>.
          </p>
        </section>

        {/* Traffic Generator Controller */}
        <section className="border border-border-subtle bg-bg-surface rounded-sm p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-border-subtle">
            <span className="text-xs font-medium text-text-primary uppercase tracking-wider font-mono">
              Simulator Background Traffic Rate
            </span>
            <span className="text-xs font-mono text-status-sage">
              Active ({trafficRps} RPS)
            </span>
          </div>

          <div className="space-y-3">
            <div className="flex justify-between text-xs font-mono">
              <span className="text-text-muted">Fleet Throughput:</span>
              <span className="text-text-primary font-medium">{trafficRps} Requests / Second</span>
            </div>
            <input
              type="range"
              min="1"
              max="50"
              step="1"
              value={trafficRps}
              onChange={(e) => setTrafficRps(parseInt(e.target.value))}
              onMouseUp={() => trafficMutation.mutate(trafficRps)}
              className="w-full accent-text-primary cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-text-muted font-mono">
              <span>1 RPS (Idle)</span>
              <span>25 RPS (Nominal)</span>
              <span>50 RPS (Peak load)</span>
            </div>
          </div>
        </section>

        {/* Safety Policies */}
        <section className="border border-border-subtle bg-bg-surface rounded-sm p-5 space-y-3">
          <div className="pb-3 border-b border-border-subtle">
            <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider font-mono">
              Autonomous Remediation Safety Boundaries
            </h3>
          </div>

          <div className="space-y-2 text-xs font-mono">
            <div className="flex items-center justify-between py-1.5 border-b border-border-subtle">
              <span className="text-text-muted">Human Operator Approval Gate:</span>
              <span className="text-status-sage font-medium">MANDATORY (Enforced)</span>
            </div>
            <div className="flex items-center justify-between py-1.5 border-b border-border-subtle">
              <span className="text-text-muted">Arbitrary Terminal / Shell Execution:</span>
              <span className="text-status-coral font-medium">DISABLED (Zero Arbitrary Execution)</span>
            </div>
            <div className="flex items-center justify-between py-1.5">
              <span className="text-text-muted">Permitted Remediation Functions:</span>
              <span className="text-text-secondary text-[11px]">
                RESTART_SERVICE, RESET_CONNECTION_POOL, ROLLBACK_DEPLOYMENT
              </span>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};
