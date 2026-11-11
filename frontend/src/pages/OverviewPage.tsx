import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import { Header } from '../components/Header';
import {
  Activity,
  AlertTriangle,
  Server,
  Zap,
  Clock,
  ArrowUpRight,
  TrendingUp,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

export const OverviewPage: React.FC = () => {
  const { data: overview, isLoading: overviewLoading } = useQuery({
    queryKey: ['metrics-overview'],
    queryFn: api.getMetricsOverview,
    refetchInterval: 3000,
  });

  const { data: services, isLoading: servicesLoading } = useQuery({
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
    queryFn: () => api.getServiceMetrics('api-gateway', 20),
    refetchInterval: 3000,
  });

  const chartData = (gatewayMetrics || []).map((m: any, i: number) => ({
    time: m.timestamp ? m.timestamp.split('T')[1].slice(0, 8) : `${i}s`,
    p95: m.latency_p95,
    error_rate: Number((m.error_rate * 100).toFixed(2)),
    cpu: m.cpu_utilization,
  }));

  const kpis = [
    {
      label: 'System Status',
      value: overview?.critical_services ? 'Degraded' : 'Operational',
      sub: `${overview?.healthy_services || 6} / ${overview?.total_services || 6} services healthy`,
      status: overview?.critical_services ? 'critical' : 'success',
      icon: Activity,
    },
    {
      label: 'Global Error Rate',
      value: `${((overview?.global_error_rate || 0.002) * 100).toFixed(2)}%`,
      sub: 'Target SLO: < 0.10%',
      status: (overview?.global_error_rate || 0) > 0.05 ? 'critical' : 'normal',
      icon: AlertTriangle,
    },
    {
      label: 'Average P95 Latency',
      value: `${(overview?.avg_latency_p95 || 45.2).toFixed(1)} ms`,
      sub: 'Fleet baseline: 52 ms',
      status: (overview?.avg_latency_p95 || 0) > 500 ? 'warning' : 'normal',
      icon: Clock,
    },
    {
      label: 'Throughput',
      value: `${(overview?.total_throughput_rps || 10.0).toFixed(1)} RPS`,
      sub: 'Simulated HTTP traffic',
      status: 'normal',
      icon: Zap,
    },
  ];

  return (
    <div className="flex-1 flex flex-col">
      <Header
        title="Fleet Observability Overview"
        subtitle="Real-time telemetry and ML-driven anomaly detection across distributed services"
        actions={
          <Link
            to="/fault-lab"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-accent/10 border border-accent/30 text-accent text-xs font-medium hover:bg-accent/20 transition-colors"
          >
            <span>Open Fault Lab</span>
            <ArrowUpRight size={14} />
          </Link>
        }
      />

      <div className="p-6 space-y-6">
        {/* KPI Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {kpis.map((kpi, idx) => {
            const Icon = kpi.icon;
            return (
              <div
                key={idx}
                className="bg-bg-surface border border-border-subtle rounded-md p-4 flex flex-col justify-between"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-text-secondary">{kpi.label}</span>
                  <div className="w-7 h-7 rounded bg-bg-raised border border-border-subtle flex items-center justify-center text-text-muted">
                    <Icon size={14} />
                  </div>
                </div>
                <div className="mt-3">
                  <div
                    className={`text-xl font-bold font-mono tracking-tight ${
                      kpi.status === 'critical'
                        ? 'text-status-critical'
                        : kpi.status === 'success'
                        ? 'text-status-success'
                        : kpi.status === 'warning'
                        ? 'text-status-warning'
                        : 'text-text-primary'
                    }`}
                  >
                    {kpi.value}
                  </div>
                  <div className="text-[11px] text-text-muted mt-0.5">{kpi.sub}</div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Telemetry Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="bg-bg-surface border border-border-subtle rounded-md p-4">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-xs font-semibold text-text-primary tracking-tight">API Gateway P95 Latency</h3>
                <p className="text-[11px] text-text-muted">Sliding 60s sample window (ms)</p>
              </div>
              <span className="text-xs font-mono text-accent">p95</span>
            </div>
            <div className="h-44 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="latencyGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#65A9FF" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#65A9FF" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="time" stroke="#647184" fontSize={10} tickLine={false} />
                  <YAxis stroke="#647184" fontSize={10} tickLine={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#151D27', borderColor: '#293442', fontSize: '11px' }}
                  />
                  <Area type="monotone" dataKey="p95" stroke="#65A9FF" strokeWidth={1.5} fillOpacity={1} fill="url(#latencyGradient)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="bg-bg-surface border border-border-subtle rounded-md p-4">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-xs font-semibold text-text-primary tracking-tight">Fleet Error Rate (%)</h3>
                <p className="text-[11px] text-text-muted">Ratio of 5xx HTTP responses</p>
              </div>
              <span className="text-xs font-mono text-status-critical">5xx %</span>
            </div>
            <div className="h-44 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="errorGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#E16B73" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#E16B73" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="time" stroke="#647184" fontSize={10} tickLine={false} />
                  <YAxis stroke="#647184" fontSize={10} tickLine={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#151D27', borderColor: '#293442', fontSize: '11px' }}
                  />
                  <Area type="monotone" dataKey="error_rate" stroke="#E16B73" strokeWidth={1.5} fillOpacity={1} fill="url(#errorGradient)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Monitored Services Grid */}
        <div className="bg-bg-surface border border-border-subtle rounded-md overflow-hidden">
          <div className="px-4 py-3 border-b border-border-subtle flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Server size={14} className="text-accent" />
              <h2 className="text-xs font-semibold text-text-primary uppercase tracking-wider">Monitored Service Fleet</h2>
            </div>
            <span className="text-[11px] font-mono text-text-muted">6 Microservices Instrumented</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-bg-raised text-text-secondary border-b border-border-subtle">
                <tr>
                  <th className="py-2.5 px-4 font-medium">Service</th>
                  <th className="py-2.5 px-4 font-medium">Status</th>
                  <th className="py-2.5 px-4 font-medium">CPU</th>
                  <th className="py-2.5 px-4 font-medium">Memory</th>
                  <th className="py-2.5 px-4 font-medium">Latency (P95)</th>
                  <th className="py-2.5 px-4 font-medium">Error Rate</th>
                  <th className="py-2.5 px-4 font-medium">Throughput</th>
                  <th className="py-2.5 px-4 font-medium">Active Fault</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle">
                {(services || []).map((svc: any) => {
                  const m = svc.latest_metrics || {};
                  return (
                    <tr key={svc.id} className="hover:bg-bg-raised/50 transition-colors">
                      <td className="py-3 px-4 font-mono font-medium text-text-primary">
                        <Link to={`/services`} className="hover:underline text-accent">
                          {svc.id}
                        </Link>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono uppercase ${
                            svc.status === 'healthy'
                              ? 'bg-status-success/10 text-status-success'
                              : svc.status === 'degraded'
                              ? 'bg-status-warning/10 text-status-warning'
                              : 'bg-status-critical/10 text-status-critical'
                          }`}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              svc.status === 'healthy'
                                ? 'bg-status-success'
                                : svc.status === 'degraded'
                                ? 'bg-status-warning'
                                : 'bg-status-critical'
                            }`}
                          />
                          {svc.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono">{m.cpu_utilization?.toFixed(1)}%</td>
                      <td className="py-3 px-4 font-mono">{m.memory_utilization?.toFixed(1)}%</td>
                      <td className="py-3 px-4 font-mono">{m.latency_p95?.toFixed(1)} ms</td>
                      <td className="py-3 px-4 font-mono">
                        <span className={m.error_rate > 0.05 ? 'text-status-critical font-bold' : ''}>
                          {(m.error_rate * 100).toFixed(2)}%
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono">{m.request_rate?.toFixed(1)} rps</td>
                      <td className="py-3 px-4 font-mono">
                        {svc.active_fault ? (
                          <span className="px-2 py-0.5 rounded bg-status-critical/20 text-status-critical text-[10px] font-bold border border-status-critical/40">
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
        </div>

        {/* Recent Incidents Section */}
        <div className="bg-bg-surface border border-border-subtle rounded-md overflow-hidden">
          <div className="px-4 py-3 border-b border-border-subtle flex items-center justify-between">
            <h2 className="text-xs font-semibold text-text-primary uppercase tracking-wider">Recent Production Incidents</h2>
            <Link to="/incidents" className="text-xs text-accent hover:underline flex items-center gap-1 font-medium">
              <span>View All</span>
              <ArrowUpRight size={13} />
            </Link>
          </div>
          <div className="divide-y divide-border-subtle">
            {(incidents || []).slice(0, 3).map((inc: any) => (
              <div key={inc.id} className="p-4 flex items-center justify-between hover:bg-bg-raised/40 transition-colors">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-text-muted">{inc.id}</span>
                    <span
                      className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                        inc.severity === 'P1_CRITICAL'
                          ? 'bg-status-critical/15 text-status-critical border border-status-critical/30'
                          : 'bg-status-warning/15 text-status-warning border border-status-warning/30'
                      }`}
                    >
                      {inc.severity}
                    </span>
                    <span className="text-xs font-medium text-text-primary">{inc.title}</span>
                  </div>
                  <p className="text-[11px] text-text-secondary">{inc.summary}</p>
                </div>
                <Link
                  to={`/incidents/${inc.id}`}
                  className="px-3 py-1.5 rounded bg-bg-raised border border-border-subtle text-xs font-medium text-accent hover:border-accent/40 transition-colors"
                >
                  Investigate →
                </Link>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
