import React, { useState } from 'react';
import { X, Server, Wifi, RefreshCw, CheckCircle2, AlertTriangle, HelpCircle } from 'lucide-react';
import { getStoredBaseUrl, setStoredBaseUrl, resetStoredBaseUrl, DEFAULT_BASE_URL } from '../../services/apiClient';
import { pathsnapService, HealthCheckResult } from '../../services/pathsnapService';

interface ConnectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConnectionUpdated: () => void;
}

export const ConnectionModal: React.FC<ConnectionModalProps> = ({
  isOpen,
  onClose,
  onConnectionUpdated,
}) => {
  const [currentUrl, setCurrentUrl] = useState<string>(getStoredBaseUrl());
  const [testResult, setTestResult] = useState<HealthCheckResult | null>(null);
  const [isTesting, setIsTesting] = useState<boolean>(false);
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);

  if (!isOpen) return null;

  const handleTest = async () => {
    setIsTesting(true);
    setTestResult(null);
    setSaveSuccess(false);
    try {
      const res = await pathsnapService.checkHealth(currentUrl);
      setTestResult(res);
    } catch (e: any) {
      setTestResult({
        isHealthy: false,
        latencyMs: 0,
        error: e.message || 'Unknown network error',
        urlChecked: currentUrl,
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleSave = () => {
    setStoredBaseUrl(currentUrl);
    setSaveSuccess(true);
    onConnectionUpdated();
    setTimeout(() => {
      onClose();
      setSaveSuccess(false);
    }, 800);
  };

  const handleReset = () => {
    const def = resetStoredBaseUrl();
    setCurrentUrl(def);
    setTestResult(null);
    onConnectionUpdated();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/60">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <Server className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-100">Laptop 1 Connection Settings</h3>
              <p className="text-xs text-slate-400">Configure target FastAPI ML backend address</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Backend Base URL (Laptop 1 IP & Port)
            </label>
            <div className="relative flex items-center">
              <input
                type="text"
                value={currentUrl}
                onChange={(e) => {
                  setCurrentUrl(e.target.value);
                  setTestResult(null);
                  setSaveSuccess(false);
                }}
                placeholder="http://10.30.xxx.xxx:8000"
                className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-700/80 rounded-xl text-sm font-mono text-emerald-400 placeholder:text-slate-600 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-all"
              />
            </div>
            <p className="mt-1.5 text-[11px] text-slate-400 flex items-center gap-1">
              <Wifi className="w-3.5 h-3.5 text-slate-500" />
              Default: <code className="text-slate-300">{DEFAULT_BASE_URL}</code>
            </p>
          </div>

          {/* Test Status Banner */}
          {testResult && (
            <div
              className={`p-3.5 rounded-xl border text-xs space-y-1.5 ${
                testResult.isHealthy
                  ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300'
                  : 'bg-rose-950/40 border-rose-500/40 text-rose-300'
              }`}
            >
              <div className="flex items-center justify-between font-semibold">
                <div className="flex items-center gap-1.5">
                  {testResult.isHealthy ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 text-rose-400" />
                  )}
                  <span>
                    {testResult.isHealthy ? 'Backend Reachable' : 'Connection Failed'}
                  </span>
                </div>
                <span className="font-mono text-[11px] opacity-80">{testResult.latencyMs} ms</span>
              </div>
              {testResult.data && (
                <div className="text-[11px] font-mono text-slate-300 pt-1 border-t border-slate-800">
                  Model: {testResult.data.active_model || 'Loaded'} | Version: {testResult.data.version || '1.0'}
                </div>
              )}
              {testResult.error && (
                <p className="text-[11px] text-rose-400 opacity-90">{testResult.error}</p>
              )}
            </div>
          )}

          {/* Tips Box */}
          <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800/80 text-[11px] text-slate-400 space-y-1.5">
            <div className="flex items-center gap-1 text-slate-300 font-medium">
              <HelpCircle className="w-3.5 h-3.5 text-emerald-400" />
              <span>Two-Laptop Checklist:</span>
            </div>
            <ul className="list-disc pl-4 space-y-0.5 text-slate-400">
              <li>Both laptops must be connected to the same Wi-Fi / hotspot.</li>
              <li>Laptop 1 must start FastAPI with <code className="text-emerald-400">--host 0.0.0.0 --port 8000</code>.</li>
              <li>Laptop 1 firewall must permit inbound connections on port 8000.</li>
            </ul>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 bg-slate-950/50 border-t border-slate-800">
          <button
            type="button"
            onClick={handleReset}
            className="text-xs text-slate-400 hover:text-slate-200 transition-colors"
          >
            Reset to Default
          </button>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleTest}
              disabled={isTesting || !currentUrl.trim()}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-slate-200 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 rounded-xl transition-all"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isTesting ? 'animate-spin' : ''}`} />
              <span>{isTesting ? 'Testing...' : 'Test Ping'}</span>
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={!currentUrl.trim()}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-slate-950 bg-emerald-400 hover:bg-emerald-300 disabled:opacity-50 rounded-xl shadow-glow-emerald transition-all"
            >
              <span>{saveSuccess ? 'Saved!' : 'Save & Apply'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
