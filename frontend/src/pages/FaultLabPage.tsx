import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { Header } from '../components/Header';
import {
  FlaskConical,
  Play,
  Square,
  AlertTriangle,
  Zap,
  Clock,
  Sliders,
  ShieldAlert,
  Database,
  Cpu,
  Layers,
  HardDrive,
  GitCommit,
} from 'lucide-react';

export const FaultLabPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedFault, setSelectedFault] = useState<string>('db_pool_exhaustion');
  const [intensity, setIntensity] = useState<number>(0.85);
  const [duration, setDuration] = useState<number>(180);
  const [targetService, setTargetService] = useState<string>('order-service');

  const { data: faultsData, isLoading } = useQuery({
    queryKey: ['faults'],
    queryFn: api.getFaults,
    refetchInterval: 2500,
  });

  const { data: trafficData } = useQuery({
    queryKey: ['traffic'],
    queryFn: api.getTraffic,
    refetchInterval: 3000,
  });

  const injectMutation = useMutation({
    mutationFn: () =>
      api.injectFault({
        fault_type: selectedFault,
        target_service_id: targetService,
        intensity: intensity,
        duration_seconds: duration,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['faults'] });
      queryClient.invalidateQueries({ queryKey: ['services'] });
      queryClient.invalidateQueries({ queryKey: ['metrics-overview'] });
    },
  });

  const stopMutation = useMutation({
    mutationFn: (id: string) => api.stopFault(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['faults'] });
      queryClient.invalidateQueries({ queryKey: ['services'] });
    },
  });

  const activeFaults = faultsData?.active_faults || [];

  const faultCatalog = [
    {
      type: 'db_pool_exhaustion',
      name: 'DB Connection Pool Exhaustion',
      defaultService: 'order-service',
      icon: Database,
      desc: 'Simulates PostgreSQL connection saturation (100/100 active connections) causing query acquisition timeouts.',
      expectedCause: 'Database connection pool exhausted due to unreleased client connections',
    },
    {
      type: 'cpu_saturation',
      name: 'CPU Saturation / Compute Starvation',
      defaultService: 'checkout-service',
      icon: Cpu,
      desc: 'Saturates container CPU utilization to 98%+, spiking latency and triggering request timeouts.',
      expectedCause: 'CPU starvation due to unthrottled computation loop',
    },
    {
      type: 'memory_pressure',
      name: 'Memory Pressure / Heap Leak',
      defaultService: 'product-service',
      icon: HardDrive,
      desc: 'Simulates rapid heap growth to 95% capacity, causing severe garbage collection pauses.',
      expectedCause: 'Memory leak in cache retention table',
    },
    {
      type: 'downstream_latency',
      name: 'Downstream Payment Latency',
      defaultService: 'payment-service',
      icon: Clock,
      desc: 'Injects 3500ms response delays into 3rd-party banking partner integration calls.',
      expectedCause: 'External banking provider latency timeout',
    },
    {
      type: 'downstream_failure',
      name: 'Downstream Outage (HTTP 503)',
      defaultService: 'payment-service',
      icon: AlertTriangle,
      desc: 'Returns HTTP 503 Service Unavailable errors on payment authorization requests.',
      expectedCause: 'Downstream provider handshake connection refused',
    },
    {
      type: 'queue_backlog',
      name: 'Async Order Queue Backlog',
      defaultService: 'order-service',
      icon: Layers,
      desc: 'Simulates order ingestion queue accumulation beyond 10,000 pending tasks.',
      expectedCause: 'Worker thread deadlock preventing queue message consumption',
    },
    {
      type: 'bad_deployment',
      name: 'Bad Deployment / Config Regression',
      defaultService: 'user-service',
      icon: GitCommit,
      desc: 'Simulates missing environment variable in new release v2.4.1 throwing runtime KeyErrors.',
      expectedCause: 'Deployment configuration regression: missing JWT_SECRET_KEY env var',
    },
  ];

  const handleSelectFault = (item: any) => {
    setSelectedFault(item.type);
    setTargetService(item.defaultService);
  };

  return (
    <div className="flex-1 flex flex-col">
      <Header
        title="Controlled Fault Injection Lab"
        subtitle="Safe, isolated production failure simulations to test ML anomaly detection and autonomous agent investigation"
      />

      <div className="p-6 space-y-6">
        {/* Active Injected Faults Panel */}
        <div className="bg-bg-surface border border-border-subtle rounded-md p-5 space-y-3">
          <div className="flex items-center justify-between pb-3 border-b border-border-subtle">
            <div className="flex items-center gap-2">
              <FlaskConical size={16} className="text-status-critical" />
              <h2 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                Active Injected Faults ({activeFaults.length})
              </h2>
            </div>
            {activeFaults.length > 0 && (
              <span className="text-[11px] font-mono text-status-critical animate-pulse font-semibold">
                Telemetry degradation active
              </span>
            )}
          </div>

          {activeFaults.length === 0 ? (
            <div className="py-6 text-center text-text-muted text-xs">
              No active fault simulations running. The fleet is operating under normal baseline traffic.
            </div>
          ) : (
            <div className="space-y-2">
              {activeFaults.map((f: any) => (
                <div
                  key={f.id}
                  className="p-3 bg-bg-raised border border-status-critical/30 rounded flex items-center justify-between text-xs"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-status-critical">{f.fault_type}</span>
                      <span className="text-text-muted text-[11px]">on</span>
                      <span className="font-mono text-accent">{f.target_service_id}</span>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-bg-surface text-text-secondary">
                        Intensity: {(f.intensity * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div className="text-[11px] text-text-secondary">
                      <span className="text-text-muted">Ground-Truth Cause (Isolated from Agent): </span>
                      <span className="font-medium text-text-primary">{f.expected_root_cause}</span>
                    </div>
                  </div>

                  <button
                    onClick={() => stopMutation.mutate(f.id)}
                    disabled={stopMutation.isPending}
                    className="px-3 py-1.5 rounded bg-status-critical/15 text-status-critical border border-status-critical/30 text-xs font-mono font-semibold hover:bg-status-critical/25 transition-colors disabled:opacity-50"
                  >
                    Stop Simulation
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Fault Selector Grid */}
        <div>
          <h2 className="text-xs font-semibold text-text-primary uppercase tracking-wider mb-3">
            Select Controlled Failure Scenario
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {faultCatalog.map((item) => {
              const Icon = item.icon;
              const isSelected = selectedFault === item.type;
              return (
                <div
                  key={item.type}
                  onClick={() => handleSelectFault(item)}
                  className={`p-4 rounded-md border text-xs cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-bg-raised border-accent ring-1 ring-accent/40'
                      : 'bg-bg-surface border-border-subtle hover:border-border-strong'
                  }`}
                >
                  <div className="flex items-center gap-2.5 mb-2">
                    <div
                      className={`w-7 h-7 rounded flex items-center justify-center ${
                        isSelected ? 'bg-accent/20 text-accent' : 'bg-bg-raised text-text-muted'
                      }`}
                    >
                      <Icon size={14} />
                    </div>
                    <span className="font-semibold text-text-primary text-xs">{item.name}</span>
                  </div>
                  <p className="text-[11px] text-text-secondary leading-relaxed mb-2">{item.desc}</p>
                  <div className="text-[10px] font-mono text-text-muted">Target: {item.defaultService}</div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Configuration Sliders & Inject Action */}
        <div className="bg-bg-surface border border-border-subtle rounded-md p-5 space-y-4">
          <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
            Injection Parameters ({selectedFault})
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <label className="text-[11px] font-medium text-text-secondary flex justify-between mb-1.5">
                <span>Fault Intensity:</span>
                <span className="font-mono text-accent font-bold">{(intensity * 100).toFixed(0)}%</span>
              </label>
              <input
                type="range"
                min="0.2"
                max="1.0"
                step="0.05"
                value={intensity}
                onChange={(e) => setIntensity(parseFloat(e.target.value))}
                className="w-full accent-accent cursor-pointer"
              />
              <span className="text-[10px] text-text-muted mt-1 block">Higher intensity increases error rate & latency impact</span>
            </div>

            <div>
              <label className="text-[11px] font-medium text-text-secondary flex justify-between mb-1.5">
                <span>Duration (Seconds):</span>
                <span className="font-mono text-accent font-bold">{duration}s</span>
              </label>
              <input
                type="range"
                min="30"
                max="600"
                step="30"
                value={duration}
                onChange={(e) => setDuration(parseInt(e.target.value))}
                className="w-full accent-accent cursor-pointer"
              />
              <span className="text-[10px] text-text-muted mt-1 block">Fault will automatically expire after duration</span>
            </div>

            <div>
              <label className="text-[11px] font-medium text-text-secondary block mb-1.5">Target Microservice:</label>
              <select
                value={targetService}
                onChange={(e) => setTargetService(e.target.value)}
                className="w-full bg-bg-raised border border-border-subtle rounded text-xs px-3 py-1.5 text-text-primary font-mono focus:outline-none focus:border-accent"
              >
                <option value="order-service">order-service</option>
                <option value="checkout-service">checkout-service</option>
                <option value="payment-service">payment-service</option>
                <option value="user-service">user-service</option>
                <option value="product-service">product-service</option>
                <option value="api-gateway">api-gateway</option>
              </select>
            </div>
          </div>

          <div className="pt-3 border-t border-border-subtle flex justify-end">
            <button
              onClick={() => injectMutation.mutate()}
              disabled={injectMutation.isPending}
              className="flex items-center gap-2 px-5 py-2 rounded bg-status-critical text-bg-app font-semibold text-xs hover:bg-status-critical/90 transition-colors disabled:opacity-50"
            >
              <Play size={14} />
              <span>{injectMutation.isPending ? 'Injecting Fault...' : 'Inject Fault into Telemetry Pipeline'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
