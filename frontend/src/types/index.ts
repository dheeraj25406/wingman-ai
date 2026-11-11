export interface ServiceMetric {
  cpu_utilization: number;
  memory_utilization: number;
  request_rate: number;
  error_rate: number;
  latency_p50: number;
  latency_p95: number;
  latency_p99: number;
  db_connections: number;
  queue_depth: number;
  timeout_rate: number;
  timestamp: string;
}

export interface ServiceItem {
  id: string;
  name: string;
  status: 'healthy' | 'degraded' | 'critical';
  dependencies: string[];
  active_fault?: string | null;
  latest_metrics: {
    cpu_utilization: number;
    memory_utilization: number;
    error_rate: number;
    latency_p95: number;
    request_rate: number;
    db_connections: number;
  };
}

export interface MetricsOverviewData {
  total_services: number;
  healthy_services: number;
  degraded_services: number;
  critical_services: number;
  global_error_rate: number;
  avg_latency_p95: number;
  total_throughput_rps: number;
  active_incidents_count: number;
}

export interface IncidentEvent {
  id: string;
  event_type: string;
  description: string;
  created_at: string;
}

export interface EvidenceItem {
  id: string;
  evidence_type: string;
  service_id: string;
  headline: string;
  details: Record<string, any>;
  confidence_score: number;
  timestamp: string;
}

export interface HypothesisItem {
  id: string;
  rank: number;
  root_cause: string;
  confidence_score: number;
  explanation: string;
  supporting_evidence_ids: string[];
  contradictory_evidence_ids: string[];
  affected_services: string[];
  recommended_remediation: string;
  status?: string;
}

export interface RemediationProposal {
  id: string;
  action_type: string;
  target_service_id: string;
  parameters?: Record<string, any>;
  justification: string;
  risk_assessment: string;
  status: 'PENDING_APPROVAL' | 'APPROVED' | 'REJECTED' | 'EXECUTED';
  created_at?: string;
}

export interface IncidentItem {
  id: string;
  title: string;
  severity: 'P1_CRITICAL' | 'P2_HIGH' | 'P3_MEDIUM' | 'P4_LOW';
  status: 'DETECTED' | 'INVESTIGATING' | 'IDENTIFIED' | 'MITIGATING' | 'RESOLVED' | 'CLOSED';
  primary_service_id: string;
  affected_service_ids: string[];
  detection_source: string;
  detected_at: string;
  mitigated_at?: string | null;
  resolved_at?: string | null;
  summary?: string | null;
  anomaly_score?: number;
  predicted_category?: string;
  ml_confidence?: number;
  timeline: IncidentEvent[];
  evidence: EvidenceItem[];
  hypotheses: HypothesisItem[];
  remediation_proposal?: RemediationProposal | null;
}

export interface ActiveFaultItem {
  id: string;
  fault_type: string;
  target_service_id: string;
  intensity: number;
  duration_seconds: number;
  expected_root_cause: string;
  expected_affected_services: string[];
  elapsed_seconds: number;
}

export interface EvaluationCase {
  scenario_name: string;
  ground_truth_cause: string;
  predicted_cause: string;
  is_top1_match: boolean;
  is_top3_match: boolean;
  evidence_count: number;
  passed: boolean;
  latency_ms: number;
}

export interface EvaluationRun {
  run_id: string;
  benchmark_name: string;
  total_cases: number;
  top1_accuracy: number;
  top3_accuracy: number;
  remediation_validity: number;
  unsafe_actions_count: number;
  avg_latency_ms: number;
  executed_at: string;
  cases: EvaluationCase[];
}
