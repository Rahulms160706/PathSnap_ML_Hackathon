import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Header } from './components/common/Header';
import { Sidebar } from './components/common/Sidebar';
import { OverviewPage } from './pages/OverviewPage';
import { EvaluationPage } from './pages/EvaluationPage';
import { ModelAnalyticsPage } from './pages/ModelAnalyticsPage';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <div className="flex flex-col h-screen w-screen bg-slate-950 text-slate-100 font-sans overflow-hidden">
        {/* Top Header */}
        <Header />

        {/* Workspace Body */}
        <div className="flex flex-1 overflow-hidden">
          {/* Left Sidebar */}
          <Sidebar />

          {/* Main View Area */}
          <main className="flex-1 overflow-y-auto bg-slate-950">
            <Routes>
              <Route path="/" element={<OverviewPage />} />
              <Route path="/evaluation" element={<EvaluationPage />} />
              <Route path="/models" element={<ModelAnalyticsPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
};

export default App;
