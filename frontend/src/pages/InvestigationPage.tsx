import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { Header } from '../components/Header';
import {
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ShieldCheck,
  Server,
  FileText,
  Activity,
  Layers,
  Sparkles,
  Check,
  X,
  Terminal,
  Binary,
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
    queryFn: () => api.getServiceMetrics(incident?.primary_service_id, 24),
    enabled: !!incident?.primary_service_id,
    refetchInterval: 3000,
  });

  const chartData = (serviceMetrics || []).map((m: any, i: number) => ({
    time: m.timestamp ? m.timestamp.split('T')[1].slice(0, 8) : `${i * 5}s`,
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
      <div className="flex-1 flex items-center justify-center font-mono text-xs text-text-muted">
        <Activity size={18} className="animate-spin text-text-primary mr-2" />
        Initializing incident workstation...
      </div>
    );
  }

  const proposal = incident.remediation_proposal;
  const isResolved = incident.status === 'RESOLVED';

  return (
    <div className="flex-1 flex flex-col font-sans">
      <Header
        title={`Incident Workstation — ${incident.id}`}
        subtitle="Agentic root cause investigation & remediation execution"
        actions={
          <div className="flex items-center gap-2">
            <Link
              to="/incidents"
              className="flex items-center gap-1 px-2.5 py-1 rounded-sm bg-bg-surface border border-border-subtle text-xs text-text-muted hover:text-text-primary transition-colors font-mono"
            >
              <ArrowLeft size={12} />
              <span>Back</span>
            </Link>

            {incident.status !== 'RESOLVED' && (
              <button
                onClick={() => investigateMutation.mutate()}
                disabled={investigateMutation.isPending}
                className="flex items-center gap-1.5 px-3 py-1 rounded-sm bg-text-primary text-bg-app text-xs font-medium hover:bg-white transition-colors disabled:opacity-50"
              >
                <Sparkles size={12} className={investigateMutation.isPending ? 'animate-spin' : ''} />
                <span>{investigateMutation.isPending ? 'Executing LangGraph...' : 'Investigate Incident'}</span>
              </button>
            )}
          </div>
        }
      />

      <div className="p-6 space-y-6 max-w-7xl mx-auto w-full">
        {/* Editorial Workstation Header Strip */}
        <div className="border border-border-subtle bg-bg-surface rounded-sm p-5 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-border-subtle">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs text-text-muted">{incident.id}</span>
              <span className="text-border-primary">/</span>
              <span
                className={`text-[10px] font-mono px-2 py-0.5 rounded-sm uppercase font-medium ${
                  incident.severity === 'P1_CRITICAL'
                    ? 'text-status-coral bg-status-coral/10 border border-status-coral/25'
                    : 'text-status-amber bg-status-amber/10 border border-status-amber/25'
                }`}
              >
                {incident.severity}
              </span>
              <span
                className={`text-[10px] font-mono px-2 py-0.5 rounded-sm uppercase ${
                  isResolved
                    ? 'text-status-sage bg-status-sage/10 border border-status-sage/20'
                    : incident.status === 'INVESTIGATING'
                    ? 'text-status-amber bg-status-amber/10 border border-status-amber/20 animate-pulse'
                    : 'text-text-secondary bg-bg-raised border border-border-subtle'
                }`}
              >
                {incident.status}
              </span>
            </div>

            <div className="flex items-center gap-4 text-xs font-mono text-text-muted">
              <div>
                <span>Detected: </span>
                <span className="text-text-primary">{incident.detected_at?.replace('T', ' ').slice(0, 19)}</span>
              </div>
              <div>
                <span>Source: </span>
                <span className="text-text-primary">{incident.detection_source}</span>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="space-y-1 max-w-3xl">
              <h2 className="text-base font-semibold text-text-primary tracking-tight">{incident.title}</h2>
              <p className="text-xs text-text-secondary leading-relaxed">{incident.summary}</p>
            </div>

            {/* Quick Metadata Block */}
            <div className="flex items-center gap-4 bg-bg-raised border border-border-subtle rounded-sm px-3.5 py-2 text-xs font-mono">
              <div>
                <span className="text-[10px] uppercase text-text-muted block">Primary Service</span>
                <span className="text-text-primary font-medium">{incident.primary_service_id}</span>
              </div>
              <div className="w-px h-6 bg-border-subtle" />
              <div>
                <span className="text-[10px] uppercase text-text-muted block">ML Confidence</span>
                <span className="text-status-sage font-medium">
                  {incident.ml_confidence ? `${(incident.ml_confidence * 100).toFixed(0)}%` : '—'}
                </span>
              </div>
              <div className="w-px h-6 bg-border-subtle" />
              <div>
                <span className="text-[10px] uppercase text-text-muted block">Blast Radius</span>
                <span className="text-text-primary">{incident.affected_service_ids?.length || 1} Services</span>
              </div>
            </div>
          </div>
        </div>

        {/* 2-Column Workstation Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* LEFT: Telemetry & Verified Evidence (7 cols) */}
          <div className="lg:col-span-7 space-y-6">
            {/* Telemetry Chart */}
            <div className="border border-border-subtle bg-bg-surface rounded-sm p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-xs font-medium text-text-primary block">
                    Telemetry Stream: {incident.primary_service_id}
                  </span>
                  <span className="text-[10px] text-text-muted font-mono">Real-time latency (P95) vs 5xx error percentage</span>
                </div>
                <div className="flex items-center gap-3 text-[10px] font-mono">
                  <span className="flex items-center gap-1 text-text-primary">
                    <span className="w-1.5 h-1.5 rounded-full bg-text-primary" /> Latency P95
                  </span>
                  <span className="flex items-center gap-1 text-status-coral">
                    <span className="w-1.5 h-1.5 rounded-full bg-status-coral" /> Error Rate
                  </span>
                </div>
              </div>

              <div className="h-40 w-full pt-1">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData}>
                    <defs>
                      <linearGradient id="invMono" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#EAE8E3" stopOpacity={0.15} />
                        <stop offset="95%" stopColor="#EAE8E3" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="time" stroke="#252525" tick={{ fill: '#686761', fontSize: 10 }} tickLine={false} />
                    <YAxis stroke="#252525" tick={{ fill: '#686761', fontSize: 10 }} tickLine={false} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#111111', borderColor: '#252525', borderRadius: '3px', fontSize: '11px', color: '#EAE8E3' }}
                    />
                    <Area type="monotone" dataKey="p95" stroke="#EAE8E3" strokeWidth={1.25} fill="url(#invMono)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Abnormal Signals Breakdown */}
            <div className="border border-border-subtle bg-bg-surface rounded-sm p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-text-primary uppercase tracking-wider font-mono">
                  ML Anomaly Signals
                </span>
                <span className="text-[10px] font-mono text-text-muted">
                  Score: {(incident.anomaly_score || 0.89).toFixed(4)} (Threshold: 0.5200)
                </span>
              </div>

              <div className="flex flex-wrap gap-2">
                {(incident.abnormal_features || []).map((feat: any, idx: number) => (
                  <div
                    key={idx}
                    className="px-2.5 py-1 rounded-sm bg-bg-raised border border-border-primary text-xs font-mono flex items-center gap-2"
                  >
                    <span className="text-status-coral font-medium">{feat.feature}</span>
                    <span className="text-text-primary">{feat.value}</span>
                    <span className="text-[10px] text-text-muted">(+{feat.deviation_sigma}σ)</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Verified Diagnostic Evidence Panel (Monospace, Tabs) */}
            <div className="border border-border-subtle bg-bg-surface rounded-sm overflow-hidden">
              <div className="px-4 py-2.5 border-b border-border-subtle flex items-center justify-between">
                <span className="text-xs font-medium text-text-primary uppercase tracking-wider font-mono">
                  Verified Diagnostic Evidence
                </span>
                <div className="flex items-center gap-1 bg-bg-raised p-0.5 rounded-sm text-xs font-mono">
                  <button
                    onClick={() => setActiveEvidenceTab('METRICS')}
                    className={`px-2 py-0.5 rounded-sm text-[10px] transition-colors ${
                      activeEvidenceTab === 'METRICS'
                        ? 'bg-bg-hover text-text-primary font-medium'
                        : 'text-text-muted hover:text-text-secondary'
                    }`}
                  >
                    Metrics & Spans
                  </button>
                  <button
                    onClick={() => setActiveEvidenceTab('LOGS')}
                    className={`px-2 py-0.5 rounded-sm text-[10px] transition-colors ${
                      activeEvidenceTab === 'LOGS'
                        ? 'bg-bg-hover text-text-primary font-medium'
                        : 'text-text-muted hover:text-text-secondary'
                    }`}
                  >
                    Error Logs
                  </button>
                  <button
                    onClick={() => setActiveEvidenceTab('RUNBOOKS')}
                    className={`px-2 py-0.5 rounded-sm text-[10px] transition-colors ${
                      activeEvidenceTab === 'RUNBOOKS'
                        ? 'bg-bg-hover text-text-primary font-medium'
                        : 'text-text-muted hover:text-text-secondary'
                    }`}
                  >
                    Runbook RAG
                  </button>
                </div>
              </div>

              <div className="p-4 space-y-3">
                {(incident.evidence || []).map((ev: any) => (
                  <div key={ev.id} className="p-3 bg-bg-raised border border-border-subtle rounded-sm text-xs space-y-1.5 font-mono">
                    <div className="flex items-center justify-between text-[11px]">
                      <div className="flex items-center gap-2">
                        <span className="text-text-primary font-medium">{ev.id}</span>
                        <span className="text-border-primary">/</span>
                        <span className="text-text-muted uppercase text-[10px]">{ev.evidence_type}</span>
                      </div>
                      <span className="text-text-muted text-[10px]">{ev.timestamp?.slice(11, 19)} UTC</span>
                    </div>

                    <div className="text-text-secondary text-xs font-sans font-medium">{ev.headline}</div>

                    {ev.details && (
                      <pre className="text-[10.5px] font-mono bg-bg-app p-2 rounded-sm text-text-muted border border-border-subtle overflow-x-auto">
                        {JSON.stringify(ev.details, null, 2)}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Investigation Timeline */}
            <div className="border border-border-subtle bg-bg-surface rounded-sm p-4 space-y-3">
              <span className="text-xs font-medium text-text-primary uppercase tracking-wider font-mono block">
                Investigation Sequence
              </span>
              <div className="space-y-3 relative before:absolute before:inset-0 before:left-1.5 before:w-px before:bg-border-subtle">
                {(incident.timeline || []).map((ev: any, idx: number) => (
                  <div key={idx} className="relative pl-5 space-y-0.5">
                    <div className="absolute left-1 top-1.5 w-1.5 h-1.5 rounded-full bg-border-strong border border-bg-surface" />
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono text-text-muted">{ev.created_at?.slice(11, 19)}</span>
                      <span className="text-[9px] font-mono px-1 py-0.2 rounded-sm bg-bg-raised text-text-secondary uppercase">
                        {ev.event_type}
                      </span>
                    </div>
                    <p className="text-xs text-text-primary">{ev.description}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* RIGHT: AI Root Cause Hypotheses & Remediation Gate (5 cols) */}
          <div className="lg:col-span-5 space-y-6">
            {/* Ranked Root Cause Hypotheses */}
            <div className="border border-border-subtle bg-bg-surface rounded-sm p-4 space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-border-subtle">
                <span className="text-xs font-medium text-text-primary uppercase tracking-wider font-mono">
                  Ranked Root-Cause Hypotheses
                </span>
                <span className="text-[10px] font-mono text-text-muted">Gemini 3.5 Flash-Lite</span>
              </div>

              <div className="space-y-3">
                {(incident.hypotheses || []).map((hyp: any) => (
                  <div key={hyp.id} className="p-3.5 bg-bg-raised border border-border-primary rounded-sm space-y-2">
                    <div className="flex items-center justify-between text-xs font-mono">
                      <span className="text-text-primary font-bold">Hypothesis #{hyp.rank}</span>
                      <span className="text-status-sage">
                        {(hyp.confidence_score * 100).toFixed(0)}% Confidence
                      </span>
                    </div>

                    <h4 className="text-xs font-semibold text-text-primary leading-tight">{hyp.root_cause}</h4>
                    <p className="text-[11px] text-text-secondary leading-relaxed">{hyp.explanation}</p>

                    <div className="pt-2 border-t border-border-subtle text-[11px] font-mono">
                      <span className="text-[10px] uppercase text-text-muted block mb-1">Supporting Evidence:</span>
                      <div className="flex flex-wrap gap-1">
                        {(hyp.supporting_evidence_ids || []).map((eid: string) => (
                          <span
                            key={eid}
                            className="px-1.5 py-0.2 rounded-sm bg-bg-surface border border-border-subtle text-[10px] text-text-secondary"
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

            {/* Separate Remediation Approval Workstation Card */}
            <div className="border border-border-primary bg-bg-surface rounded-sm p-4 space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-border-subtle">
                <span className="text-xs font-medium text-text-primary uppercase tracking-wider font-mono">
                  Remediation & Human Approval Gate
                </span>
                {proposal && (
                  <span
                    className={`text-[9px] font-mono px-1.5 py-0.2 rounded-sm uppercase ${
                      proposal.status === 'EXECUTED'
                        ? 'text-status-sage bg-status-sage/10 border border-status-sage/20'
                        : 'text-status-amber bg-status-amber/10 border border-status-amber/20'
                    }`}
                  >
                    {proposal.status}
                  </span>
                )}
              </div>

              {proposal ? (
                <div className="space-y-3 text-xs">
                  <div className="bg-bg-raised p-3 rounded-sm border border-border-subtle space-y-1.5 font-mono">
                    <div className="flex justify-between">
                      <span className="text-text-muted">Proposed Action:</span>
                      <span className="text-text-primary font-bold">{proposal.action_type}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-muted">Target Service:</span>
                      <span className="text-text-primary">{proposal.target_service_id}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-muted">Safety Risk:</span>
                      <span className="text-status-sage font-medium">{proposal.risk_assessment} RISK</span>
                    </div>
                    <p className="text-[11px] text-text-secondary font-sans pt-2 border-t border-border-subtle">
                      {proposal.justification}
                    </p>
                  </div>

                  {!isResolved && proposal.status === 'PENDING_APPROVAL' && (
                    <div className="space-y-3 pt-1">
                      <div>
                        <label className="text-[11px] text-text-muted block mb-1 font-mono">
                          Operator Authorization Signature / Notes:
                        </label>
                        <input
                          type="text"
                          placeholder="e.g. Authorized automated recovery procedure..."
                          value={operatorNotes}
                          onChange={(e) => setOperatorNotes(e.target.value)}
                          className="w-full bg-bg-raised border border-border-subtle rounded-sm px-2.5 py-1.5 text-xs text-text-primary font-mono focus:outline-none focus:border-border-strong"
                        />
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => approveMutation.mutate(proposal.id)}
                          disabled={approveMutation.isPending}
                          className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-sm bg-text-primary text-bg-app font-medium text-xs hover:bg-white transition-colors disabled:opacity-50"
                        >
                          <Check size={13} />
                          <span>{approveMutation.isPending ? 'Executing Action...' : 'Approve & Execute Remediation'}</span>
                        </button>

                        <button
                          onClick={() => rejectMutation.mutate(proposal.id)}
                          disabled={rejectMutation.isPending}
                          className="px-2.5 py-1.5 rounded-sm bg-bg-raised border border-border-subtle text-status-coral hover:bg-status-coral/10 text-xs transition-colors"
                        >
                          <X size={13} />
                        </button>
                      </div>
                    </div>
                  )}

                  {isResolved && (
                    <div className="p-3 bg-status-sage/10 border border-status-sage/20 rounded-sm text-xs space-y-1">
                      <div className="flex items-center gap-1.5 text-status-sage font-medium">
                        <CheckCircle2 size={14} />
                        <span>Remediation Verified & Healthy</span>
                      </div>
                      <p className="text-[11px] text-text-secondary">
                        Action executed safely. Telemetry pipeline verified post-action normalization across the fleet.
                      </p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="py-8 text-center text-text-muted text-xs font-mono">
                  Run the LangGraph investigation workflow to generate remediation proposals.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
