import { useEffect, useState } from 'react';
import { apiFetch, API_BASE_URL } from '../api/client';
import { useAuth } from '../auth/AuthContext';

type HealthResponse = {
  status: string;
  version: string;
  environment: string;
  database: string;
  redis: string;
  platform_mock_mode: boolean;
  ollama: {
    base_url: string;
    primary_model: string;
    fallback_model: string;
  };
};

export function Settings() {
  const { token } = useAuth();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [result, setResult] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<HealthResponse>('/health', {}, token).then(setHealth).catch(() => setHealth(null));
  }, [token]);

  async function testHealth() {
    try {
      const data = await apiFetch<HealthResponse>('/health', {}, token);
      setHealth(data);
      setResult('API health check succeeded.');
    } catch {
      setResult('API health check failed.');
    }
  }

  async function testOllama() {
    try {
      const data = await apiFetch<HealthResponse>('/health', {}, token);
      setResult(`Ollama configured at ${data.ollama.base_url} using ${data.ollama.primary_model}.`);
    } catch {
      setResult('Ollama test failed.');
    }
  }

  return (
    <div className="stack">
      <section className="card settings-grid">
        <div><strong>API base URL</strong><span>{API_BASE_URL || window.location.origin}</span></div>
        <div><strong>Auth token</strong><span>{token ? 'Present in localStorage' : 'Missing'}</span></div>
        <div><strong>Environment</strong><span>{health?.environment || 'unknown'}</span></div>
        <div><strong>Platform mock mode</strong><span>{String(health?.platform_mock_mode ?? true)}</span></div>
        <div><strong>Ollama primary</strong><span>{health?.ollama.primary_model || 'unknown'}</span></div>
        <div><strong>Ollama fallback</strong><span>{health?.ollama.fallback_model || 'unknown'}</span></div>
      </section>
      <section className="card form-actions">
        <button type="button" className="button button--primary" onClick={testHealth}>Test API Health</button>
        <button type="button" className="button button--ghost" onClick={testOllama}>Test Ollama</button>
      </section>
      {result ? <div className="alert alert--success">{result}</div> : null}
    </div>
  );
}
