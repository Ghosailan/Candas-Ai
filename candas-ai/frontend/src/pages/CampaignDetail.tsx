import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { apiFetch } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { AgentTimeline } from '../components/AgentTimeline';
import { EmptyState } from '../components/EmptyState';
import { PostCard } from '../components/PostCard';
import { StatusBadge } from '../components/StatusBadge';

type CampaignRecord = {
  id: string;
  title: string;
  brief: string;
  platforms: string[];
  goals: string[];
  target_audience: Record<string, unknown>;
  status: string;
  created_at: string;
};

type DashboardPost = {
  id: string;
  platform: string;
  copy: string;
  image_url?: string | null;
  image_prompt?: string | null;
  compliance_flags?: Record<string, unknown>;
  reflection_score?: number | null;
  status: string;
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

type DashboardResponse = {
  campaign: CampaignRecord;
  posts: DashboardPost[];
  approval: null | {
    approval_id: string;
    decision: string;
    feedback?: string | null;
  };
  progress: {
    completed_posts: number;
    scheduled_posts?: number;
    total_posts: number;
    percent: number;
  };
};

type TraceEvent = {
  event: string;
  node?: string;
  detail?: Record<string, unknown>;
  timestamp?: string;
};

type Suggestion = {
  post_id: string;
  platform: string;
  recommended_publish_at: string;
  reason: string;
  confidence: number;
};

type DraftState = Record<
  string,
  {
    copy: string;
    image_prompt: string;
    image_url: string;
    publishAt: string;
  }
>;

const initialStatuses = Object.fromEntries(
  ['memory', 'planner', 'researcher', 'creator', 'reflection', 'approval', 'scheduler', 'publisher', 'analyst'].map(
    (node) => [node, 'waiting'],
  ),
) as Record<string, 'waiting' | 'running' | 'completed' | 'failed'>;

function toLocalInputValue(value?: string | null) {
  if (!value) return '';
  const date = new Date(value);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

export function CampaignDetail() {
  const { campaignId = '' } = useParams();
  const navigate = useNavigate();
  const { token, user } = useAuth();

  const [data, setData] = useState<DashboardResponse | null>(null);
  const [drafts, setDrafts] = useState<DraftState>({});
  const [campaignDraft, setCampaignDraft] = useState({
    title: '',
    brief: '',
    goals: '',
    platforms: '',
    targetAudience: '{}',
  });
  const [suggestions, setSuggestions] = useState<Record<string, Suggestion>>({});
  const [statuses, setStatuses] = useState(initialStatuses);
  const [trace, setTrace] = useState<TraceEvent[]>([]);
  const [feedback, setFeedback] = useState('');
  const [lastHeartbeat, setLastHeartbeat] = useState<number | null>(null);
  const [mutationError, setMutationError] = useState<string | null>(null);
  const [savingPostId, setSavingPostId] = useState<string | null>(null);
  const [savingCampaign, setSavingCampaign] = useState(false);
  const [requestingSuggestions, setRequestingSuggestions] = useState(false);

  async function refreshDashboard() {
    if (!campaignId || !token) return;
    const next = await apiFetch<DashboardResponse>(`/campaigns/${campaignId}/dashboard`, {}, token);
    setData(next);
  }

  useEffect(() => {
    refreshDashboard().catch(() => setData(null));
  }, [campaignId, token]);

  useEffect(() => {
    if (!data) return;
    setDrafts(
      Object.fromEntries(
        data.posts.map((post) => [
          post.id,
          {
            copy: post.copy,
            image_prompt: post.image_prompt || '',
            image_url: post.image_url || '',
            publishAt: toLocalInputValue(post.publish_at),
          },
        ]),
      ),
    );
    setCampaignDraft({
      title: data.campaign.title,
      brief: data.campaign.brief,
      goals: data.campaign.goals.join(', '),
      platforms: data.campaign.platforms.join(', '),
      targetAudience: JSON.stringify(data.campaign.target_audience || {}, null, 2),
    });
  }, [data]);

  useEffect(() => {
    if (!token || !campaignId) return;

    const url = `${window.location.origin}/v1/campaigns/${campaignId}/stream?token=${encodeURIComponent(token)}`;
    const source = new EventSource(url);

    source.onmessage = (message) => {
      const event = JSON.parse(message.data) as TraceEvent;
      setTrace((current) => [event, ...current].slice(0, 50));

      if (event.event === 'heartbeat') {
        setLastHeartbeat(Date.now());
        return;
      }

      if (event.node && event.event === 'node_started') {
        setStatuses((current) => ({ ...current, [event.node!]: 'running' }));
      }

      if (event.node && event.event === 'node_completed') {
        setStatuses((current) => ({ ...current, [event.node!]: 'completed' }));
        refreshDashboard().catch(() => undefined);
      }

      if (event.node && event.event === 'node_failed') {
        setStatuses((current) => ({ ...current, [event.node!]: 'failed' }));
        refreshDashboard().catch(() => undefined);
      }

      if (event.event === 'graph_completed') {
        refreshDashboard().catch(() => undefined);
      }
    };

    return () => source.close();
  }, [campaignId, token]);

  const heartbeatLabel = useMemo(() => {
    if (!lastHeartbeat) return 'Waiting for heartbeat';
    return Date.now() - lastHeartbeat < 20000 ? 'Stream healthy' : 'Heartbeat stale';
  }, [lastHeartbeat]);

  const isApproved =
    data?.approval?.decision === 'approved' || data?.campaign.status === 'completed';

  const isRejected =
    data?.approval?.decision === 'rejected' || data?.campaign.status === 'paused';

  const isFinalCampaign = isApproved || isRejected;
  const hasPublishedPosts = data?.posts.some((post) => post.status === 'published') ?? false;
  const canApprove = (user?.role === 'approver' || user?.role === 'admin') && !isFinalCampaign;
  const canEditCampaign = !hasPublishedPosts && data?.campaign.status !== 'completed';
  const unscheduledPosts = (data?.posts || []).filter((post) => !post.publish_at);

  const displayStatuses = useMemo(() => {
    const next = { ...statuses };
    if (data?.posts.length) {
      next.planner = 'completed';
      next.researcher = 'completed';
      next.creator = 'completed';
      next.reflection = 'completed';
    }
    if (data?.approval) {
      next.approval = 'completed';
    }
    if (isApproved && data?.posts.every((post) => Boolean(post.publish_at))) {
      next.scheduler = next.scheduler === 'waiting' ? 'completed' : next.scheduler;
    }
    if (data?.posts.length && data.posts.every((post) => post.status === 'published')) {
      next.publisher = 'completed';
    }
    const publishedWithAnalytics = (data?.posts || []).filter((post) => post.status === 'published' && post.analytics);
    const publishedCount = (data?.posts || []).filter((post) => post.status === 'published').length;
    if (publishedCount > 0 && publishedWithAnalytics.length === publishedCount) {
      next.analyst = 'completed';
    }
    return next;
  }, [statuses, data, isApproved]);

  function setDraftValue(postId: string, field: 'copy' | 'image_prompt' | 'image_url' | 'publishAt', value: string) {
    setDrafts((current) => ({
      ...current,
      [postId]: {
        ...(current[postId] || { copy: '', image_prompt: '', image_url: '', publishAt: '' }),
        [field]: value,
      },
    }));
  }

  async function savePost(postId: string) {
    const draft = drafts[postId];
    if (!draft) return;
    setMutationError(null);
    setSavingPostId(postId);
    try {
      await apiFetch(
        `/posts/${postId}`,
        {
          method: 'PATCH',
          body: JSON.stringify({
            copy: draft.copy,
            image_prompt: draft.image_prompt,
            image_url: draft.image_url || null,
          }),
        },
        token,
      );
      await refreshDashboard();
    } catch (error) {
      setMutationError(error instanceof Error ? error.message : 'Unable to save post');
    } finally {
      setSavingPostId(null);
    }
  }

  async function saveSchedule(postId: string) {
    const publishAt = drafts[postId]?.publishAt;
    if (!publishAt) {
      setMutationError('Select a publish time before saving the schedule.');
      return;
    }
    setMutationError(null);
    setSavingPostId(postId);
    try {
      await apiFetch(
        `/posts/${postId}/schedule`,
        {
          method: 'POST',
          body: JSON.stringify({ publish_at: new Date(publishAt).toISOString() }),
        },
        token,
      );
      await refreshDashboard();
    } catch (error) {
      setMutationError(error instanceof Error ? error.message : 'Unable to save schedule');
    } finally {
      setSavingPostId(null);
    }
  }

  async function requestSuggestions() {
    setMutationError(null);
    setRequestingSuggestions(true);
    try {
      const result = await apiFetch<{ suggestions: Suggestion[] }>(
        `/campaigns/${campaignId}/schedule-suggestions`,
        {
          method: 'POST',
          body: JSON.stringify({
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Riyadh',
          }),
        },
        token,
      );
      setSuggestions(Object.fromEntries(result.suggestions.map((item) => [item.post_id, item])));
    } catch (error) {
      setMutationError(error instanceof Error ? error.message : 'Unable to fetch recommended posting times');
    } finally {
      setRequestingSuggestions(false);
    }
  }

  function useSuggestedTime(postId: string) {
    const suggestion = suggestions[postId];
    if (!suggestion) return;
    setDraftValue(postId, 'publishAt', toLocalInputValue(suggestion.recommended_publish_at));
  }

  async function submitDecision(decision: 'approved' | 'rejected') {
    setMutationError(null);
    if (decision === 'approved' && unscheduledPosts.length > 0) {
      setMutationError('Please select or confirm schedule times for all posts before approving the campaign.');
      return;
    }

    try {
      await apiFetch(
        `/approvals/${campaignId}/decision`,
        {
          method: 'POST',
          body: JSON.stringify({
            decision,
            feedback: feedback || undefined,
          }),
        },
        token,
      );
      await refreshDashboard();
      setFeedback('');
      setStatuses((current) => ({ ...current, approval: 'completed' }));
    } catch (error) {
      setMutationError(error instanceof Error ? error.message : 'Unable to submit decision');
    }
  }

  async function saveCampaign() {
    setMutationError(null);
    setSavingCampaign(true);
    try {
      const targetAudience = JSON.parse(campaignDraft.targetAudience || '{}');
      await apiFetch(
        `/campaigns/${campaignId}`,
        {
          method: 'PATCH',
          body: JSON.stringify({
            title: campaignDraft.title,
            brief: campaignDraft.brief,
            goals: campaignDraft.goals.split(',').map((item) => item.trim()).filter(Boolean),
            platforms: campaignDraft.platforms.split(',').map((item) => item.trim()).filter(Boolean),
            target_audience: targetAudience,
          }),
        },
        token,
      );
      await refreshDashboard();
    } catch (error) {
      setMutationError(error instanceof Error ? error.message : 'Unable to save campaign');
    } finally {
      setSavingCampaign(false);
    }
  }

  async function deleteOrCancelCampaign() {
    if (!window.confirm('Delete or cancel this campaign? Published campaigns will be cancelled instead of deleted.')) {
      return;
    }
    setMutationError(null);
    try {
      await apiFetch(`/campaigns/${campaignId}`, { method: 'DELETE' }, token);
      navigate('/campaigns');
    } catch (error) {
      setMutationError(error instanceof Error ? error.message : 'Unable to delete or cancel campaign');
    }
  }

  if (!data) {
    return (
      <EmptyState
        title="Campaign unavailable"
        description="The campaign could not be loaded or is still being created."
      />
    );
  }

  return (
    <div className="stack">
      <section className="card">
        <div className="card__split">
          <div>
            <h2>{data.campaign.title}</h2>
            <p>{data.campaign.brief}</p>
          </div>

          <StatusBadge value={data.campaign.status} />
        </div>

        <div className="meta-grid">
          <div>
            <strong>Platforms</strong>
            <span>{data.campaign.platforms.join(', ')}</span>
          </div>

          <div>
            <strong>Goals</strong>
            <span>{data.campaign.goals.join(', ')}</span>
          </div>

          <div>
            <strong>Created</strong>
            <span>{new Date(data.campaign.created_at).toLocaleString()}</span>
          </div>

          <div>
            <strong>Heartbeat</strong>
            <span>{heartbeatLabel}</span>
          </div>
        </div>

        <div className="progress-bar">
          <span style={{ width: `${data.progress.percent}%` }} />
        </div>

        {canEditCampaign ? (
          <div className="stack">
            <div className="card__header">
              <h3>Edit Campaign</h3>
              <button type="button" className="button button--danger" onClick={deleteOrCancelCampaign}>
                Delete or Cancel
              </button>
            </div>

            <label>
              Title
              <input
                value={campaignDraft.title}
                onChange={(event) => setCampaignDraft((current) => ({ ...current, title: event.target.value }))}
                disabled={savingCampaign}
              />
            </label>

            <label>
              Brief
              <textarea
                value={campaignDraft.brief}
                onChange={(event) => setCampaignDraft((current) => ({ ...current, brief: event.target.value }))}
                disabled={savingCampaign}
              />
            </label>

            <label>
              Goals
              <input
                value={campaignDraft.goals}
                onChange={(event) => setCampaignDraft((current) => ({ ...current, goals: event.target.value }))}
                disabled={savingCampaign}
              />
            </label>

            <label>
              Platforms
              <input
                value={campaignDraft.platforms}
                onChange={(event) => setCampaignDraft((current) => ({ ...current, platforms: event.target.value }))}
                disabled={savingCampaign}
              />
            </label>

            <label>
              Target audience JSON
              <textarea
                value={campaignDraft.targetAudience}
                onChange={(event) => setCampaignDraft((current) => ({ ...current, targetAudience: event.target.value }))}
                disabled={savingCampaign}
              />
            </label>

            <div className="form-actions">
              <button type="button" className="button button--primary" disabled={savingCampaign} onClick={saveCampaign}>
                Save Campaign
              </button>
            </div>
          </div>
        ) : null}
      </section>

      <AgentTimeline statuses={displayStatuses} />

      <section className="card">
        <div className="card__header">
          <h3>Generated Content Review</h3>

          <button
            type="button"
            className="button button--primary"
            onClick={requestSuggestions}
            disabled={requestingSuggestions || data.posts.length === 0}
          >
            Suggest posting times with AI
          </button>
        </div>

        {isApproved ? (
          <div className="alert alert--success">
            Campaign approved. Publishing and analytics will progress from backend events as posts become due.
          </div>
        ) : isRejected ? (
          <div className="alert alert--error">
            Campaign rejected. Publishing is paused.
          </div>
        ) : unscheduledPosts.length > 0 ? (
          <div className="alert alert--warning">
            {unscheduledPosts.length} post{unscheduledPosts.length === 1 ? '' : 's'} still need selected publish times before approval.
          </div>
        ) : (
          <div className="alert alert--success">
            All posts have selected schedule times and are ready for approval.
          </div>
        )}

        {mutationError ? <div className="alert alert--error">{mutationError}</div> : null}

        {data.posts.length ? (
          <div className="grid grid--posts">
            {data.posts.map((post) => (
              <PostCard
                key={post.id}
                post={post}
                draft={drafts[post.id] || { copy: post.copy, image_prompt: post.image_prompt || '', image_url: post.image_url || '', publishAt: '' }}
                suggestion={suggestions[post.id]}
                canEdit={data.campaign.status !== 'completed' && post.status !== 'published'}
                saving={savingPostId === post.id}
                onDraftChange={setDraftValue}
                onUseSuggestion={useSuggestedTime}
                onSavePost={savePost}
                onSaveSchedule={saveSchedule}
              />
            ))}
          </div>
        ) : (
          <EmptyState
            title="No drafts yet"
            description="The agent is still generating content. Live events will appear below."
          />
        )}

        {canApprove ? (
          <div className="approval-box">
            <textarea
              placeholder="Feedback for rejection or revision"
              value={feedback}
              onChange={(event) => setFeedback(event.target.value)}
            />

            <div className="form-actions">
              <button
                type="button"
                className="button button--primary"
                onClick={() => submitDecision('approved')}
                disabled={unscheduledPosts.length > 0}
              >
                Approve Campaign
              </button>

              <button
                type="button"
                className="button button--danger"
                onClick={() => submitDecision('rejected')}
              >
                Reject with Feedback
              </button>
            </div>
          </div>
        ) : null}
      </section>

      <section className="card">
        <details open>
          <summary>Agent Trace</summary>

          <div className="trace">
            {trace.map((event, index) => (
              <pre key={`${event.timestamp || 'trace'}-${index}`}>
                {JSON.stringify(event, null, 2)}
              </pre>
            ))}
          </div>
        </details>
      </section>
    </div>
  );
}
