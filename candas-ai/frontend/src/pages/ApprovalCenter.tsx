import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiFetch } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { EmptyState } from '../components/EmptyState';
import { StatusBadge } from '../components/StatusBadge';

type PendingApproval = {
  approval_id: string;
  campaign_id: string;
  campaign_title: string;
  status: string;
  post_count: number;
  platforms: string[];
  created_at: string;
};

export function ApprovalCenter() {
  const { token } = useAuth();
  const [items, setItems] = useState<PendingApproval[]>([]);

  useEffect(() => {
    apiFetch<PendingApproval[]>('/approvals/pending', {}, token).then(setItems).catch(() => setItems([]));
  }, [token]);

  return items.length ? (
    <section className="grid grid--cards">
      {items.map((item) => (
        <article key={item.approval_id} className="card quick-card">
          <div className="card__split">
            <h3>{item.campaign_title}</h3>
            <StatusBadge value={item.status} />
          </div>
          <p>{item.post_count} draft posts ready for review.</p>
          <p>{item.platforms.join(', ')}</p>
          <p>{new Date(item.created_at).toLocaleString()}</p>
          <Link className="button button--primary" to={`/campaigns/${item.campaign_id}`}>
            Review Campaign
          </Link>
        </article>
      ))}
    </section>
  ) : (
    <EmptyState title="Approval queue is clear" description="When campaigns reach human review, they will appear here." />
  );
}
