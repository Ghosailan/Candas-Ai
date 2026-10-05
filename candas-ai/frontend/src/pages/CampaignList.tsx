import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiFetch } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { EmptyState } from '../components/EmptyState';
import { StatusBadge } from '../components/StatusBadge';

type Campaign = {
  id: string;
  title: string;
  status: string;
  platforms: string[];
  goals: string[];
  created_at: string;
};

export function CampaignList() {
  const { token } = useAuth();
  const [items, setItems] = useState<Campaign[]>([]);
  const [status, setStatus] = useState('all');
  const [platform, setPlatform] = useState('all');

  useEffect(() => {
    apiFetch<Campaign[]>('/campaigns', {}, token).then(setItems).catch(() => setItems([]));
  }, [token]);

  const filtered = items.filter((item) => {
    if (status !== 'all' && item.status !== status) return false;
    if (platform !== 'all' && !item.platforms.includes(platform)) return false;
    return true;
  });

  return (
    <div className="stack">
      <section className="card filters">
        <label>
          Status
          <select value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="all">all</option>
            <option value="draft">draft</option>
            <option value="active">active</option>
            <option value="paused">paused</option>
            <option value="completed">completed</option>
            <option value="failed">failed</option>
          </select>
        </label>
        <label>
          Platform
          <select value={platform} onChange={(event) => setPlatform(event.target.value)}>
            <option value="all">all</option>
            <option value="instagram">instagram</option>
            <option value="facebook">facebook</option>
            <option value="linkedin">linkedin</option>
            <option value="twitter">twitter/x</option>
            <option value="tiktok">tiktok</option>
            <option value="youtube">youtube</option>
          </select>
        </label>
      </section>
      {filtered.length ? (
        <section className="grid grid--cards">
          {filtered.map((campaign) => (
            <article key={campaign.id} className="card quick-card">
              <div className="card__split">
                <h3>{campaign.title}</h3>
                <StatusBadge value={campaign.status} />
              </div>
              <p>{campaign.platforms.join(', ')}</p>
              <p>{campaign.goals.join(', ')}</p>
              <p>{new Date(campaign.created_at).toLocaleString()}</p>
              <Link to={`/campaigns/${campaign.id}`} className="button button--primary">
                Open
              </Link>
            </article>
          ))}
        </section>
      ) : (
        <EmptyState title="No campaigns found" description="Adjust your filters or create a new campaign to get started." />
      )}
    </div>
  );
}
