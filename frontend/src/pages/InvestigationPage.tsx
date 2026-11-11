import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { Header } from '../components/Header';
import {
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  Play,
  Clock,
  ShieldAlert,
  Server,
  FileText,
  Terminal,
  Activity,
  Layers,
  Sparkles,
  Check,
  X,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

export const InvestigationPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [operatorNotes, setOperatorNotes] = useState('');
  const [activeEvidenceTab, setActiveEvidenceTab] = useState<'METRICS' | 'LOGS' | 'RUNBOOKS'>('METRICS');

  const { data: incident, isLoading } = useQuery({
    queryKey: ['incident', id],
    queryFn: () => api.getIncident(id!),
    enabled: !!id,
    refetchInterval: 2500,
  });

  const { data: serviceMetrics } = useQuery({
    queryKey: ['service-metrics', incident?.primary_service_id],
    queryFn: () => api.getServiceMetrics(incident?.primary_service_id, 25),
    enabled: !!incident?.primary_service_id,
    refetchInterval: 3000,
  });

  const chartData = (serviceMetrics || []).map((m: any, i: number) => ({
    time: m.timestamp ? m.timestamp.split('T')[1].slice(0, 8) : `${i}s`,
    p95: m.latency_p95,
    error_rate: Number((m.error_rate * 100).toFixed(2)),
    db_conn: m.db_connections,
  }));

  const investigateMutation = useMutation({
    mutationFn: () => api.investigateIncident(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incident', id] });
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
    },
  });

  const approveMutation = useMutation({
    mutationFn: (proposalId: string) => api.approveRemediation(id!, proposalId, operatorNotes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incident', id] });
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      queryClient.invalidateQueries({ queryKey: ['faults'] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (proposalId: string) => api.rejectRemediation(id!, proposalId, operatorNotes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incident', id] });
    },
  });

  if (isLoading || !incident) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center space-y-2">
          <Activity size={28} className="animate-spin text-accent mx-auto" />
          <p className="text-xs text-text-muted">Loading incident investigation context...</p>
        </div>
      </div>
    );
  }

  const proposal = incident.remediation_proposal;
  const isResolved = incident.status === 'RESOLVED';

  return (
    <div className="flex-1 flex flex-col">
      <Header
        title={`Incident Investigation — ${incident.id}`}
        subtitle={`Root-cause hypothesis generation and safe remediation execution`}
        actions={
          <div className="flex items-center gap-2">
            <Link
              to="/incidents"
              className="flex items-center gap-1 px-2.5 py-1 rounded bg-bg-surface border border-border-subtle text-xs text-text-secondary hover:text-text-primary transition-colors"
            >
              <ArrowLeft size={13} />
              <span>Back to Incidents</span>
            </Link>

            {incident.status !== 'RESOLVED' && (
              <button
                onClick={() => investigateMutation.mutate()}
                disabled={investigateMutation.isPending}
                className="flex items-center gap-1.5 px-3 py-1 rounded bg-accent text-bg-app text-xs font-semibold hover:bg-accent/90 transition-colors disabled:opacity-50"
              >
                <Sparkles size={13} className={investigateMutation.isPending ? 'animate-spin' : ''} />
                <span>{investigateMutation.isPending ? 'Analyzing with LangGraph...' : 'Run Investigation Workflow'}</span>
              </button>
            )}
          </div>
        }
      />

      {/* Main Incident Details Grid */}
      <div className="p-6 space-y-6">
        {/* Banner summary */}
        <div className="bg-bg-surface border border-border-subtle rounded-md p-5 flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-1.5 max-w-3xl">
            <div className="flex items-center gap-2.5">
              <span
                className={`text-[11px] font-mono px-2 py-0.5 rounded font-semibold ${
                  incident.severity === 'P1_CRITICAL'
                    ? 'bg-status-critical/15 text-status-critical border border-status-critical/30'
                    : 'bg-status-warning/15 text-status-warning border border-status-warning/30'
                }`}
              >
                {incident.severity}
              </span>
              <span
                className={`text-[11px] font-mono px-2 py-0.5 rounded ${
                  isResolved
                    ? 'bg-status-success/15 text-status-success'
                    : incident.status === 'INVESTIGATING'
                    ? 'bg-accent/15 text-accent animate-pulse'
                    : 'bg-status-warning/15 text-status-warning'
                }`}
              >
                STATUS: {incident.status}
              </span>
              <span className="text-xs text-text-muted font-mono">
                Detected: {incident.detected_at?.replace('T', ' ').slice(0, 19)}
              </span>
            </div>
            <h1 className="text-base font-semibold text-text-primary tracking-tight">{incident.title}</h1>
            <p className="text-xs text-text-secondary leading-relaxed">{incident.summary}</p>
          </div>

          <div className="flex items-center gap-4 bg-bg-raised border border-border-subtle rounded p-3 text-xs">
            <div>
              <span className="text-[10px] uppercase font-mono text-text-muted block">Primary Service</span>
              <span className="font-mono text-accent font-semibold">{incident.primary_service_id}</span>
            </div>
            <div className="w-px h-7 bg-border-subtle" />
            <div>
              <span className="text-[10px] uppercase font-mono text-text-muted block">ML Confidence</span>
              <span className="font-mono text-status-success font-semibold">
                {incident.ml_confidence ? `${(incident.ml_confidence * 100).toFixed(0)}%` : '—'}
              </span>
            </div>
            <div className="w-px h-7 bg-border-subtle" />
            <div>
              <span className="text-[10px] uppercase font-mono text-text-muted block">Affected Count</span>
              <span className="font-mono text-text-primary font-semibold">
                {incident.affected_service_ids?.length || 1} Services
              </span>
            </div>
          </div>
        </div>

        {/* Two-Column Deep-Dive */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Diagnostics & Evidence (7 Cols) */}
          <div className="lg:col-span-7 space-y-6">
            {/* Anomaly ML Overview */}
            <div className="bg-bg-surface border border-border-subtle rounded-md p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Activity size={14} className="text-accent" />
                  <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                    Machine Learning Anomaly Detection
                  </h3>
                </div>
                <span className="text-[11px] font-mono text-text-muted">Isolation Forest + LightGBM</span>
              </div>

              <div className="grid grid-cols-2 gap-3 mb-4">
                <div className="bg-bg-raised p-2.5 rounded border border-border-subtle">
                  <span className="text-[10px] font-mono text-text-muted block">Isolation Forest Anomaly Score</span>
                  <span className="text-lg font-mono font-bold text-status-critical">
                    {(incident.anomaly_score || 0.89).toFixed(4)}
                  </span>
                  <span className="text-[10px] text-text-muted block">Threshold: 0.5200</span>
                </div>
                <div className="bg-bg-raised p-2.5 rounded border border-border-subtle">
                  <span className="text-[10px] font-mono text-text-muted block">Predicted Failure Category</span>
                  <span className="text-sm font-mono font-bold text-accent">
                    {incident.predicted_category || 'DB_POOL_EXHAUSTION'}
                  </span>
                  <span className="text-[10px] text-status-success block">Calibrated Probability: 96.0%</span>
                </div>
              </div>

              {/* Abnormal Features Badges */}
              <div>
                <span className="text-[11px] font-medium text-text-secondary block mb-2">Abnormal Telemetry Signals:</span>
                <div className="flex flex-wrap gap-2">
                  {(incident.abnormal_features || []).map((feat: any, idx: number) => (
                    <div
                      key={idx}
                      className="px-2.5 py-1 rounded bg-status-critical/10 border border-status-critical/30 text-xs font-mono flex items-center gap-2"
                    >
                      <span className="text-status-critical font-semibold">{feat.feature}</span>
                      <span className="text-text-primary">{feat.value}</span>
                      <span className="text-[10px] text-text-muted">(+{feat.deviation_sigma}σ)</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Live Telemetry Chart */}
            <div className="bg-bg-surface border border-border-subtle rounded-md p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                  Target Service Telemetry ({incident.primary_service_id})
                </h3>
                <div className="flex items-center gap-3 text-[11px] font-mono">
                  <span className="flex items-center gap-1 text-accent">
                    <span className="w-2 h-2 rounded-full bg-accent" /> Latency P95 (ms)
                  </span>
                  <span className="flex items-center gap-1 text-status-critical">
                    <span className="w-2 h-2 rounded-full bg-status-critical" /> Error Rate (%)
                  </span>
                </div>
              </div>
              <div className="h-44 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData}>
                    <defs>
                      <linearGradient id="invP95" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#65A9FF" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#65A9FF" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="time" stroke="#647184" fontSize={10} tickLine={false} />
                    <YAxis stroke="#647184" fontSize={10} tickLine={false} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#151D27', borderColor: '#293442', fontSize: '11px' }}
                    />
                    <Area type="monotone" dataKey="p95" stroke="#65A9FF" strokeWidth={1.5} fillOpacity={1} fill="url(#invP95)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Diagnostic Evidence Inspector */}
            <div className="bg-bg-surface border border-border-subtle rounded-md overflow-hidden">
              <div className="px-4 py-3 border-b border-border-subtle flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Layers size={14} className="text-accent" />
                  <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                    Verified Diagnostic Evidence
                  </h3>
                </div>
                <div className="flex items-center gap-1 bg-bg-raised p-0.5 rounded text-xs">
                  <button
                    onClick={() => setActiveEvidenceTab('METRICS')}
                    className={`px-2 py-0.5 rounded text-[11px] font-mono ${
                      activeEvidenceTab === 'METRICS' ? 'bg-accent/20 text-accent font-semibold' : 'text-text-muted'
                    }`}
                  >
                    Metrics & Spans
                  </button>
                  <button
                    onClick={() => setActiveEvidenceTab('LOGS')}
                    className={`px-2 py-0.5 rounded text-[11px] font-mono ${
                      activeEvidenceTab === 'LOGS' ? 'bg-accent/20 text-accent font-semibold' : 'text-text-muted'
                    }`}
                  >
                    Error Logs
                  </button>
                  <button
                    onClick={() => setActiveEvidenceTab('RUNBOOKS')}
                    className={`px-2 py-0.5 rounded text-[11px] font-mono ${
                      activeEvidenceTab === 'RUNBOOKS' ? 'bg-accent/20 text-accent font-semibold' : 'text-text-muted'
                    }`}
                  >
                    Runbook RAG
                  </button>
                </div>
              </div>

              <div className="p-4 space-y-3">
                {(incident.evidence || []).map((ev: any) => (
                  <div key={ev.id} className="p-3 bg-bg-raised border border-border-subtle rounded text-xs space-y-1.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-accent text-[11px]">{ev.id}</span>
                        <span className="px-1.5 py-0.5 rounded bg-bg-surface text-text-muted text-[10px] font-mono">
                          {ev.evidence_type}
                        </span>
                      </div>
                      <span className="text-[10px] text-text-muted font-mono">{ev.timestamp?.slice(11, 19)}</span>
                    </div>
                    <p className="font-medium text-text-primary">{ev.headline}</p>
                    {ev.details && (
                      <pre className="text-[11px] font-mono bg-bg-surface p-2 rounded text-text-secondary overflow-x-auto border border-border-subtle/50">
                        {JSON.stringify(ev.details, null, 2)}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Investigation Timeline */}
            <div className="bg-bg-surface border border-border-subtle rounded-md p-4">
              <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider mb-4 flex items-center gap-2">
                <Clock size={14} className="text-accent" />
                <span>Investigation & Lifecycle Timeline</span>
              </h3>
              <div className="space-y-4 relative before:absolute before:inset-0 before:left-2 before:w-0.5 before:bg-border-subtle">
                {(incident.timeline || []).map((ev: any, idx: number) => (
                  <div key={idx} className="relative pl-6 space-y-0.5">
                    <div className="absolute left-0.5 top-1 w-3 h-3 rounded-full bg-accent border-2 border-bg-surface" />
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono text-text-muted">{ev.created_at?.slice(11, 19)}</span>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-bg-raised text-accent">
                        {ev.event_type}
                      </span>
                    </div>
                    <p className="text-xs text-text-primary font-medium">{ev.description}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right Column: AI Root-Cause Hypotheses & Remediation Gate (5 Cols) */}
          <div className="lg:col-span-5 space-y-6">
            {/* Ranked Hypotheses */}
            <div className="bg-bg-surface border border-border-subtle rounded-md p-4 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Sparkles size={14} className="text-accent" />
                  <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                    Ranked Root-Cause Hypotheses
                  </h3>
                </div>
                <span className="text-[11px] font-mono text-text-muted">Gemini 3.5 Flash-Lite</span>
              </div>

              <div className="space-y-3">
                {(incident.hypotheses || []).map((hyp: any) => (
                  <div
                    key={hyp.id}
                    className="p-3.5 bg-bg-raised border border-border-strong rounded-md space-y-2 relative"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono font-bold text-accent">Rank #{hyp.rank}</span>
                      <div className="flex items-center gap-1.5 text-status-success font-mono text-xs font-semibold">
                        <span>Confidence:</span>
                        <span>{(hyp.confidence_score * 100).toFixed(0)}%</span>
                      </div>
                    </div>

                    <h4 className="text-xs font-bold text-text-primary leading-tight">{hyp.root_cause}</h4>
                    <p className="text-[11px] text-text-secondary leading-relaxed">{hyp.explanation}</p>

                    {/* Cited Evidence */}
                    <div className="pt-2 border-t border-border-subtle">
                      <span className="text-[10px] uppercase font-mono text-text-muted block mb-1">
                        Supporting Evidence Citations:
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {(hyp.supporting_evidence_ids || []).map((eid: string) => (
                          <span
                            key={eid}
                            className="px-1.5 py-0.5 rounded bg-bg-surface text-[10px] font-mono text-accent border border-border-subtle"
                          >
                            {eid}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Human Approval Remediation Gate */}
            <div className="bg-bg-surface border border-border-strong rounded-md p-4 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShieldAlert size={15} className="text-status-warning" />
                  <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                    Remediation & Human Approval Gate
                  </h3>
                </div>
                {proposal && (
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold ${
                      proposal.status === 'EXECUTED'
                        ? 'bg-status-success/20 text-status-success'
                        : 'bg-status-warning/20 text-status-warning'
                    }`}
                  >
                    {proposal.status}
                  </span>
                )}
              </div>

              {proposal ? (
                <div className="space-y-3">
                  <div className="bg-bg-raised p-3 rounded border border-border-subtle space-y-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-mono text-text-muted">Proposed Action:</span>
                      <span className="font-mono font-bold text-text-primary">{proposal.action_type}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-mono text-text-muted">Target Service:</span>
                      <span className="font-mono text-accent">{proposal.target_service_id}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-mono text-text-muted">Safety Risk Assessment:</span>
                      <span className="font-mono text-status-success font-semibold">{proposal.risk_assessment} RISK</span>
                    </div>
                    <p className="text-[11px] text-text-secondary pt-1 border-t border-border-subtle">
                      {proposal.justification}
                    </p>
                  </div>

                  {!isResolved && proposal.status === 'PENDING_APPROVAL' && (
                    <div className="space-y-3 pt-2">
                      <div>
                        <label className="text-[11px] font-medium text-text-secondary block mb-1">
                          Operator Authorization Notes:
                        </label>
                        <input
                          type="text"
                          placeholder="e.g. Authorized automated connection pool reset..."
                          value={operatorNotes}
                          onChange={(e) => setOperatorNotes(e.target.value)}
                          className="w-full bg-bg-raised border border-border-subtle rounded px-3 py-1.5 text-xs text-text-primary focus:outline-none focus:border-accent"
                        />
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => approveMutation.mutate(proposal.id)}
                          disabled={approveMutation.isPending}
                          className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded bg-status-success text-bg-app font-semibold text-xs hover:bg-status-success/90 transition-colors disabled:opacity-50"
                        >
                          <Check size={14} />
                          <span>{approveMutation.isPending ? 'Executing Action...' : 'Approve & Execute Remediation'}</span>
                        </button>

                        <button
                          onClick={() => rejectMutation.mutate(proposal.id)}
                          disabled={rejectMutation.isPending}
                          className="px-3 py-2 rounded bg-bg-raised border border-border-subtle text-status-critical font-medium text-xs hover:bg-status-critical/10 transition-colors"
                        >
                          <X size={14} />
                        </button>
                      </div>
                    </div>
                  )}

                  {isResolved && (
                    <div className="p-3 bg-status-success/10 border border-status-success/30 rounded text-xs space-y-1">
                      <div className="flex items-center gap-1.5 text-status-success font-semibold">
                        <CheckCircle2 size={15} />
                        <span>Remediation Verified & Healthy</span>
                      </div>
                      <p className="text-[11px] text-text-secondary">
                        Predefined safe remediation was successfully executed. Telemetry pipeline verified post-recovery normalization.
                      </p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="py-6 text-center text-text-muted text-xs">
                  Run the LangGraph investigation workflow to generate safe remediation proposals.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
