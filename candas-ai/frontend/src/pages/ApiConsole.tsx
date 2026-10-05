import { useEffect, useMemo, useState } from 'react';
import { apiFetch } from '../api/client';
import { fetchOpenApi, OpenApiDocument, OpenApiOperation } from '../api/openapi';
import { useAuth } from '../auth/AuthContext';
import { OpenApiForm } from '../components/OpenApiForm';

type SelectedEndpoint = {
  path: string;
  method: string;
  operation: OpenApiOperation;
};

export function ApiConsole() {
  const { token } = useAuth();
  const [doc, setDoc] = useState<OpenApiDocument | null>(null);
  const [selected, setSelected] = useState<SelectedEndpoint | null>(null);
  const [body, setBody] = useState<unknown>({});
  const [response, setResponse] = useState<unknown>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchOpenApi().then(setDoc).catch(() => setDoc(null));
  }, []);

  const grouped = useMemo(() => {
    if (!doc) return {};
    const result: Record<string, SelectedEndpoint[]> = {};
    Object.entries(doc.paths).forEach(([path, methods]) => {
      Object.entries(methods).forEach(([method, operation]) => {
        const tag = operation.tags?.[0] || 'system';
        if (!['campaigns', 'posts', 'approvals', 'analytics', 'webhooks', 'auth'].includes(tag)) return;
        result[tag] = result[tag] || [];
        result[tag].push({ path, method: method.toUpperCase(), operation });
      });
    });
    return result;
  }, [doc]);

  async function sendRequest() {
    if (!selected) return;
    setError(null);
    try {
      const data = await apiFetch(selected.path, {
        method: selected.method,
        body: ['GET', 'DELETE'].includes(selected.method) ? undefined : JSON.stringify(body),
      }, token);
      setResponse(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed');
      setResponse(null);
    }
  }

  return (
    <div className="api-console">
      <section className="card api-console__nav">
        <h3>OpenAPI Explorer</h3>
        {Object.entries(grouped).map(([tag, endpoints]) => (
          <div key={tag} className="stack">
            <h4>{tag}</h4>
            {endpoints.map((endpoint) => (
              <button
                key={`${endpoint.method}-${endpoint.path}`}
                className={`api-link${selected?.path === endpoint.path && selected?.method === endpoint.method ? ' api-link--active' : ''}`}
                onClick={() => setSelected(endpoint)}
                type="button"
              >
                <span className={`method method--${endpoint.method.toLowerCase()}`}>{endpoint.method}</span>
                <span>{endpoint.path}</span>
              </button>
            ))}
          </div>
        ))}
      </section>
      <section className="card api-console__panel">
        {selected ? (
          <>
            <div className="card__header">
              <div>
                <div className={`method method--${selected.method.toLowerCase()}`}>{selected.method}</div>
                <h3>{selected.path}</h3>
                <p>{selected.operation.summary || selected.operation.description || 'No summary provided.'}</p>
              </div>
              <div className="metric-pill">
                {selected.operation.security?.length ? 'Auth required' : 'Public'}
              </div>
            </div>
            <OpenApiForm
              doc={doc!}
              schema={selected.operation.requestBody?.content?.['application/json']?.schema}
              onChange={setBody}
            />
            {error ? <div className="alert alert--error">{error}</div> : null}
            <button className="button button--primary" type="button" onClick={sendRequest}>
              Send Request
            </button>
            <pre className="response-viewer">{JSON.stringify(response, null, 2)}</pre>
          </>
        ) : (
          <div className="empty-state">
            <h3>Select an endpoint</h3>
            <p>This console is generated from the live `/openapi.json` document, not hardcoded schemas.</p>
          </div>
        )}
      </section>
    </div>
  );
}
