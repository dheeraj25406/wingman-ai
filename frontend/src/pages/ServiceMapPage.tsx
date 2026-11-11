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
import { Server, Database, AlertCircle, CheckCircle, ArrowRight } from 'lucide-react';

const CustomServiceNode = ({ data }: any) => {
  const isCritical = data.status === 'critical';
  const isDegraded = data.status === 'degraded';

  return (
    <div
      className={`px-4 py-3 rounded-md bg-bg-surface border text-xs shadow-lg min-w-[170px] transition-all ${
        isCritical
          ? 'border-status-critical ring-1 ring-status-critical/30'
          : isDegraded
          ? 'border-status-warning'
          : 'border-border-strong hover:border-accent'
      }`}
    >
      <Handle type="target" position={Position.Top} className="!bg-border-strong" />
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-1.5">
          {data.isDb ? <Database size={13} className="text-accent" /> : <Server size={13} className="text-accent" />}
          <span className="font-mono font-bold text-text-primary text-[11px]">{data.label}</span>
        </div>
        <span
          className={`w-2 h-2 rounded-full ${
            isCritical ? 'bg-status-critical animate-ping' : isDegraded ? 'bg-status-warning' : 'bg-status-success'
          }`}
        />
      </div>

      <div className="space-y-0.5 text-[10px] font-mono text-text-secondary">
        <div className="flex justify-between">
          <span>P95:</span>
          <span className="text-text-primary">{data.p95?.toFixed(1) || 30.0}ms</span>
        </div>
        <div className="flex justify-between">
          <span>Err:</span>
          <span className={data.err > 0.05 ? 'text-status-critical font-bold' : 'text-text-primary'}>
            {((data.err || 0) * 100).toFixed(1)}%
          </span>
        </div>
      </div>

      {data.fault && (
        <div className="mt-1.5 px-1.5 py-0.5 rounded bg-status-critical/20 text-status-critical text-[9px] font-mono font-bold truncate border border-status-critical/30">
          {data.fault}
        </div>
      )}
      <Handle type="source" position={Position.Bottom} className="!bg-border-strong" />
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
      style: { stroke: '#647184' },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#647184' },
    },
    {
      id: 'e-gw-prod',
      source: 'api-gateway',
      target: 'product-service',
      animated: true,
      style: { stroke: '#647184' },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#647184' },
    },
    {
      id: 'e-gw-check',
      source: 'api-gateway',
      target: 'checkout-service',
      animated: true,
      style: { stroke: '#647184' },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#647184' },
    },
    {
      id: 'e-check-pay',
      source: 'checkout-service',
      target: 'payment-service',
      animated: true,
      style: { stroke: '#647184' },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#647184' },
    },
    {
      id: 'e-check-ord',
      source: 'checkout-service',
      target: 'order-service',
      animated: true,
      style: { stroke: '#647184' },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#647184' },
    },
    {
      id: 'e-ord-db',
      source: 'order-service',
      target: 'database',
      animated: true,
      style: { stroke: '#647184' },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#647184' },
    },
  ];

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  const selectedSvcDetails = (services || []).find((s: any) => s.id === selectedService);

  return (
    <div className="flex-1 flex flex-col h-full">
      <Header
        title="Interactive Service Dependency Graph"
        subtitle="Distributed microservice call graph with active anomaly propagation and latency tracking"
      />

      <div className="flex-1 flex relative">
        {/* React Flow Canvas */}
        <div className="flex-1 h-[calc(100vh-3.5rem)] bg-bg-app">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            onNodeClick={(_, node) => setSelectedService(node.id)}
            fitView
          >
            <Background color="#1A2430" gap={16} />
            <Controls className="!bg-bg-surface !border-border-subtle !fill-text-primary" />
          </ReactFlow>
        </div>

        {/* Selected Service Detail Drawer */}
        {selectedSvcDetails && (
          <div className="w-80 bg-bg-surface border-l border-border-subtle p-5 flex flex-col justify-between overflow-y-auto">
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-border-subtle">
                <div>
                  <h3 className="text-sm font-bold font-mono text-accent">{selectedSvcDetails.id}</h3>
                  <span className="text-[11px] text-text-muted">{selectedSvcDetails.name}</span>
                </div>
                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold uppercase ${
                    selectedSvcDetails.status === 'healthy'
                      ? 'bg-status-success/20 text-status-success'
                      : 'bg-status-critical/20 text-status-critical'
                  }`}
                >
                  {selectedSvcDetails.status}
                </span>
              </div>

              {selectedSvcDetails.active_fault && (
                <div className="p-3 bg-status-critical/15 border border-status-critical/30 rounded text-xs space-y-1">
                  <span className="text-status-critical font-bold block text-[11px]">ACTIVE INJECTED FAULT</span>
                  <p className="font-mono text-text-primary">{selectedSvcDetails.active_fault}</p>
                </div>
              )}

              {/* Service metrics snapshot */}
              <div className="space-y-2">
                <span className="text-[11px] font-medium text-text-secondary uppercase tracking-wider block">
                  Current Telemetry
                </span>
                <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                  <div className="p-2 bg-bg-raised rounded border border-border-subtle">
                    <span className="text-[10px] text-text-muted block">CPU</span>
                    <span className="font-bold text-text-primary">
                      {selectedSvcDetails.latest_metrics?.cpu_utilization?.toFixed(1)}%
                    </span>
                  </div>
                  <div className="p-2 bg-bg-raised rounded border border-border-subtle">
                    <span className="text-[10px] text-text-muted block">Memory</span>
                    <span className="font-bold text-text-primary">
                      {selectedSvcDetails.latest_metrics?.memory_utilization?.toFixed(1)}%
                    </span>
                  </div>
                  <div className="p-2 bg-bg-raised rounded border border-border-subtle">
                    <span className="text-[10px] text-text-muted block">Latency P95</span>
                    <span className="font-bold text-text-primary">
                      {selectedSvcDetails.latest_metrics?.latency_p95?.toFixed(1)}ms
                    </span>
                  </div>
                  <div className="p-2 bg-bg-raised rounded border border-border-subtle">
                    <span className="text-[10px] text-text-muted block">Error Rate</span>
                    <span
                      className={`font-bold ${
                        selectedSvcDetails.latest_metrics?.error_rate > 0.05
                          ? 'text-status-critical'
                          : 'text-text-primary'
                      }`}
                    >
                      {((selectedSvcDetails.latest_metrics?.error_rate || 0) * 100).toFixed(2)}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Dependencies */}
              <div>
                <span className="text-[11px] font-medium text-text-secondary uppercase tracking-wider block mb-2">
                  Downstream Dependencies
                </span>
                <div className="space-y-1">
                  {selectedSvcDetails.dependencies?.length ? (
                    selectedSvcDetails.dependencies.map((dep: string) => (
                      <div
                        key={dep}
                        className="px-2.5 py-1.5 rounded bg-bg-raised border border-border-subtle text-xs font-mono text-text-primary flex items-center justify-between"
                      >
                        <span>{dep}</span>
                        <ArrowRight size={12} className="text-text-muted" />
                      </div>
                    ))
                  ) : (
                    <span className="text-xs text-text-muted">Leaf service (No downstream dependencies)</span>
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
