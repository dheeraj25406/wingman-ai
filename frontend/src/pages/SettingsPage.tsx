import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { Header } from '../components/Header';
import {
  Sparkles,
  Zap,
  ShieldCheck,
  Activity,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Play,
  Pause,
  Key,
  Database,
  Radio,
  Server,
  RefreshCw,
} from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const queryClient = useQueryClient();

  // Traffic rate state
  const [trafficRps, setTrafficRps] = useState<number>(10);
  const [trafficFeedback, setTrafficFeedback] = useState<string | null>(null);

  // Gemini API key edit state
  const [showKeyInput, setShowKeyInput] = useState<boolean>(false);
  const [newApiKey, setNewApiKey] = useState<string>('');
  const [keyFeedback, setKeyFeedback] = useState<{ ok: boolean; msg: string } | null>(null);

  // Gemini test connection state
  const [testResult, setTestResult] = useState<{ ok: boolean; latency?: number; msg: string } | null>(null);

  // Safety settings local state
  const [humanApproval, setHumanApproval] = useState<boolean>(true);
  const [maxRemediations, setMaxRemediations] = useState<number>(10);
  const [allowedActions, setAllowedActions] = useState<string[]>([
    'RESTART_SERVICE',
    'RESET_CONNECTION_POOL',
    'ROLLBACK_DEPLOYMENT',
    'THROTTLE_TRAFFIC',
    'DRAIN_QUEUE',
  ]);
  const [safetyFeedback, setSafetyFeedback] = useState<string | null>(null);

  // Reset demo feedback
  const [resetFeedback, setResetFeedback] = useState<string | null>(null);

  // Queries
  const { data: settingsData, isLoading: loadingSettings } = useQuery({
    queryKey: ['settings'],
    queryFn: api.getSettings,
    refetchInterval: 10000,
  });

  const { data: trafficData } = useQuery({
    queryKey: ['traffic'],
    queryFn: api.getTraffic,
    refetchInterval: 3000,
  });

  const { data: safetyData } = useQuery({
    queryKey: ['safety'],
    queryFn: api.getSafety,
  });

  const { data: diagnosticsData, isFetching: fetchingDiagnostics, refetch: refetchDiagnostics } = useQuery({
    queryKey: ['diagnostics'],
    queryFn: api.getDiagnostics,
  });

  // Sync trafficRps when query succeeds and not actively editing
  useEffect(() => {
    if (trafficData?.target_rps !== undefined) {
      setTrafficRps(trafficData.target_rps);
    }
  }, [trafficData?.target_rps]);

  // Sync safety settings
  useEffect(() => {
    if (safetyData) {
      if (safetyData.human_approval_required !== undefined) {
        setHumanApproval(safetyData.human_approval_required);
      }
      if (safetyData.max_remediations_per_hour !== undefined) {
        setMaxRemediations(safetyData.max_remediations_per_hour);
      }
      if (safetyData.allowed_actions) {
        setAllowedActions(safetyData.allowed_actions);
      }
    }
  }, [safetyData]);

  // Mutations
  const trafficMutation = useMutation({
    mutationFn: (rps: number) => api.updateTraffic(rps),
    onSuccess: (data: any) => {
      queryClient.invalidateQueries({ queryKey: ['traffic'] });
      setTrafficFeedback(`Updated throughput to ${trafficRps} RPS`);
      setTimeout(() => setTrafficFeedback(null), 3500);
    },
  });

  const toggleTrafficMutation = useMutation({
    mutationFn: api.toggleTraffic,
    onSuccess: (data: any) => {
      queryClient.invalidateQueries({ queryKey: ['traffic'] });
      queryClient.invalidateQueries({ queryKey: ['diagnostics'] });
      setTrafficFeedback(data?.message || 'Updated generator state');
      setTimeout(() => setTrafficFeedback(null), 3500);
    },
  });

  const testGeminiMutation = useMutation({
    mutationFn: api.testGemini,
    onSuccess: (data: any) => {
      if (data?.data?.ok) {
        setTestResult({
          ok: true,
          latency: data.data.latency_ms,
          msg: `Live ping verified in ${data.data.latency_ms} ms (${data.data.model})`,
        });
      } else {
        setTestResult({
          ok: false,
          msg: data?.message || 'Gemini connectivity failed',
        });
      }
    },
    onError: (err: any) => {
      setTestResult({
        ok: false,
        msg: err?.message || 'Gemini connection test failed',
      });
    },
  });

  const keyMutation = useMutation({
    mutationFn: (key: string) => api.updateApiKey(key),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
      queryClient.invalidateQueries({ queryKey: ['diagnostics'] });
      setKeyFeedback({ ok: true, msg: 'Gemini API key updated and verified successfully.' });
      setNewApiKey('');
      setShowKeyInput(false);
      setTimeout(() => setKeyFeedback(null), 4000);
    },
    onError: (err: any) => {
      setKeyFeedback({ ok: false, msg: err?.message || 'Failed to update API key.' });
    },
  });

  const safetyMutation = useMutation({
    mutationFn: (cfg: any) => api.updateSafety(cfg),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['safety'] });
      setSafetyFeedback('Safety boundaries successfully saved.');
      setTimeout(() => setSafetyFeedback(null), 3500);
    },
  });

  const resetDemoMutation = useMutation({
    mutationFn: api.resetDemo,
    onSuccess: (data: any) => {
      queryClient.invalidateQueries();
      setResetFeedback(data?.message || 'Demo environment reset to baseline.');
      setTimeout(() => setResetFeedback(null), 4500);
    },
  });

  const gemini = settingsData?.gemini;
  const obs = settingsData?.observability;
  const db = settingsData?.database;
  const isTrafficRunning = trafficData?.running ?? true;

  const handleActionToggle = (action: string) => {
    if (allowedActions.includes(action)) {
      setAllowedActions(allowedActions.filter((a) => a !== action));
    } else {
      setAllowedActions([...allowedActions, action]);
    }
  };

  return (
    <div className="flex-1 flex flex-col font-sans">
      <Header
        title="Settings & System Configuration"
        subtitle="LLM provider credentials, simulator throughput, safety policies, and system diagnostics"
        actions={
          <button
            onClick={() => resetDemoMutation.mutate()}
            disabled={resetDemoMutation.isPending}
            className="flex items-center gap-1.5 px-3 py-1 rounded-sm bg-bg-surface border border-border-primary text-text-primary text-xs font-mono hover:bg-bg-hover transition-colors disabled:opacity-50"
            title="Clear all injected faults, reset simulator to 10 RPS, and re-arm baseline metrics"
          >
            <RotateCcw size={12} className={resetDemoMutation.isPending ? 'animate-spin' : ''} />
            <span>{resetDemoMutation.isPending ? 'Resetting...' : 'Reset Demo State'}</span>
          </button>
        }
      />

      <div className="p-6 space-y-6 max-w-5xl mx-auto w-full">
        {/* Global Action Feedback Notification */}
        {resetFeedback && (
          <div className="px-4 py-2.5 rounded-sm bg-bg-surface border border-status-healthy text-status-healthy text-xs font-mono flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 size={14} />
              <span>{resetFeedback}</span>
            </div>
            <button onClick={() => setResetFeedback(null)} className="text-text-muted hover:text-text-primary">
              ✕
            </button>
          </div>
        )}

        {/* SECTION 1: Google Gemini API Provider */}
        <section className="border border-border-subtle bg-bg-surface rounded-sm p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-border-subtle">
            <div className="flex items-center gap-2.5">
              <Sparkles size={16} className="text-text-primary" />
              <div>
                <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider font-mono">
                  Google Gemini API Provider
                </h3>
                <span className="text-[11px] text-text-muted">
                  Strict LLM Provider (google-genai SDK · gemini-3.5-flash-lite)
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span
                className={`text-[10px] font-mono px-2 py-0.5 rounded-sm uppercase ${
                  gemini?.configured
                    ? 'text-status-healthy bg-status-healthy/10 border border-status-healthy/20'
                    : 'text-status-warning bg-status-warning/10 border border-status-warning/20'
                }`}
              >
                {gemini?.configured ? 'Active Provider' : 'Unconfigured'}
              </span>

              <button
                onClick={() => testGeminiMutation.mutate()}
                disabled={testGeminiMutation.isPending}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-sm bg-bg-raised border border-border-primary text-text-primary text-xs font-mono hover:bg-bg-hover transition-colors disabled:opacity-50"
              >
                <Zap size={11} className={testGeminiMutation.isPending ? 'animate-pulse text-status-warning' : ''} />
                <span>{testGeminiMutation.isPending ? 'Testing...' : 'Test Connection'}</span>
              </button>
            </div>
          </div>

          {/* Test connection result pill */}
          {testResult && (
            <div
              className={`p-3 rounded-sm border text-xs font-mono flex items-center justify-between ${
                testResult.ok
                  ? 'bg-status-healthy/10 border-status-healthy/30 text-status-healthy'
                  : 'bg-status-critical/10 border-status-critical/30 text-status-critical'
              }`}
            >
              <div className="flex items-center gap-2">
                {testResult.ok ? <CheckCircle2 size={13} /> : <AlertTriangle size={13} />}
                <span>{testResult.msg}</span>
              </div>
              <button onClick={() => setTestResult(null)} className="opacity-60 hover:opacity-100">
                ✕
              </button>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs font-mono">
            <div className="p-3 bg-bg-raised rounded-sm border border-border-subtle">
              <span className="text-[10px] uppercase text-text-muted block">Enforced Model</span>
              <span className="text-xs font-semibold text-text-primary mt-1 block">
                {gemini?.model_identifier || 'gemini-3.5-flash-lite'}
              </span>
            </div>

            <div className="p-3 bg-bg-raised rounded-sm border border-border-subtle">
              <span className="text-[10px] uppercase text-text-muted block">API Key Status</span>
              <div className="flex items-center justify-between mt-1">
                <span className="text-xs font-medium text-text-primary">
                  {gemini?.masked_key || 'Configured via .env'}
                </span>
                <button
                  onClick={() => setShowKeyInput(!showKeyInput)}
                  className="text-[10px] text-text-muted hover:text-text-primary underline ml-2"
                >
                  {showKeyInput ? 'Cancel' : 'Change'}
                </button>
              </div>
            </div>

            <div className="p-3 bg-bg-raised rounded-sm border border-border-subtle">
              <span className="text-[10px] uppercase text-text-muted block">SDK Client</span>
              <span className="text-xs font-medium text-text-primary mt-1 block">
                {gemini?.provider || 'Google Gen AI SDK'}
              </span>
            </div>
          </div>

          {/* Expandable API Key updater */}
          {showKeyInput && (
            <div className="p-4 bg-bg-raised border border-border-primary rounded-sm space-y-3">
              <div className="flex items-center gap-2">
                <Key size={13} className="text-text-muted" />
                <span className="text-xs font-mono text-text-primary font-medium">Update Gemini API Key</span>
              </div>
              <div className="flex gap-2">
                <input
                  type="password"
                  placeholder="Enter Gemini API key (e.g. your-api-key)"
                  value={newApiKey}
                  onChange={(e) => setNewApiKey(e.target.value)}
                  className="flex-1 bg-bg-surface border border-border-subtle rounded-sm px-3 py-1.5 text-xs text-text-primary font-mono focus:outline-none focus:border-border-strong"
                />
                <button
                  onClick={() => keyMutation.mutate(newApiKey)}
                  disabled={keyMutation.isPending || newApiKey.length < 10}
                  className="px-3 py-1.5 rounded-sm bg-text-primary text-bg-app text-xs font-medium hover:bg-white transition-colors disabled:opacity-50 font-mono"
                >
                  {keyMutation.isPending ? 'Verifying...' : 'Save & Verify'}
                </button>
              </div>
              <span className="text-[10px] text-text-muted block">
                Your key will be validated against <code className="text-text-secondary">gemini-3.5-flash-lite</code> before being committed to memory.
              </span>
            </div>
          )}

          {keyFeedback && (
            <div
              className={`p-2.5 rounded-sm border text-xs font-mono ${
                keyFeedback.ok
                  ? 'bg-status-healthy/10 border-status-healthy/30 text-status-healthy'
                  : 'bg-status-critical/10 border-status-critical/30 text-status-critical'
              }`}
            >
              {keyFeedback.msg}
            </div>
          )}
        </section>

        {/* SECTION 2: Simulator Background Traffic Throughput */}
        <section className="border border-border-subtle bg-bg-surface rounded-sm p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-border-subtle">
            <div className="flex items-center gap-2.5">
              <Activity size={16} className="text-text-primary" />
              <div>
                <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider font-mono">
                  Simulator Traffic Rate Controller
                </h3>
                <span className="text-[11px] text-text-muted">
                  Synthetic microservice traffic generator for 6 communicating services
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span
                className={`text-[10px] font-mono px-2 py-0.5 rounded-sm uppercase ${
                  isTrafficRunning
                    ? 'text-status-healthy bg-status-healthy/10 border border-status-healthy/20'
                    : 'text-text-muted bg-bg-raised border border-border-subtle'
                }`}
              >
                {isTrafficRunning ? `Active (${trafficRps} RPS)` : 'Paused'}
              </span>

              <button
                onClick={() => toggleTrafficMutation.mutate()}
                disabled={toggleTrafficMutation.isPending}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-sm bg-bg-raised border border-border-primary text-text-primary text-xs font-mono hover:bg-bg-hover transition-colors disabled:opacity-50"
              >
                {isTrafficRunning ? <Pause size={11} /> : <Play size={11} />}
                <span>{isTrafficRunning ? 'Pause Generator' : 'Resume Generator'}</span>
              </button>
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex justify-between items-center text-xs font-mono">
              <span className="text-text-muted">Target Throughput:</span>
              <div className="flex items-center gap-2">
                <span className="text-text-primary font-bold text-sm">{trafficRps}</span>
                <span className="text-text-muted">Requests / Second</span>
              </div>
            </div>

            <input
              type="range"
              min="1"
              max="50"
              step="1"
              value={trafficRps}
              onChange={(e) => setTrafficRps(parseInt(e.target.value))}
              className="w-full accent-text-primary cursor-pointer h-1.5 bg-bg-raised rounded-sm"
            />

            <div className="flex justify-between text-[10px] text-text-muted font-mono">
              <span>1 RPS (Idle)</span>
              <span>10 RPS (Default)</span>
              <span>25 RPS (Nominal)</span>
              <span>50 RPS (Stress)</span>
            </div>

            {/* Quick preset selector buttons & Apply button */}
            <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-border-subtle">
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] font-mono text-text-muted mr-1">Presets:</span>
                {[1, 5, 10, 25, 50].map((rpsVal) => (
                  <button
                    key={rpsVal}
                    onClick={() => {
                      setTrafficRps(rpsVal);
                      trafficMutation.mutate(rpsVal);
                    }}
                    className={`px-2 py-0.5 rounded-sm text-[11px] font-mono border transition-colors ${
                      trafficRps === rpsVal
                        ? 'bg-bg-raised text-text-primary border-border-strong font-bold'
                        : 'bg-bg-surface text-text-muted border-border-subtle hover:text-text-primary hover:border-border-primary'
                    }`}
                  >
                    {rpsVal} RPS
                  </button>
                ))}
              </div>

              <button
                onClick={() => trafficMutation.mutate(trafficRps)}
                disabled={trafficMutation.isPending}
                className="px-3 py-1 rounded-sm bg-text-primary text-bg-app text-xs font-medium hover:bg-white transition-colors disabled:opacity-50 font-mono"
              >
                {trafficMutation.isPending ? 'Applying...' : 'Apply Rate'}
              </button>
            </div>

            {trafficFeedback && (
              <div className="p-2.5 rounded-sm bg-status-healthy/10 border border-status-healthy/30 text-status-healthy text-xs font-mono flex items-center gap-2">
                <CheckCircle2 size={13} />
                <span>{trafficFeedback}</span>
              </div>
            )}
          </div>
        </section>

        {/* SECTION 3: Autonomous Remediation Safety Boundaries */}
        <section className="border border-border-subtle bg-bg-surface rounded-sm p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-border-subtle">
            <div className="flex items-center gap-2.5">
              <ShieldCheck size={16} className="text-text-primary" />
              <div>
                <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider font-mono">
                  Autonomous Remediation Safety Boundaries
                </h3>
                <span className="text-[11px] text-text-muted">
                  Human-in-the-loop gates and permitted action types
                </span>
              </div>
            </div>

            <button
              onClick={() =>
                safetyMutation.mutate({
                  human_approval_required: humanApproval,
                  max_remediations_per_hour: maxRemediations,
                  allowed_actions: allowedActions,
                })
              }
              disabled={safetyMutation.isPending}
              className="px-3 py-1 rounded-sm bg-text-primary text-bg-app text-xs font-medium hover:bg-white transition-colors disabled:opacity-50 font-mono"
            >
              {safetyMutation.isPending ? 'Saving...' : 'Save Safety Policies'}
            </button>
          </div>

          {safetyFeedback && (
            <div className="p-2.5 rounded-sm bg-status-healthy/10 border border-status-healthy/30 text-status-healthy text-xs font-mono flex items-center gap-2">
              <CheckCircle2 size={13} />
              <span>{safetyFeedback}</span>
            </div>
          )}

          <div className="space-y-4 text-xs font-mono">
            {/* Human Gate */}
            <div className="flex items-center justify-between py-2 border-b border-border-subtle">
              <div>
                <span className="text-text-primary font-medium block">Human Operator Approval Gate</span>
                <span className="text-[11px] text-text-muted block mt-0.5">
                  Requires explicit operator signature before executing any LangGraph remediation plan
                </span>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={humanApproval}
                  onChange={(e) => setHumanApproval(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-9 h-5 bg-bg-raised peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-text-primary after:border-border-subtle after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-status-healthy"></div>
              </label>
            </div>

            {/* Terminal execution block */}
            <div className="flex items-center justify-between py-2 border-b border-border-subtle">
              <div>
                <span className="text-text-primary font-medium block">Arbitrary Terminal / Shell Execution</span>
                <span className="text-[11px] text-text-muted block mt-0.5">
                  Prohibits execution of unvetted bash commands, raw scripts, or terminal shells
                </span>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded-sm bg-status-critical/10 text-status-critical border border-status-critical/20 font-bold uppercase">
                Zero Shell Execution Allowed
              </span>
            </div>

            {/* Max Remediations Rate */}
            <div className="flex items-center justify-between py-2 border-b border-border-subtle">
              <div>
                <span className="text-text-primary font-medium block">Rate-Limit: Max Remediations Per Hour</span>
                <span className="text-[11px] text-text-muted block mt-0.5">
                  Prevents runaway remediation loops during cascading cluster faults
                </span>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min="1"
                  max="50"
                  value={maxRemediations}
                  onChange={(e) => setMaxRemediations(parseInt(e.target.value) || 10)}
                  className="w-16 bg-bg-raised border border-border-subtle rounded-sm px-2 py-1 text-xs text-text-primary font-mono text-center focus:outline-none"
                />
                <span className="text-text-muted text-[11px]">actions / hr</span>
              </div>
            </div>

            {/* Allowed actions checklist */}
            <div className="pt-2 space-y-2">
              <span className="text-[11px] uppercase text-text-muted block">Permitted Action Catalog:</span>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
                {[
                  { id: 'RESTART_SERVICE', label: 'Restart Microservice Container' },
                  { id: 'RESET_CONNECTION_POOL', label: 'Flush DB Connection Pool' },
                  { id: 'ROLLBACK_DEPLOYMENT', label: 'Rollback Deployment Release' },
                  { id: 'THROTTLE_TRAFFIC', label: 'Apply Ingress Rate-Limiting' },
                  { id: 'DRAIN_QUEUE', label: 'Drain Dead-Letter Queue' },
                ].map((act) => {
                  const checked = allowedActions.includes(act.id);
                  return (
                    <button
                      key={act.id}
                      type="button"
                      onClick={() => handleActionToggle(act.id)}
                      className={`p-2.5 rounded-sm border text-left flex items-start gap-2 transition-colors ${
                        checked
                          ? 'bg-bg-raised border-border-primary text-text-primary'
                          : 'bg-bg-surface border-border-subtle text-text-disabled'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => {}}
                        className="mt-0.5 accent-text-primary pointer-events-none"
                      />
                      <div>
                        <span className="text-xs font-semibold block">{act.id}</span>
                        <span className="text-[10px] text-text-muted block">{act.label}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </section>

        {/* SECTION 4: Subsystem Diagnostics & Health Workstation */}
        <section className="border border-border-subtle bg-bg-surface rounded-sm p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-border-subtle">
            <div className="flex items-center gap-2.5">
              <Server size={16} className="text-text-primary" />
              <div>
                <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider font-mono">
                  Subsystem Health & System Diagnostics
                </h3>
                <span className="text-[11px] text-text-muted">
                  Live verification of DB, ML models, LangGraph agent, and service mesh
                </span>
              </div>
            </div>

            <button
              onClick={() => refetchDiagnostics()}
              disabled={fetchingDiagnostics}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-sm bg-bg-raised border border-border-primary text-text-primary text-xs font-mono hover:bg-bg-hover transition-colors disabled:opacity-50"
            >
              <RefreshCw size={11} className={fetchingDiagnostics ? 'animate-spin' : ''} />
              <span>{fetchingDiagnostics ? 'Checking...' : 'Refresh Diagnostics'}</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
            {(diagnosticsData?.subsystems || []).map((sub: any, idx: number) => {
              const isHealthy = sub.status === 'HEALTHY';
              const isDegraded = sub.status === 'DEGRADED';
              return (
                <div key={idx} className="p-3 bg-bg-raised rounded-sm border border-border-subtle flex items-start justify-between">
                  <div>
                    <span className="text-xs font-medium text-text-primary block">{sub.name}</span>
                    <span className="text-[10px] text-text-muted block mt-0.5">{sub.details}</span>
                  </div>
                  <span
                    className={`text-[9px] uppercase px-1.5 py-0.5 rounded-sm font-semibold shrink-0 ml-2 ${
                      isHealthy
                        ? 'text-status-healthy bg-status-healthy/10 border border-status-healthy/20'
                        : isDegraded
                        ? 'text-status-critical bg-status-critical/10 border border-status-critical/20'
                        : 'text-status-warning bg-status-warning/10 border border-status-warning/20'
                    }`}
                  >
                    {sub.status}
                  </span>
                </div>
              );
            })}
          </div>
        </section>

        {/* SECTION 5: Infrastructure & Observability Endpoints */}
        <section className="border border-border-subtle bg-bg-surface rounded-sm p-5 space-y-3">
          <div className="pb-3 border-b border-border-subtle flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Radio size={14} className="text-text-muted" />
              <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider font-mono">
                Observability & Database Integrations
              </h3>
            </div>
            <span className="text-[10px] font-mono text-text-muted">Distributed telemetry connectors</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
            <div className="p-3 bg-bg-raised rounded-sm border border-border-subtle">
              <span className="text-[10px] uppercase text-text-muted block">Prometheus (Metrics)</span>
              <span className="text-[11px] text-text-primary mt-1 block truncate">
                {obs?.prometheus_url || 'http://localhost:9090'}
              </span>
            </div>
            <div className="p-3 bg-bg-raised rounded-sm border border-border-subtle">
              <span className="text-[10px] uppercase text-text-muted block">Loki (Logs)</span>
              <span className="text-[11px] text-text-primary mt-1 block truncate">
                {obs?.loki_url || 'http://localhost:3100'}
              </span>
            </div>
            <div className="p-3 bg-bg-raised rounded-sm border border-border-subtle">
              <span className="text-[10px] uppercase text-text-muted block">Tempo (Traces)</span>
              <span className="text-[11px] text-text-primary mt-1 block truncate">
                {obs?.tempo_url || 'http://localhost:3200'}
              </span>
            </div>
            <div className="p-3 bg-bg-raised rounded-sm border border-border-subtle">
              <span className="text-[10px] uppercase text-text-muted block">Database URI</span>
              <span className="text-[11px] text-text-primary mt-1 block truncate">
                {db?.database_url || 'sqlite+aiosqlite:///wingman.db'}
              </span>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};
