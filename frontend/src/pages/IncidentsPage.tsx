import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import { Header } from '../components/Header';
import {
  AlertTriangle,
  Search,
  Filter,
  RefreshCw,
  Clock,
  ArrowRight,
  ShieldAlert,
} from 'lucide-react';

export const IncidentsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState<string>('');

  const { data: incidents, isLoading, refetch } = useQuery({
    queryKey: ['incidents'],
    queryFn: () => api.getIncidents(),
    refetchInterval: 3000,
  });

  const detectMutation = useMutation({
    mutationFn: api.detectIncidents,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
    },
  });

  const filteredIncidents = (incidents || []).filter((inc: any) => {
    if (severityFilter !== 'ALL' && inc.severity !== severityFilter) return false;
    if (statusFilter !== 'ALL' && inc.status !== statusFilter) return false;
    if (searchTerm) {
      const matchTitle = inc.title.toLowerCase().includes(searchTerm.toLowerCase());
      const matchService = inc.primary_service_id.toLowerCase().includes(searchTerm.toLowerCase());
      const matchId = inc.id.toLowerCase().includes(searchTerm.toLowerCase());
      if (!matchTitle && !matchService && !matchId) return false;
    }
    return true;
  });

  return (
    <div className="flex-1 flex flex-col">
      <Header
        title="Production Incidents"
        subtitle="Correlated multi-service incidents detected by machine learning and investigated by agentic AI"
        actions={
          <button
            onClick={() => detectMutation.mutate()}
            disabled={detectMutation.isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-accent text-bg-app text-xs font-semibold hover:bg-accent/90 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={13} className={detectMutation.isPending ? 'animate-spin' : ''} />
            <span>{detectMutation.isPending ? 'Scanning...' : 'Scan Anomaly Pipeline'}</span>
          </button>
        }
      />

      <div className="p-6 space-y-4">
        {/* Filters and search bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 bg-bg-surface border border-border-subtle rounded-md p-3">
          <div className="flex items-center gap-2 flex-1 min-w-[240px]">
            <Search size={15} className="text-text-muted" />
            <input
              type="text"
              placeholder="Search by incident ID, title, or service..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-transparent text-xs text-text-primary placeholder:text-text-muted focus:outline-none w-full"
            />
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] text-text-muted">Severity:</span>
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="bg-bg-raised border border-border-subtle rounded text-xs px-2 py-1 text-text-primary focus:outline-none"
              >
                <option value="ALL">All Severities</option>
                <option value="P1_CRITICAL">P1 Critical</option>
                <option value="P2_HIGH">P2 High</option>
                <option value="P3_MEDIUM">P3 Medium</option>
              </select>
            </div>

            <div className="flex items-center gap-1.5">
              <span className="text-[11px] text-text-muted">Status:</span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-bg-raised border border-border-subtle rounded text-xs px-2 py-1 text-text-primary focus:outline-none"
              >
                <option value="ALL">All Statuses</option>
                <option value="DETECTED">Detected</option>
                <option value="INVESTIGATING">Investigating</option>
                <option value="IDENTIFIED">Identified</option>
                <option value="RESOLVED">Resolved</option>
              </select>
            </div>
          </div>
        </div>

        {/* Incidents Table */}
        <div className="bg-bg-surface border border-border-subtle rounded-md overflow-hidden">
          <table className="w-full text-left text-xs">
            <thead className="bg-bg-raised text-text-secondary border-b border-border-subtle">
              <tr>
                <th className="py-2.5 px-4 font-medium">Incident ID</th>
                <th className="py-2.5 px-4 font-medium">Title & Root Cause</th>
                <th className="py-2.5 px-4 font-medium">Severity</th>
                <th className="py-2.5 px-4 font-medium">Primary Service</th>
                <th className="py-2.5 px-4 font-medium">Status</th>
                <th className="py-2.5 px-4 font-medium">ML Confidence</th>
                <th className="py-2.5 px-4 font-medium">Detected At</th>
                <th className="py-2.5 px-4 font-medium text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle">
              {filteredIncidents.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-text-muted">
                    <ShieldAlert size={28} className="mx-auto mb-2 opacity-40" />
                    <p className="text-xs">No incidents match the active filter criteria.</p>
                  </td>
                </tr>
              ) : (
                filteredIncidents.map((inc: any) => (
                  <tr key={inc.id} className="hover:bg-bg-raised/40 transition-colors">
                    <td className="py-3 px-4 font-mono font-medium text-accent">
                      <Link to={`/incidents/${inc.id}`} className="hover:underline">
                        {inc.id}
                      </Link>
                    </td>
                    <td className="py-3 px-4 max-w-md">
                      <div className="font-medium text-text-primary truncate">{inc.title}</div>
                      <div className="text-[11px] text-text-muted truncate">{inc.summary}</div>
                    </td>
                    <td className="py-3 px-4 font-mono">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                          inc.severity === 'P1_CRITICAL'
                            ? 'bg-status-critical/15 text-status-critical border border-status-critical/30'
                            : 'bg-status-warning/15 text-status-warning border border-status-warning/30'
                        }`}
                      >
                        {inc.severity}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-text-secondary">{inc.primary_service_id}</td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono ${
                          inc.status === 'RESOLVED'
                            ? 'bg-status-success/15 text-status-success'
                            : inc.status === 'INVESTIGATING'
                            ? 'bg-accent/15 text-accent animate-pulse'
                            : 'bg-status-warning/15 text-status-warning'
                        }`}
                      >
                        <span
                          className={`w-1.5 h-1.5 rounded-full ${
                            inc.status === 'RESOLVED'
                              ? 'bg-status-success'
                              : inc.status === 'INVESTIGATING'
                              ? 'bg-accent'
                              : 'bg-status-warning'
                          }`}
                        />
                        {inc.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono">
                      {inc.ml_confidence ? `${(inc.ml_confidence * 100).toFixed(0)}%` : '—'}
                    </td>
                    <td className="py-3 px-4 font-mono text-text-muted">
                      {inc.detected_at?.replace('T', ' ').slice(0, 19)}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Link
                        to={`/incidents/${inc.id}`}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-bg-raised border border-border-subtle hover:border-accent/50 text-accent font-medium text-xs transition-colors"
                      >
                        <span>Investigate</span>
                        <ArrowRight size={13} />
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
