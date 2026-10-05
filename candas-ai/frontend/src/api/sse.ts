export type CampaignEvent = {
  event: string;
  node?: string;
  detail?: Record<string, unknown>;
  trace_id?: string | null;
  timestamp?: string;
};

export function connectCampaignStream(
  url: string,
  token: string,
  handlers: {
    onEvent: (event: CampaignEvent) => void;
    onError?: () => void;
  },
) {
  const eventSource = new EventSource(`${url}${url.includes('?') ? '&' : '?'}token=${encodeURIComponent(token)}`);
  eventSource.onmessage = (message) => {
    try {
      handlers.onEvent(JSON.parse(message.data));
    } catch {
      handlers.onEvent({ event: 'raw', detail: { message: message.data } });
    }
  };
  eventSource.onerror = () => handlers.onError?.();
  return () => eventSource.close();
}
