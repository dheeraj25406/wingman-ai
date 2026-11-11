import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { Header } from '../components/Header';
import {
  Play,
  Database,
  Cpu,
  Layers,
  HardDrive,
  GitCommit,
  Clock,
  AlertTriangle,
} from 'lucide-react';

export const FaultLabPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedFault, setSelectedFault] = useState<string>('db_pool_exhaustion');
  const [intensity, setIntensity] = useState<number>(0.85);
  const [duration, setDuration] = useState<number>(180);
  const [targetService, setTargetService] = useState<string>('order-service');

  const { data: faultsData } = useQuery({
    queryKey: ['faults'],
    queryFn: api.getFaults,
    refetchInterval: 2500,
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
      desc: 'Saturates PostgreSQL connection pool (100/100 active connections) triggering query acquisition timeouts.',
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
    <div className="flex-1 flex flex-col font-sans">
      <Header
        title="Controlled Fault Lab"
        subtitle="Safe, isolated telemetry disruption injection for testing ML detection and agent workflows"
      />

      <div className="p-6 space-y-6 max-w-7xl mx-auto w-full">
        {/* Active Fault Injections Section */}
        <section className="border border-border-subtle bg-bg-surface rounded-sm p-5 space-y-3">
          <div className="flex items-center justify-between pb-3 border-b border-border-subtle">
            <span className="text-xs font-medium text-text-primary uppercase tracking-wider font-mono">
              Active Injected Faults ({activeFaults.length})
            </span>
            {activeFaults.length > 0 ? (
              <span className="text-[10px] font-mono text-status-coral uppercase">
                Degradation Active
              </span>
            ) : (
              <span className="text-[10px] font-mono text-text-muted uppercase">
                Clean Telemetry Baseline
              </span>
            )}
          </div>

          {activeFaults.length === 0 ? (
            <div className="py-6 text-center text-text-muted text-xs font-mono">
              No active fault injections running. Fleet is operating within normal baseline telemetry.
            </div>
          ) : (
            <div className="space-y-2">
              {activeFaults.map((f: any) => (
                <div
                  key={f.id}
                  className="p-3 bg-bg-raised border border-border-primary rounded-sm flex items-center justify-between text-xs"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-status-coral font-medium">{f.fault_type}</span>
                      <span className="text-text-muted text-[11px] font-mono">on</span>
                      <span className="font-mono text-text-primary">{f.target_service_id}</span>
                      <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-sm bg-bg-surface text-text-muted border border-border-subtle">
                        {(f.intensity * 100).toFixed(0)}% Intensity
                      </span>
                    </div>
                    <div className="text-[11px] text-text-secondary">
                      <span className="text-text-muted font-mono">Ground-Truth Root Cause: </span>
                      <span>{f.expected_root_cause}</span>
                    </div>
                  </div>

                  <button
                    onClick={() => stopMutation.mutate(f.id)}
                    disabled={stopMutation.isPending}
                    className="px-2.5 py-1 rounded-sm bg-bg-surface border border-border-subtle hover:border-text-secondary text-text-primary text-xs font-mono transition-colors disabled:opacity-50"
                  >
                    Halt Simulation
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Fault Scenario Catalog (Grid) */}
        <div>
          <span className="text-xs font-medium text-text-primary uppercase tracking-wider font-mono block mb-3">
            Available Fault Scenarios (7)
          </span>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {faultCatalog.map((item) => {
              const Icon = item.icon;
              const isSelected = selectedFault === item.type;
              return (
                <div
                  key={item.type}
                  onClick={() => handleSelectFault(item)}
                  className={`p-4 rounded-sm border text-xs cursor-pointer transition-colors ${
                    isSelected
                      ? 'bg-bg-raised border-text-primary'
                      : 'bg-bg-surface border-border-subtle hover:border-border-primary'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <Icon size={14} className={isSelected ? 'text-text-primary' : 'text-text-muted'} />
                    <span className="font-medium text-text-primary text-xs">{item.name}</span>
                  </div>
                  <p className="text-[11px] text-text-secondary leading-relaxed mb-2.5">{item.desc}</p>
                  <div className="text-[10px] font-mono text-text-muted">Target Service: {item.defaultService}</div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Injection Parameter Controls & Trigger */}
        <section className="border border-border-subtle bg-bg-surface rounded-sm p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-border-subtle">
            <span className="text-xs font-medium text-text-primary uppercase tracking-wider font-mono">
              Simulation Parameters: {selectedFault}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <div className="flex justify-between text-xs font-mono mb-2">
                <span className="text-text-muted">Fault Intensity:</span>
                <span className="text-text-primary font-medium">{(intensity * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0.2"
                max="1.0"
                step="0.05"
                value={intensity}
                onChange={(e) => setIntensity(parseFloat(e.target.value))}
                className="w-full accent-text-primary cursor-pointer"
              />
              <span className="text-[10px] text-text-muted mt-1 block font-mono">Higher intensity forces steeper latency & error spikes</span>
            </div>

            <div>
              <div className="flex justify-between text-xs font-mono mb-2">
                <span className="text-text-muted">Duration (Seconds):</span>
                <span className="text-text-primary font-medium">{duration}s</span>
              </div>
              <input
                type="range"
                min="30"
                max="600"
                step="30"
                value={duration}
                onChange={(e) => setDuration(parseInt(e.target.value))}
                className="w-full accent-text-primary cursor-pointer"
              />
              <span className="text-[10px] text-text-muted mt-1 block font-mono">Fault auto-terminates after countdown</span>
            </div>

            <div>
              <span className="text-xs text-text-muted block mb-2 font-mono">Target Service:</span>
              <select
                value={targetService}
                onChange={(e) => setTargetService(e.target.value)}
                className="w-full bg-bg-raised border border-border-subtle rounded-sm text-xs px-2.5 py-1.5 text-text-primary font-mono focus:outline-none focus:border-border-strong"
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
              className="flex items-center gap-1.5 px-4 py-1.5 rounded-sm bg-text-primary text-bg-app font-medium text-xs hover:bg-white transition-colors disabled:opacity-50"
            >
              <Play size={12} />
              <span>{injectMutation.isPending ? 'Injecting Fault...' : 'Inject Fault into Telemetry Pipeline'}</span>
            </button>
          </div>
        </section>
      </div>
    </div>
  );
};
