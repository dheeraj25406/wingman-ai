import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppLayout } from './layouts/AppLayout';
import { OverviewPage } from './pages/OverviewPage';
import { IncidentsPage } from './pages/IncidentsPage';
import { InvestigationPage } from './pages/InvestigationPage';
import { ServiceMapPage } from './pages/ServiceMapPage';
import { ModelIntelligencePage } from './pages/ModelIntelligencePage';
import { EvaluationPage } from './pages/EvaluationPage';
import { FaultLabPage } from './pages/FaultLabPage';
import { SettingsPage } from './pages/SettingsPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 2000,
      retry: 1,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<AppLayout />}>
            <Route index element={<OverviewPage />} />
            <Route path="incidents" element={<IncidentsPage />} />
            <Route path="incidents/:id" element={<InvestigationPage />} />
            <Route path="services" element={<ServiceMapPage />} />
            <Route path="models" element={<ModelIntelligencePage />} />
            <Route path="evaluations" element={<EvaluationPage />} />
            <Route path="fault-lab" element={<FaultLabPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

export default App;
