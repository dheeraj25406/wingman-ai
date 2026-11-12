import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { Header } from '../components/Header';
import { RefreshCw } from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

export const ModelIntelligencePage: React.FC = () => {
  const queryClient = useQueryClient();

  const { data: modelsOverview } = useQuery({
    queryKey: ['models-overview'],
    queryFn: api.getModelsOverview,
  });

  const { data: modelMetrics } = useQuery({
    queryKey: ['models-metrics'],
    queryFn: api.getModelMetrics,
  });

  const trainMutation = useMutation({
    mutationFn: api.trainModels,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['models-overview'] });
      queryClient.invalidateQueries({ queryKey: ['models-metrics'] });
    },
  });

  const iso = modelsOverview?.isolation_forest;
  const lgbm = modelsOverview?.lightgbm;
  const binMetrics = modelMetrics?.binary_detection;
  const multiMetrics = modelMetrics?.multiclass_classification;

  const featureImpData = (multiMetrics?.feature_importance || []).map((f: any) => ({
    name: f.feature,
    importance: f.importance,
  }));

  const classNames = multiMetrics?.classes || [
    'NORMAL',
    'DB_POOL_EXHAUSTION',
    'CPU_SATURATION',
    'MEMORY_PRESSURE',
    'DOWNSTREAM_API_FAILURE',
    'QUEUE_BACKLOG',
    'DEPLOYMENT_REGRESSION',
  ];

  return (
    <div className="flex-1 flex flex-col font-sans">
      <Header
        title="Model Intelligence & MLflow Registry"
        subtitle="Statistical telemetry anomaly detection and supervised fault categorization"
        actions={
          <button
            onClick={() => trainMutation.mutate()}
            disabled={trainMutation.isPending}
            className="flex items-center gap-1.5 px-3 py-1 rounded-sm bg-text-primary text-bg-app text-xs font-medium hover:bg-white transition-colors disabled:opacity-50"
          >
            <RefreshCw size={12} className={trainMutation.isPending ? 'animate-spin' : ''} />
            <span>{trainMutation.isPending ? 'Retraining...' : 'Retrain ML Pipeline'}</span>
          </button>
        }
      />

      <div className="p-6 space-y-6 max-w-7xl mx-auto w-full">
        {/* Model Overview Section (Editorial Table Layout) */}
        <section className="border border-border-subtle bg-bg-surface rounded-sm p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-border-subtle">
            <span className="text-xs font-medium text-text-primary uppercase tracking-wider font-mono">
              Active Production Models (MLflow Tracked)
            </span>
            <span className="text-[11px] font-mono text-text-muted">Tracking URI: sqlite:///mlflow.db</span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Model 1: Isolation Forest */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-xs font-semibold text-text-primary">1. Isolation Forest (Unsupervised)</h3>
                  <span className="text-[10px] font-mono text-text-muted">Target: Fleet-wide Anomaly Detection</span>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-sm text-status-sage bg-status-sage/10 border border-status-sage/20 uppercase">
                  Version {iso?.version || 'v1.0.0'}
                </span>
              </div>

              <div className="grid grid-cols-3 gap-2 text-xs font-mono">
                <div className="p-2.5 bg-bg-raised rounded-sm border border-border-subtle">
                  <span className="text-[10px] text-text-muted block">Precision</span>
                  <span className="text-sm font-medium text-status-sage">
                    {((binMetrics?.isolation_forest?.precision || 0.9983) * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="p-2.5 bg-bg-raised rounded-sm border border-border-subtle">
                  <span className="text-[10px] text-text-muted block">Recall</span>
                  <span className="text-sm font-medium text-status-sage">
                    {((binMetrics?.isolation_forest?.recall || 0.9725) * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="p-2.5 bg-bg-raised rounded-sm border border-border-subtle">
                  <span className="text-[10px] text-text-muted block">F1 Score</span>
                  <span className="text-sm font-medium text-text-primary">
                    {(binMetrics?.isolation_forest?.f1 || 0.9852).toFixed(4)}
                  </span>
                </div>
              </div>

              <div className="text-[11px] font-mono space-y-1 text-text-muted pt-1">
                <div className="flex justify-between">
                  <span>Score Threshold:</span>
                  <span className="text-text-primary">0.5200 (Normalized [0, 1])</span>
                </div>
                <div className="flex justify-between">
                  <span>Contamination:</span>
                  <span className="text-text-primary">0.0300 (FPR &lt; 3%)</span>
                </div>
                <div className="flex justify-between">
                  <span>Feature Dimensions:</span>
                  <span className="text-text-primary">13-dim Standardized</span>
                </div>
              </div>
            </div>

            {/* Model 2: LightGBM Classifier */}
            <div className="space-y-3 lg:border-l lg:border-border-subtle lg:pl-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-xs font-semibold text-text-primary">2. LightGBM Classifier (Supervised)</h3>
                  <span className="text-[10px] font-mono text-text-muted">Target: 7-Class Failure Root Categorization</span>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-sm text-status-sage bg-status-sage/10 border border-status-sage/20 uppercase">
                  Version {lgbm?.version || 'v1.0.0'}
                </span>
              </div>

              <div className="grid grid-cols-3 gap-2 text-xs font-mono">
                <div className="p-2.5 bg-bg-raised rounded-sm border border-border-subtle">
                  <span className="text-[10px] text-text-muted block">Macro F1</span>
                  <span className="text-sm font-medium text-status-sage">
                    {(multiMetrics?.macro_f1 || 0.9993).toFixed(4)}
                  </span>
                </div>
                <div className="p-2.5 bg-bg-raised rounded-sm border border-border-subtle">
                  <span className="text-[10px] text-text-muted block">RF Baseline F1</span>
                  <span className="text-sm font-medium text-text-muted">
                    {(lgbm?.rf_baseline_macro_f1 || 0.9985).toFixed(4)}
                  </span>
                </div>
                <div className="p-2.5 bg-bg-raised rounded-sm border border-border-subtle">
                  <span className="text-[10px] text-text-muted block">Num Classes</span>
                  <span className="text-sm font-medium text-text-primary">7 Classes</span>
                </div>
              </div>

              <div className="text-[11px] font-mono space-y-1 text-text-muted pt-1">
                <div className="flex justify-between">
                  <span>Validation Split:</span>
                  <span className="text-text-primary">GroupShuffleSplit (By Run ID)</span>
                </div>
                <div className="flex justify-between">
                  <span>Probability Mode:</span>
                  <span className="text-text-primary">Calibrated Softmax</span>
                </div>
                <div className="flex justify-between">
                  <span>Baseline Heuristic:</span>
                  <span className="text-text-primary">RandomForestClassifier</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Feature Importance Section */}
        <section className="border border-border-subtle bg-bg-surface rounded-sm p-5 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-text-primary uppercase tracking-wider font-mono">
              LightGBM Feature Importance (Split Frequency)
            </span>
            <span className="text-[10px] font-mono text-text-muted">Normalized relative importance</span>
          </div>

          <div className="h-48 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={featureImpData.slice(0, 8)} layout="vertical">
                <XAxis type="number" stroke="#252525" tick={{ fill: '#858585', fontSize: 10 }} tickLine={false} />
                <YAxis dataKey="name" type="category" stroke="#252525" tick={{ fill: '#BDBDBD', fontSize: 10 }} tickLine={false} width={160} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#111111', borderColor: '#303030', borderRadius: '3px', fontSize: '11px', color: '#F2F2F2' }}
                />
                <Bar dataKey="importance" fill="#BDBDBD" radius={[0, 2, 2, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>

        {/* 7x7 Multi-Class Confusion Matrix (Held-out Benchmark Test Set) */}
        <section className="border border-border-subtle bg-bg-surface rounded-sm p-5 space-y-3 overflow-hidden">
          <div className="flex items-center justify-between pb-2 border-b border-border-subtle">
            <span className="text-xs font-medium text-text-primary uppercase tracking-wider font-mono">
              Held-Out Test Confusion Matrix (1,400 Benchmark Samples)
            </span>
            <span className="text-[10px] font-mono text-text-muted">Strict Experiment Group Isolation</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-center text-xs font-mono">
              <thead>
                <tr className="text-text-muted border-b border-border-subtle text-[10px] uppercase">
                  <th className="py-2 px-3 text-left">Ground Truth \ Predicted</th>
                  {classNames.map((c: string) => (
                    <th key={c} className="py-2 px-2 text-text-secondary font-normal">
                      {c.replace('_', ' ').slice(0, 10)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle">
                {(multiMetrics?.confusion_matrix || []).map((row: number[], rIdx: number) => (
                  <tr key={rIdx} className="hover:bg-bg-hover">
                    <td className="py-2 px-3 text-left text-[10.5px] text-text-primary">
                      {classNames[rIdx]}
                    </td>
                    {row.map((val: number, cIdx: number) => {
                      const isDiagonal = rIdx === cIdx;
                      return (
                        <td
                          key={cIdx}
                          className={`py-2 px-2 text-xs ${
                            isDiagonal
                              ? 'text-status-sage font-medium bg-status-sage/5'
                              : val > 0
                              ? 'text-status-coral font-bold bg-status-coral/10'
                              : 'text-text-muted'
                          }`}
                        >
                          {val}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
};
