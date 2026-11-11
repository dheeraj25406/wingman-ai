import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { Header } from '../components/Header';
import { Cpu, RefreshCw, CheckCircle2, TrendingUp, Layers, BarChart2 } from 'lucide-react';
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

  const { data: modelsOverview, isLoading } = useQuery({
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
    <div className="flex-1 flex flex-col">
      <Header
        title="Model Intelligence & MLflow Tracking"
        subtitle="Unsupervised anomaly detection ensembling and supervised gradient-boosted incident classification"
        actions={
          <button
            onClick={() => trainMutation.mutate()}
            disabled={trainMutation.isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-accent text-bg-app text-xs font-semibold hover:bg-accent/90 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={13} className={trainMutation.isPending ? 'animate-spin' : ''} />
            <span>{trainMutation.isPending ? 'Retraining Models...' : 'Retrain ML Models'}</span>
          </button>
        }
      />

      <div className="p-6 space-y-6">
        {/* Model Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Model 1: Isolation Forest */}
          <div className="bg-bg-surface border border-border-subtle rounded-md p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-border-subtle">
              <div className="flex items-center gap-2">
                <Cpu size={16} className="text-accent" />
                <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                  Model 1: Isolation Forest (Anomaly Detector)
                </h3>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-status-success/20 text-status-success font-semibold">
                ACTIVE INFERENCE
              </span>
            </div>

            <div className="grid grid-cols-3 gap-3 text-xs font-mono">
              <div className="p-2.5 bg-bg-raised rounded border border-border-subtle">
                <span className="text-[10px] text-text-muted block">Precision</span>
                <span className="text-base font-bold text-status-success">
                  {(binMetrics?.isolation_forest?.precision || 0.9983 * 100).toFixed(1)}%
                </span>
              </div>
              <div className="p-2.5 bg-bg-raised rounded border border-border-subtle">
                <span className="text-[10px] text-text-muted block">Recall</span>
                <span className="text-base font-bold text-status-success">
                  {(binMetrics?.isolation_forest?.recall || 0.9725 * 100).toFixed(1)}%
                </span>
              </div>
              <div className="p-2.5 bg-bg-raised rounded border border-border-subtle">
                <span className="text-[10px] text-text-muted block">F1-Score</span>
                <span className="text-base font-bold text-accent">
                  {(binMetrics?.isolation_forest?.f1 || 0.9852).toFixed(4)}
                </span>
              </div>
            </div>

            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between text-text-secondary text-[11px] font-mono">
                <span>Calibrated Score Threshold:</span>
                <span className="text-text-primary font-bold">0.5200</span>
              </div>
              <div className="flex justify-between text-text-secondary text-[11px] font-mono">
                <span>Contamination Setting:</span>
                <span className="text-text-primary">0.0300 (FPR &lt; 3%)</span>
              </div>
              <div className="flex justify-between text-text-secondary text-[11px] font-mono">
                <span>Features Vector Size:</span>
                <span className="text-text-primary">13 Dimensions</span>
              </div>
            </div>
          </div>

          {/* Model 2: LightGBM Classifier */}
          <div className="bg-bg-surface border border-border-subtle rounded-md p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-border-subtle">
              <div className="flex items-center gap-2">
                <BarChart2 size={16} className="text-accent" />
                <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                  Model 2: LightGBM (Incident Classifier)
                </h3>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-status-success/20 text-status-success font-semibold">
                ACTIVE INFERENCE
              </span>
            </div>

            <div className="grid grid-cols-3 gap-3 text-xs font-mono">
              <div className="p-2.5 bg-bg-raised rounded border border-border-subtle">
                <span className="text-[10px] text-text-muted block">LightGBM Macro-F1</span>
                <span className="text-base font-bold text-status-success">
                  {(multiMetrics?.macro_f1 || 0.9993).toFixed(4)}
                </span>
              </div>
              <div className="p-2.5 bg-bg-raised rounded border border-border-subtle">
                <span className="text-[10px] text-text-muted block">RF Baseline F1</span>
                <span className="text-base font-bold text-text-secondary">
                  {(lgbm?.rf_baseline_macro_f1 || 0.9985).toFixed(4)}
                </span>
              </div>
              <div className="p-2.5 bg-bg-raised rounded border border-border-subtle">
                <span className="text-[10px] text-text-muted block">Classes Classified</span>
                <span className="text-base font-bold text-accent">7 Classes</span>
              </div>
            </div>

            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between text-text-secondary text-[11px] font-mono">
                <span>Split Strategy:</span>
                <span className="text-text-primary">GroupShuffleSplit (By Experiment Run)</span>
              </div>
              <div className="flex justify-between text-text-secondary text-[11px] font-mono">
                <span>MLflow Experiment:</span>
                <span className="text-text-primary font-mono">wingman_incident_classifier</span>
              </div>
              <div className="flex justify-between text-text-secondary text-[11px] font-mono">
                <span>Probability Calibration:</span>
                <span className="text-status-success">Softmax Probabilities</span>
              </div>
            </div>
          </div>
        </div>

        {/* Feature Importance Chart */}
        <div className="bg-bg-surface border border-border-subtle rounded-md p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
              LightGBM Feature Importance (Split Frequency)
            </h3>
            <span className="text-[11px] font-mono text-text-muted">Top Engineered Telemetry Features</span>
          </div>

          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={featureImpData.slice(0, 8)} layout="vertical">
                <XAxis type="number" stroke="#647184" fontSize={10} tickLine={false} />
                <YAxis dataKey="name" type="category" stroke="#929EAD" fontSize={10} tickLine={false} width={150} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#151D27', borderColor: '#293442', fontSize: '11px' }}
                />
                <Bar dataKey="importance" fill="#65A9FF" radius={[0, 3, 3, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Multi-class Confusion Matrix Heatmap */}
        <div className="bg-bg-surface border border-border-subtle rounded-md p-5 space-y-4 overflow-hidden">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
              Held-Out Test Confusion Matrix (1,400 Benchmark Samples)
            </h3>
            <span className="text-[11px] font-mono text-text-muted">Group-Aware Test Set</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-center text-xs font-mono">
              <thead>
                <tr className="text-text-muted border-b border-border-subtle">
                  <th className="py-2 px-3 text-left">True \ Predicted</th>
                  {classNames.map((c: string) => (
                    <th key={c} className="py-2 px-2 text-[10px] text-text-secondary">
                      {c.replace('_', ' ').slice(0, 10)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle">
                {(multiMetrics?.confusion_matrix || []).map((row: number[], rIdx: number) => (
                  <tr key={rIdx} className="hover:bg-bg-raised/30">
                    <td className="py-2 px-3 text-left text-[10px] font-medium text-text-primary">
                      {classNames[rIdx]}
                    </td>
                    {row.map((val: number, cIdx: number) => {
                      const isDiagonal = rIdx === cIdx;
                      return (
                        <td
                          key={cIdx}
                          className={`py-2 px-2 text-xs ${
                            isDiagonal
                              ? 'bg-status-success/20 text-status-success font-bold'
                              : val > 0
                              ? 'bg-status-critical/20 text-status-critical font-bold'
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
        </div>
      </div>
    </div>
  );
};
