export type Envelope<T> = {
  status: string;
  data: T;
  meta?: {
    trace_id?: string | null;
    timestamp?: string;
    version?: string;
  };
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/v1';

function buildUrl(path: string) {
  return `${API_BASE_URL}${path}`;
}

export async function apiFetch<T>(path: string, init: RequestInit = {}, token?: string | null): Promise<T> {
  const response = await fetch(buildUrl(path), {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers || {}),
    },
  });

  const text = await response.text();
  const payload = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const message = payload?.detail || payload?.message || 'Request failed';
    throw new Error(message);
  }

  if (payload && typeof payload === 'object' && 'data' in payload) {
    return (payload as Envelope<T>).data;
  }
  return payload as T;
}

export { API_BASE_URL };
