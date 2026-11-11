import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ReactFlow,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  Position,
  Handle,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { api } from '../services/api';
import { Header } from '../components/Header';
import { Server, Database, ArrowRight } from 'lucide-react';

const CustomServiceNode = ({ data }: any) => {
  const isCritical = data.status === 'critical';
  const isDegraded = data.status === 'degraded';

  return (
    <div
      className={`px-3 py-2.5 rounded-sm bg-bg-surface border text-xs min-w-[160px] font-sans transition-colors ${
        isCritical
          ? 'border-status-coral/70 bg-bg-surface'
          : isDegraded
          ? 'border-status-amber/70 bg-bg-surface'
          : 'border-border-primary hover:border-text-secondary bg-bg-surface'
      }`}
    >
      <Handle type="target" position={Position.Top} className="!bg-border-strong !w-1.5 !h-1.5" />
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-1.5">
          {data.isDb ? <Database size={12} className="text-text-muted" /> : <Server size={12} className="text-text-muted" />}
          <span className="font-mono font-medium text-text-primary text-[11px]">{data.label}</span>
        </div>
        <span
          className={`w-1.5 h-1.5 rounded-full ${
            isCritical ? 'bg-status-coral animate-ping' : isDegraded ? 'bg-status-amber' : 'bg-status-sage'
          }`}
        />
      </div>

      <div className="space-y-0.5 text-[10px] font-mono text-text-muted">
        <div className="flex justify-between">
          <span>P95:</span>
          <span className="text-text-primary">{data.p95?.toFixed(1) || 30.0}ms</span>
        </div>
        <div className="flex justify-between">
          <span>Err:</span>
          <span className={data.err > 0.05 ? 'text-status-coral font-medium' : 'text-text-primary'}>
            {((data.err || 0) * 100).toFixed(1)}%
          </span>
        </div>
      </div>

      {data.fault && (
        <div className="mt-1 px-1.5 py-0.2 rounded-sm bg-status-coral/15 text-status-coral text-[9px] font-mono truncate border border-status-coral/30">
          {data.fault}
        </div>
      )}
      <Handle type="source" position={Position.Bottom} className="!bg-border-strong !w-1.5 !h-1.5" />
    </div>
  );
};

const nodeTypes = { serviceNode: CustomServiceNode };

