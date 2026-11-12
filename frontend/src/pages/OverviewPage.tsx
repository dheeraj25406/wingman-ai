import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import { Header } from '../components/Header';
import {
  ArrowUpRight,
  Clock,
  Activity,
  Layers,
  ArrowRight,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

export const OverviewPage: React.FC = () => {
  const [timeRange, setTimeRange] = useState<'15m' | '1h' | '24h'>('15m');

  const { data: overview } = useQuery({
    queryKey: ['metrics-overview'],
    queryFn: api.getMetricsOverview,
    refetchInterval: 3000,
  });

  const { data: services } = useQuery({
    queryKey: ['services'],
    queryFn: api.getServices,
    refetchInterval: 3000,
  });

  const { data: incidents } = useQuery({
    queryKey: ['incidents'],
    queryFn: () => api.getIncidents(),
    refetchInterval: 3000,
  });

  const { data: gatewayMetrics } = useQuery({
    queryKey: ['service-metrics', 'api-gateway'],
    queryFn: () => api.getServiceMetrics('api-gateway', 24),
    refetchInterval: 3000,
  });

  const chartData = (gatewayMetrics || []).map((m: any, i: number) => ({
    time: m.timestamp ? m.timestamp.split('T')[1].slice(0, 8) : `${i * 5}s`,
    p95: m.latency_p95,
    error_rate: Number((m.error_rate * 100).toFixed(2)),
    rps: m.request_rate,
  }));

  const isDegraded = (overview?.critical_services || 0) > 0 || (overview?.degraded_services || 0) > 0;

  return (
    <div className="flex-1 flex flex-col font-sans">
      <Header
        title="Fleet Overview"
        subtitle="Distributed runtime telemetry & anomaly monitoring"
        actions={
          <div className="flex items-center gap-2">
            {/* Time range toggle */}
            <div className="flex items-center rounded-sm bg-bg-surface border border-border-subtle p-0.5 text-[11px] font-mono">
              {(['15m', '1h', '24h'] as const).map((r) => (
                <button
                  key={r}
                  onClick={() => setTimeRange(r)}
                  className={`px-2 py-0.5 rounded-sm transition-colors ${
                    timeRange === r
                      ? 'bg-bg-raised text-text-primary font-medium'
                      : 'text-text-muted hover:text-text-secondary'
                  }`}
                >
                  {r}
                </button>
              ))}
            </div>

            <Link
              to="/fault-lab"
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-sm bg-bg-surface border border-border-primary hover:border-text-secondary text-text-primary text-xs font-medium transition-colors"
            >
              <span>Fault Lab</span>
              <ArrowUpRight size={13} className="text-text-muted" />
            </Link>
          </div>
        }
      />

      <div className="p-6 space-y-6 max-w-7xl mx-auto w-full">
        {/* SECTION 1: Asymmetric System Health Composition */}
        <section className="border border-border-subtle bg-bg-surface rounded-sm p-5">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
            {/* Hero Health State (5 cols) */}
            <div className="lg:col-span-5 space-y-1.5 border-b lg:border-b-0 lg:border-r border-border-subtle pb-4 lg:pb-0 lg:pr-6">
              <div className="flex items-center gap-2">
                <span
                  className={`w-2 h-2 rounded-full ${
                    isDegraded ? 'bg-status-coral animate-pulse' : 'bg-status-sage'
                  }`}
                />
                <span className="text-[11px] font-mono uppercase tracking-wider text-text-muted">
                  System Health Index
                </span>
              </div>
              <div className="text-2xl font-medium tracking-tight text-text-primary">
                {isDegraded ? 'Degraded Performance' : 'Fleet Operating Normally'}
              </div>
              <p className="text-xs text-text-secondary leading-relaxed">
                {isDegraded
                  ? `${overview?.critical_services || 1} service experiencing abnormal anomaly spikes. Primary correlation active.`
                  : 'All 6 microservices reporting nominal telemetry within historical baseline limits.'}
              </p>
            </div>

            {/* Asymmetric secondary technical metrics (7 cols) */}
            <div className="lg:col-span-7 grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-text-muted block">
                  Active Incidents
                </span>
                <span
                  className={`text-xl font-mono font-medium mt-1 block ${
                    (overview?.active_incidents_count || 0) > 0 ? 'text-status-coral' : 'text-text-primary'
                  }`}
                >
                  {overview?.active_incidents_count || 0}
                </span>
                <span className="text-[10px] text-text-muted font-mono">P1/P2 Active</span>
              </div>

              <div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-text-muted block">
                  P95 Fleet Latency
                </span>
                <span
                  className={`text-xl font-mono font-medium mt-1 block ${
                    (overview?.avg_latency_p95 || 45) > 500 ? 'text-status-amber' : 'text-text-primary'
                  }`}
                >
                  {(overview?.avg_latency_p95 || 45.2).toFixed(1)}
                  <span className="text-xs text-text-muted ml-0.5 font-normal">ms</span>
                </span>
                <span className="text-[10px] text-text-muted font-mono">Baseline: 52ms</span>
              </div>

              <div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-text-muted block">
                  Global Error Rate
                </span>
                <span
                  className={`text-xl font-mono font-medium mt-1 block ${
                    (overview?.global_error_rate || 0) > 0.05 ? 'text-status-coral' : 'text-text-primary'
                  }`}
                >
                  {((overview?.global_error_rate || 0.002) * 100).toFixed(2)}
                  <span className="text-xs text-text-muted ml-0.5 font-normal">%</span>
                </span>
                <span className="text-[10px] text-text-muted font-mono">SLO: &lt; 0.10%</span>
              </div>

              <div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-text-muted block">
                  Throughput
                </span>
                <span className="text-xl font-mono font-medium mt-1 block text-text-primary">
                  {(overview?.total_throughput_rps || 10.0).toFixed(1)}
                  <span className="text-xs text-text-muted ml-0.5 font-normal">rps</span>
                </span>
                <span className="text-[10px] text-text-muted font-mono">Simulated load</span>
              </div>
            </div>
          </div>
        </section>

        {/* SECTION 2: Observability Charts (Visually Integrated, Thin Lines, Monochromatic) */}
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Latency P95 Chart */}
          <div className="border border-border-subtle bg-bg-surface rounded-sm p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-medium text-text-primary block">API Gateway Latency (P95)</span>
                <span className="text-[10px] text-text-muted font-mono">Sliding telemetry window (ms)</span>
              </div>
              <span className="text-xs font-mono text-text-primary">
                {gatewayMetrics?.length ? `${gatewayMetrics[gatewayMetrics.length - 1].latency_p95.toFixed(1)} ms` : '—'}
              </span>
            </div>

            <div className="h-40 w-full pt-1">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="latencyMono" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#F2F2F2" stopOpacity={0.15} />
                      <stop offset="95%" stopColor="#F2F2F2" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="time" stroke="#252525" tick={{ fill: '#858585', fontSize: 10 }} tickLine={false} />
                  <YAxis stroke="#252525" tick={{ fill: '#858585', fontSize: 10 }} tickLine={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#111111', borderColor: '#303030', borderRadius: '3px', fontSize: '11px', color: '#F2F2F2' }}
                  />
                  <Area type="monotone" dataKey="p95" stroke="#F2F2F2" strokeWidth={1.25} fill="url(#latencyMono)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Error Rate Chart */}
          <div className="border border-border-subtle bg-bg-surface rounded-sm p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-medium text-text-primary block">HTTP 5xx Error Ratio</span>
                <span className="text-[10px] text-text-muted font-mono">Percentage of failed requests</span>
              </div>
              <span className="text-xs font-mono text-status-coral">
                {gatewayMetrics?.length ? `${(gatewayMetrics[gatewayMetrics.length - 1].error_rate * 100).toFixed(2)} %` : '—'}
              </span>
            </div>

            <div className="h-40 w-full pt-1">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="errorCoral" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#D96C6C" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="#D96C6C" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="time" stroke="#252525" tick={{ fill: '#858585', fontSize: 10 }} tickLine={false} />
                  <YAxis stroke="#252525" tick={{ fill: '#858585', fontSize: 10 }} tickLine={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#111111', borderColor: '#303030', borderRadius: '3px', fontSize: '11px', color: '#F2F2F2' }}
                  />
                  <Area type="monotone" dataKey="error_rate" stroke="#D96C6C" strokeWidth={1.25} fill="url(#errorCoral)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </section>

        {/* SECTION 3: Monitored Service Fleet (Full-width editorial data table) */}
        <section className="border border-border-subtle bg-bg-surface rounded-sm overflow-hidden">
          <div className="px-5 py-3 border-b border-border-subtle flex items-center justify-between">
            <span className="text-xs font-medium text-text-primary uppercase tracking-wider font-mono">
              Monitored Service Fleet (6)
            </span>
            <span className="text-[11px] text-text-muted font-mono">Prometheus & OTel Ingestion Active</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-border-subtle text-[11px] font-mono text-text-muted uppercase tracking-wider">
                <tr>
                  <th className="py-2.5 px-5 font-normal">Service</th>
                  <th className="py-2.5 px-4 font-normal">Status</th>
                  <th className="py-2.5 px-4 font-normal font-mono">CPU</th>
                  <th className="py-2.5 px-4 font-normal font-mono">Memory</th>
                  <th className="py-2.5 px-4 font-normal font-mono">P95 Latency</th>
                  <th className="py-2.5 px-4 font-normal font-mono">5xx Rate</th>
                  <th className="py-2.5 px-4 font-normal font-mono">Throughput</th>
                  <th className="py-2.5 px-5 font-normal text-right font-mono">Active Injected Fault</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle">
                {(services || []).map((svc: any) => {
                  const m = svc.latest_metrics || {};
                  return (
                    <tr key={svc.id} className="hover:bg-bg-hover transition-colors">
                      <td className="py-2.5 px-5 font-mono font-medium text-text-primary">
                        <Link to="/services" className="hover:underline">
                          {svc.id}
                        </Link>
                      </td>
                      <td className="py-2.5 px-4">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm text-[10px] font-mono uppercase ${
                            svc.status === 'healthy'
                              ? 'text-status-sage bg-status-sage/10 border border-status-sage/20'
                              : svc.status === 'degraded'
                              ? 'text-status-amber bg-status-amber/10 border border-status-amber/20'
                              : 'text-status-coral bg-status-coral/10 border border-status-coral/20'
                          }`}
                        >
                          <span
                            className={`w-1 h-1 rounded-full ${
                              svc.status === 'healthy'
                                ? 'bg-status-sage'
                                : svc.status === 'degraded'
                                ? 'bg-status-amber'
                                : 'bg-status-coral'
                            }`}
                          />
                          {svc.status}
                        </span>
                      </td>
                      <td className="py-2.5 px-4 font-mono text-text-secondary">{m.cpu_utilization?.toFixed(1)}%</td>
                      <td className="py-2.5 px-4 font-mono text-text-secondary">{m.memory_utilization?.toFixed(1)}%</td>
                      <td className="py-2.5 px-4 font-mono text-text-secondary">{m.latency_p95?.toFixed(1)}ms</td>
                      <td className="py-2.5 px-4 font-mono">
                        <span className={m.error_rate > 0.05 ? 'text-status-coral font-medium' : 'text-text-secondary'}>
                          {(m.error_rate * 100).toFixed(2)}%
                        </span>
                      </td>
                      <td className="py-2.5 px-4 font-mono text-text-secondary">{m.request_rate?.toFixed(1)} rps</td>
                      <td className="py-2.5 px-5 text-right font-mono">
                        {svc.active_fault ? (
                          <span className="px-2 py-0.5 rounded-sm bg-status-coral/15 text-status-coral border border-status-coral/30 text-[10px] font-medium">
                            {svc.active_fault}
                          </span>
                        ) : (
                          <span className="text-text-muted text-[11px]">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>

        {/* SECTION 4: Recent Incident Activity Timeline */}
        <section className="border border-border-subtle bg-bg-surface rounded-sm p-5 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-border-subtle">
            <span className="text-xs font-medium text-text-primary uppercase tracking-wider font-mono">
              Recent Production Incidents
            </span>
            <Link to="/incidents" className="text-xs text-text-muted hover:text-text-primary transition-colors flex items-center gap-1 font-mono">
              <span>View All</span>
              <ArrowRight size={12} />
            </Link>
          </div>

          <div className="divide-y divide-border-subtle">
            {(incidents || []).slice(0, 3).map((inc: any) => (
              <div key={inc.id} className="py-3 flex items-center justify-between gap-4">
                <div className="space-y-0.5 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-text-muted">{inc.id}</span>
                    <span
                      className={`text-[9px] font-mono px-1.5 py-0.2 rounded-sm uppercase ${
                        inc.severity === 'P1_CRITICAL'
                          ? 'text-status-coral bg-status-coral/10 border border-status-coral/25'
                          : 'text-status-amber bg-status-amber/10 border border-status-amber/25'
                      }`}
                    >
                      {inc.severity}
                    </span>
                    <span className="text-xs font-medium text-text-primary truncate">{inc.title}</span>
                  </div>
                  <p className="text-[11px] text-text-secondary truncate">{inc.summary}</p>
                </div>

                <Link
                  to={`/incidents/${inc.id}`}
                  className="px-2.5 py-1 rounded-sm bg-bg-raised border border-border-primary hover:border-text-muted text-xs text-text-primary font-mono transition-colors shrink-0"
                >
                  Investigate →
                </Link>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
};
