import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import { Header } from '../components/Header';
import {
  Search,
  RefreshCw,
  ArrowRight,
  ShieldAlert,
} from 'lucide-react';

export const IncidentsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState<string>('');

  const { data: incidents, isLoading } = useQuery({
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
    <div className="flex-1 flex flex-col font-sans">
      <Header
        title="Production Incidents"
        subtitle="Correlated multi-service incidents detected by ML anomaly models"
        actions={
          <button
            onClick={() => detectMutation.mutate()}
            disabled={detectMutation.isPending}
            className="flex items-center gap-1.5 px-3 py-1 rounded-sm bg-text-primary text-bg-app text-xs font-medium hover:bg-white transition-colors disabled:opacity-50"
          >
            <RefreshCw size={12} className={detectMutation.isPending ? 'animate-spin' : ''} />
            <span>{detectMutation.isPending ? 'Scanning...' : 'Scan Anomaly Pipeline'}</span>
          </button>
        }
      />

      <div className="p-6 space-y-4 max-w-7xl mx-auto w-full">
        {/* Technical Filter Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 bg-bg-surface border border-border-subtle rounded-sm px-4 py-2.5">
          <div className="flex items-center gap-2 flex-1 min-w-[240px]">
            <Search size={14} className="text-text-muted" />
            <input
              type="text"
              placeholder="Filter by ID, incident description, or affected service..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-transparent text-xs text-text-primary placeholder:text-text-muted focus:outline-none w-full"
            />
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs font-mono">
              <span className="text-[11px] text-text-muted">Severity:</span>
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="bg-bg-raised border border-border-subtle rounded-sm text-xs px-2 py-1 text-text-primary focus:outline-none"
              >
                <option value="ALL">All Severities</option>
                <option value="P1_CRITICAL">P1 Critical</option>
                <option value="P2_HIGH">P2 High</option>
                <option value="P3_MEDIUM">P3 Medium</option>
              </select>
            </div>

            <div className="flex items-center gap-1.5 text-xs font-mono">
              <span className="text-[11px] text-text-muted">Status:</span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-bg-raised border border-border-subtle rounded-sm text-xs px-2 py-1 text-text-primary focus:outline-none"
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

        {/* Data Table */}
        <div className="bg-bg-surface border border-border-subtle rounded-sm overflow-hidden">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-border-subtle text-[11px] font-mono text-text-muted uppercase tracking-wider bg-bg-raised/40">
              <tr>
                <th className="py-2.5 px-4 font-normal">Incident ID</th>
                <th className="py-2.5 px-4 font-normal">Title & Description</th>
                <th className="py-2.5 px-3 font-normal">Severity</th>
                <th className="py-2.5 px-3 font-normal">Primary Service</th>
                <th className="py-2.5 px-3 font-normal">Lifecycle Status</th>
                <th className="py-2.5 px-3 font-normal">ML Confidence</th>
                <th className="py-2.5 px-4 font-normal">Detection Time</th>
                <th className="py-2.5 px-4 font-normal text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle">
              {filteredIncidents.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-text-muted">
                    <ShieldAlert size={24} className="mx-auto mb-2 opacity-30" />
                    <p className="text-xs">No incidents match the active search criteria.</p>
                  </td>
                </tr>
              ) : (
                filteredIncidents.map((inc: any) => (
                  <tr key={inc.id} className="hover:bg-bg-hover transition-colors">
                    <td className="py-3 px-4 font-mono font-medium text-text-primary">
                      <Link to={`/incidents/${inc.id}`} className="hover:underline">
                        {inc.id}
                      </Link>
                    </td>
                    <td className="py-3 px-4 max-w-sm">
                      <div className="font-medium text-text-primary truncate">{inc.title}</div>
                      <div className="text-[11px] text-text-secondary truncate mt-0.5">{inc.summary}</div>
                    </td>
                    <td className="py-3 px-3 font-mono">
                      <span
                        className={`px-1.5 py-0.5 rounded-sm text-[10px] uppercase font-medium ${
                          inc.severity === 'P1_CRITICAL'
                            ? 'text-status-coral bg-status-coral/10 border border-status-coral/25'
                            : 'text-status-amber bg-status-amber/10 border border-status-amber/25'
                        }`}
                      >
                        {inc.severity}
                      </span>
                    </td>
                    <td className="py-3 px-3 font-mono text-text-secondary">{inc.primary_service_id}</td>
                    <td className="py-3 px-3">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm text-[10px] font-mono uppercase ${
                          inc.status === 'RESOLVED'
                            ? 'text-status-sage bg-status-sage/10 border border-status-sage/20'
                            : inc.status === 'INVESTIGATING'
                            ? 'text-status-amber bg-status-amber/10 border border-status-amber/20 animate-pulse'
                            : 'text-text-secondary bg-bg-raised border border-border-subtle'
                        }`}
                      >
                        <span
                          className={`w-1 h-1 rounded-full ${
                            inc.status === 'RESOLVED'
                              ? 'bg-status-sage'
                              : inc.status === 'INVESTIGATING'
                              ? 'bg-status-amber'
                              : 'bg-text-muted'
                          }`}
                        />
                        {inc.status}
                      </span>
                    </td>
                    <td className="py-3 px-3 font-mono text-text-secondary">
                      {inc.ml_confidence ? `${(inc.ml_confidence * 100).toFixed(0)}%` : '—'}
                    </td>
                    <td className="py-3 px-4 font-mono text-[11px] text-text-muted">
                      {inc.detected_at?.replace('T', ' ').slice(0, 19)}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Link
                        to={`/incidents/${inc.id}`}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-sm bg-bg-raised border border-border-primary hover:border-text-secondary text-text-primary text-xs font-mono transition-colors"
                      >
                        <span>Investigate</span>
                        <ArrowRight size={12} className="text-text-muted" />
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