export const ServiceMapPage: React.FC = () => {
  const [selectedService, setSelectedService] = useState<string | null>('order-service');

  const { data: services } = useQuery({
    queryKey: ['services'],
    queryFn: api.getServices,
    refetchInterval: 3000,
  });

  const getServiceData = (id: string) => {
    const s = (services || []).find((x: any) => x.id === id);
    return {
      label: id,
      status: s?.status || 'healthy',
      p95: s?.latest_metrics?.latency_p95 || 35.0,
      err: s?.latest_metrics?.error_rate || 0.0,
      fault: s?.active_fault,
      isDb: id === 'database',
    };
  };

  const initialNodes = [
    {
      id: 'api-gateway',
      type: 'serviceNode',
      position: { x: 300, y: 30 },
      data: getServiceData('api-gateway'),
    },
    {
      id: 'user-service',
      type: 'serviceNode',
      position: { x: 80, y: 160 },
      data: getServiceData('user-service'),
    },
    {
      id: 'product-service',
      type: 'serviceNode',
      position: { x: 300, y: 160 },
      data: getServiceData('product-service'),
    },
    {
      id: 'checkout-service',
      type: 'serviceNode',
      position: { x: 520, y: 160 },
      data: getServiceData('checkout-service'),
    },
    {
      id: 'payment-service',
      type: 'serviceNode',
      position: { x: 420, y: 300 },
      data: getServiceData('payment-service'),
    },
    {
      id: 'order-service',
      type: 'serviceNode',
      position: { x: 630, y: 300 },
      data: getServiceData('order-service'),
    },
    {
      id: 'database',
      type: 'serviceNode',
      position: { x: 630, y: 440 },
      data: { label: 'PostgreSQL DB', status: 'healthy', p95: 12.0, err: 0.0, isDb: true },
    },
  ];

  const initialEdges = [
    {
      id: 'e-gw-user',
      source: 'api-gateway',
      target: 'user-service',
      animated: true,
      style: { stroke: '#303030' },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#303030' },
    },
    {
      id: 'e-gw-prod',
      source: 'api-gateway',
      target: 'product-service',
      animated: true,
      style: { stroke: '#303030' },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#303030' },
    },
    {
      id: 'e-gw-check',
      source: 'api-gateway',
      target: 'checkout-service',
      animated: true,
      style: { stroke: '#303030' },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#303030' },
    },
    {
      id: 'e-check-pay',
      source: 'checkout-service',
      target: 'payment-service',
      animated: true,
      style: { stroke: '#303030' },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#303030' },
    },
    {
      id: 'e-check-ord',
      source: 'checkout-service',
      target: 'order-service',
      animated: true,
      style: { stroke: '#303030' },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#303030' },
    },
    {
      id: 'e-ord-db',
      source: 'order-service',
      target: 'database',
      animated: true,
      style: { stroke: '#303030' },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#303030' },
    },
  ];

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  const selectedSvcDetails = (services || []).find((s: any) => s.id === selectedService);

  return (
    <div className="flex-1 flex flex-col h-full font-sans">
      <Header
        title="Service Dependency Topology"
        subtitle="Live microservice DAG with active fault propagation"
      />

      <div className="flex-1 flex relative">
        {/* Near-black Canvas */}
        <div className="flex-1 h-[calc(100vh-3rem)] bg-bg-app">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            onNodeClick={(_, node) => setSelectedService(node.id)}
            fitView
          >
            <Background color="#1B1B1B" gap={18} size={1} />
            <Controls className="!bg-bg-surface !border-border-subtle !fill-text-primary !rounded-sm" />
          </ReactFlow>
        </div>

        {/* Selected Service Detail Drawer */}
        {selectedSvcDetails && (
          <div className="w-80 bg-bg-surface border-l border-border-subtle p-5 flex flex-col justify-between overflow-y-auto">
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-border-subtle">
                <div>
                  <h3 className="text-xs font-mono font-bold text-text-primary">{selectedSvcDetails.id}</h3>
                  <span className="text-[11px] text-text-muted">{selectedSvcDetails.name}</span>
                </div>
                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded-sm uppercase ${
                    selectedSvcDetails.status === 'healthy'
                      ? 'text-status-sage bg-status-sage/10 border border-status-sage/20'
                      : 'text-status-coral bg-status-coral/10 border border-status-coral/20'
                  }`}
                >
                  {selectedSvcDetails.status}
                </span>
              </div>

              {selectedSvcDetails.active_fault && (
                <div className="p-3 bg-status-coral/10 border border-status-coral/25 rounded-sm text-xs space-y-1">
                  <span className="text-status-coral font-mono text-[10px] uppercase font-bold block">
                    Active Injected Fault
                  </span>
                  <p className="font-mono text-text-primary">{selectedSvcDetails.active_fault}</p>
                </div>
              )}

              {/* Telemetry snapshot */}
              <div className="space-y-2">
                <span className="text-[10px] font-mono uppercase text-text-muted block">
                  Current Telemetry
                </span>
                <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                  <div className="p-2 bg-bg-raised rounded-sm border border-border-subtle">
                    <span className="text-[10px] text-text-muted block">CPU</span>
                    <span className="text-text-primary font-medium">
                      {selectedSvcDetails.latest_metrics?.cpu_utilization?.toFixed(1)}%
                    </span>
                  </div>
                  <div className="p-2 bg-bg-raised rounded-sm border border-border-subtle">
                    <span className="text-[10px] text-text-muted block">Memory</span>
                    <span className="text-text-primary font-medium">
                      {selectedSvcDetails.latest_metrics?.memory_utilization?.toFixed(1)}%
                    </span>
                  </div>
                  <div className="p-2 bg-bg-raised rounded-sm border border-border-subtle">
                    <span className="text-[10px] text-text-muted block">Latency P95</span>
                    <span className="text-text-primary font-medium">
                      {selectedSvcDetails.latest_metrics?.latency_p95?.toFixed(1)}ms
                    </span>
                  </div>
                  <div className="p-2 bg-bg-raised rounded-sm border border-border-subtle">
                    <span className="text-[10px] text-text-muted block">Error Rate</span>
                    <span
                      className={
                        selectedSvcDetails.latest_metrics?.error_rate > 0.05
                          ? 'text-status-coral font-medium'
                          : 'text-text-primary'
                      }
                    >
                      {((selectedSvcDetails.latest_metrics?.error_rate || 0) * 100).toFixed(2)}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Dependencies */}
              <div className="space-y-2">
                <span className="text-[10px] font-mono uppercase text-text-muted block">
                  Downstream Dependencies
                </span>
                <div className="space-y-1">
                  {selectedSvcDetails.dependencies?.length ? (
                    selectedSvcDetails.dependencies.map((dep: string) => (
                      <div
                        key={dep}
                        className="px-2.5 py-1.5 rounded-sm bg-bg-raised border border-border-subtle text-xs font-mono text-text-primary flex items-center justify-between"
                      >
                        <span>{dep}</span>
                        <ArrowRight size={12} className="text-text-muted" />
                      </div>
                    ))
                  ) : (
                    <span className="text-xs text-text-muted font-mono">None (Leaf service)</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
