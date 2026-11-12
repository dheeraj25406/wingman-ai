const API_BASE = '/api';

export async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({ detail: 'Network request failed' }));
    throw new Error(errorBody.detail || `Request failed with status ${res.status}`);
  }

  const json = await res.json();
  return json.data !== undefined ? json.data : json;
}

export const api = {
  // System Health
  getHealth: () => fetchApi<any>('/health'),

  // Services
  getServices: () => fetchApi<any[]>('/services'),
  getService: (id: string) => fetchApi<any>(`/services/${id}`),

  // Metrics
  getMetricsOverview: () => fetchApi<any>('/metrics/overview'),
  getServiceMetrics: (id: string, limit: number = 30) => fetchApi<any[]>(`/metrics/services/${id}?limit=${limit}`),

  // Incidents
  getIncidents: (status?: string, severity?: string) => {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (severity) params.append('severity', severity);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return fetchApi<any[]>(`/incidents${qs}`);
  },
  getIncident: (id: string) => fetchApi<any>(`/incidents/${id}`),
  detectIncidents: () => fetchApi<any>('/incidents/detect', { method: 'POST' }),
  investigateIncident: (id: string) => fetchApi<any>(`/incidents/${id}/investigate`, { method: 'POST' }),
  approveRemediation: (id: string, proposalId: string, notes?: string) =>
    fetchApi<any>(`/incidents/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ proposal_id: proposalId, operator_notes: notes }),
    }),
  rejectRemediation: (id: string, proposalId: string, notes?: string) =>
    fetchApi<any>(`/incidents/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ proposal_id: proposalId, operator_notes: notes }),
    }),

  // Faults
  getFaults: () => fetchApi<any>('/faults'),
  injectFault: (data: { fault_type: string; target_service_id: string; intensity: number; duration_seconds: number }) =>
    fetchApi<any>('/faults/inject', { method: 'POST', body: JSON.stringify(data) }),
  stopFault: (id: string) => fetchApi<any>(`/faults/${id}/stop`, { method: 'POST' }),

  // Models
  getModelsOverview: () => fetchApi<any>('/models'),
  getModelMetrics: () => fetchApi<any>('/models/metrics'),
  trainModels: () => fetchApi<any>('/models/train', { method: 'POST' }),

  // Evaluations
  getEvaluations: () => fetchApi<any[]>('/evaluations'),
  runEvaluation: (casesCount: number = 24) =>
    fetchApi<any>('/evaluations/run', { method: 'POST', body: JSON.stringify({ cases_count: casesCount }) }),

  // Settings & System Configuration
  getSettings: () => fetchApi<any>('/settings/integrations'),
  testGemini: () => fetchApi<any>('/settings/test-gemini', { method: 'POST' }),
  updateApiKey: (apiKey: string) =>
    fetchApi<any>('/settings/api-key', { method: 'POST', body: JSON.stringify({ api_key: apiKey }) }),
  getTraffic: () => fetchApi<any>('/settings/traffic'),
  updateTraffic: (rps: number) =>
    fetchApi<any>('/settings/traffic', { method: 'POST', body: JSON.stringify({ rps }) }),
  toggleTraffic: () => fetchApi<any>('/settings/traffic/toggle', { method: 'POST' }),
  getSafety: () => fetchApi<any>('/settings/safety'),
  updateSafety: (cfg: { human_approval_required: boolean; max_remediations_per_hour: number; allowed_actions: string[] }) =>
    fetchApi<any>('/settings/safety', { method: 'POST', body: JSON.stringify(cfg) }),
  getDiagnostics: () => fetchApi<any>('/settings/system-diagnostics'),
  resetDemo: () => fetchApi<any>('/settings/reset-demo', { method: 'POST' }),
};
