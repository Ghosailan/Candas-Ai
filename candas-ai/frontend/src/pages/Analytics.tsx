import { useEffect, useMemo, useState } from 'react';
import { apiFetch } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { EmptyState } from '../components/EmptyState';

type Campaign = { id: string; title: string };
type AnalyticsPayload = {
  campaign_id: string;
  totals: Record<string, number>;
  by_platform: Array<Record<string, string | number>>;
  best_posts: Array<Record<string, string | number>>;
  empty: boolean;
  message?: string;
};

export function AnalyticsPage() {
  const { token } = useAuth();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [selectedCampaign, setSelectedCampaign] = useState('');
  const [analytics, setAnalytics] = useState<AnalyticsPayload | null>(null);

  useEffect(() => {
    apiFetch<Array<{ id: string; title: string }>>('/campaigns', {}, token)
      .then((data) => {
        setCampaigns(data.map(({ id, title }) => ({ id, title })));
        if (data[0]) setSelectedCampaign(data[0].id);
      })
      .catch(() => setCampaigns([]));
  }, [token]);

  useEffect(() => {
    if (!selectedCampaign) return;
    apiFetch<AnalyticsPayload>(`/analytics/${selectedCampaign}`, {}, token).then(setAnalytics).catch(() => setAnalytics(null));
  }, [selectedCampaign, token]);

  const maxImpressions = useMemo(
    () => Math.max(...(analytics?.by_platform.map((item) => Number(item.impressions)) || [1])),
    [analytics],
  );

  return (
    <div className="stack">
      <section className="card filters">
        <label>
          Campaign
          <select value={selectedCampaign} onChange={(event) => setSelectedCampaign(event.target.value)}>
            {campaigns.map((campaign) => (
              <option key={campaign.id} value={campaign.id}>
                {campaign.title}
              </option>
            ))}
          </select>
        </label>
      </section>
      {!analytics || analytics.empty ? (
        <EmptyState
          title="Analytics are not ready yet"
          description={analytics?.message || 'Select a published campaign or refresh analytics later. Mock mode keeps this safe for local runs.'}
        />
      ) : (
        <>
          <section className="grid grid--metrics">
            {Object.entries(analytics.totals).map(([key, value]) => (
              <article key={key} className="card metric-card">
                <span>{key.replace('_', ' ')}</span>
                <strong>{typeof value === 'number' ? value.toLocaleString() : value}</strong>
              </article>
            ))}
          </section>
          <section className="card">
            <h3>Platform Comparison</h3>
            <div className="bar-chart">
              {analytics.by_platform.map((row) => (
                <div key={String(row.platform)} className="bar-chart__row">
                  <span>{row.platform}</span>
                  <div className="bar-chart__track">
                    <div className="bar-chart__fill" style={{ width: `${(Number(row.impressions) / maxImpressions) * 100}%` }} />
                  </div>
                  <strong>{Number(row.impressions).toLocaleString()}</strong>
                </div>
              ))}
            </div>
          </section>
          <section className="card">
            <h3>Best Performing Posts</h3>
            <div className="stack">
              {analytics.best_posts.map((post) => (
                <div key={String(post.post_id)} className="list-row">
                  <span>{post.platform}</span>
                  <span>{String(post.copy)}</span>
                  <strong>ER {String(post.engagement_rate)}</strong>
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
