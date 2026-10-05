import { StatusBadge } from './StatusBadge';

type ScheduleSuggestion = {
  recommended_publish_at: string;
  reason: string;
  confidence: number;
};

type PostCardProps = {
  post: {
    id: string;
    platform: string;
    copy: string;
    image_url?: string | null;
    image_prompt?: string | null;
    compliance_flags?: Record<string, unknown>;
    reflection_score?: number | null;
    status?: string;
    publish_at?: string | null;
    publishing_status?: string | null;
    published_at?: string | null;
    publishing_error?: string | null;
    analytics?: {
      impressions: number;
      clicks: number;
      engagement_rate: number;
      reach: number;
      conversions: number;
      fetched_at?: string | null;
    } | null;
  };
  draft: {
    copy: string;
    image_prompt: string;
    image_url: string;
    publishAt: string;
  };
  suggestion?: ScheduleSuggestion | null;
  canEdit: boolean;
  saving?: boolean;
  onDraftChange: (postId: string, field: 'copy' | 'image_prompt' | 'image_url' | 'publishAt', value: string) => void;
  onUseSuggestion: (postId: string) => void;
  onSavePost: (postId: string) => void;
  onSaveSchedule: (postId: string) => void;
};

function toLocalInputValue(value?: string | null) {
  if (!value) return '';
  const date = new Date(value);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

export function PostCard({
  post,
  draft,
  suggestion,
  canEdit,
  saving,
  onDraftChange,
  onUseSuggestion,
  onSavePost,
  onSaveSchedule,
}: PostCardProps) {
  const violations = Array.isArray(post.compliance_flags?.violations)
    ? (post.compliance_flags?.violations as string[])
    : [];
  const scheduleValue = draft.publishAt || toLocalInputValue(post.publish_at);

  return (
    <article className="card post-card">
      <div className="post-card__header">
        <div>
          <div className="post-card__platform">{post.platform}</div>
          {post.status ? <StatusBadge value={post.status} /> : null}
        </div>
        <div className="metric-pill">Reflection {post.reflection_score?.toFixed(2) || 'n/a'}</div>
      </div>

      {post.image_url ? <img src={post.image_url} alt={post.platform} className="post-card__image" /> : null}

      <label className="post-card__meta">
        <strong>Copy</strong>
        <textarea
          value={draft.copy}
          onChange={(event) => onDraftChange(post.id, 'copy', event.target.value)}
          disabled={!canEdit || saving}
        />
      </label>

      <label className="post-card__meta">
        <strong>Image prompt</strong>
        <textarea
          value={draft.image_prompt}
          onChange={(event) => onDraftChange(post.id, 'image_prompt', event.target.value)}
          disabled={!canEdit || saving}
        />
      </label>

      <label className="post-card__meta">
        <strong>Image URL</strong>
        <input
          value={draft.image_url}
          onChange={(event) => onDraftChange(post.id, 'image_url', event.target.value)}
          disabled={!canEdit || saving}
        />
      </label>

      {suggestion ? (
        <div className="alert alert--success">
          <strong>Recommended posting time</strong>
          <span>{new Date(suggestion.recommended_publish_at).toLocaleString()}</span>
          <span>{suggestion.reason}</span>
          <span>Confidence {Math.round(suggestion.confidence * 100)}%</span>
          {canEdit ? (
            <button type="button" className="button button--ghost" onClick={() => onUseSuggestion(post.id)}>
              Use this time
            </button>
          ) : null}
        </div>
      ) : null}

      <label className="post-card__meta">
        <strong>Selected publish time</strong>
        <input
          type="datetime-local"
          value={scheduleValue}
          onChange={(event) => onDraftChange(post.id, 'publishAt', event.target.value)}
          disabled={!canEdit || saving}
        />
      </label>

      <div className="post-card__meta">
        <strong>Publishing</strong>
        <span>
          {post.publishing_status || 'not scheduled'}
          {post.publish_at ? ` at ${new Date(post.publish_at).toLocaleString()}` : ''}
        </span>
      </div>

      {post.published_at ? (
        <div className="post-card__meta">
          <strong>Published</strong>
          <span>{new Date(post.published_at).toLocaleString()}</span>
        </div>
      ) : null}

      <div className="post-card__meta">
        <strong>Compliance</strong>
        <span>{violations.length ? violations.join(', ') : 'No active flags'}</span>
      </div>

      {post.analytics ? (
        <div className="post-card__meta">
          <strong>Analytics</strong>
          <span>
            {post.analytics.impressions} impressions, {post.analytics.clicks} clicks, {Math.round(post.analytics.engagement_rate * 100)}% engagement
          </span>
        </div>
      ) : null}

      {post.publishing_error ? <div className="alert alert--error">{post.publishing_error}</div> : null}

      {canEdit ? (
        <div className="form-actions">
          <button type="button" className="button button--primary" disabled={saving} onClick={() => onSavePost(post.id)}>
            Save Post
          </button>
          <button type="button" className="button button--ghost" disabled={saving} onClick={() => onSaveSchedule(post.id)}>
            Save Schedule
          </button>
        </div>
      ) : null}
    </article>
  );
}
