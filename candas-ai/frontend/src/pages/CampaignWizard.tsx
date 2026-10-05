import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiFetch } from '../api/client';
import { useAuth } from '../auth/AuthContext';

const platforms = ['instagram', 'facebook', 'linkedin', 'twitter', 'tiktok', 'youtube', 'telegram'];
const goals = ['brand awareness', 'engagement', 'traffic', 'conversions', 'product launch'];

export function CampaignWizard() {
  const navigate = useNavigate();
  const { token } = useAuth();
  const [step, setStep] = useState(0);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [tone, setTone] = useState('');
  const [audience, setAudience] = useState('');
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(['instagram', 'linkedin']);
  const [selectedGoals, setSelectedGoals] = useState<string[]>(['engagement']);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const steps = ['Product Brief', 'Platforms', 'Goals', 'Review & Launch'];

  function toggle(value: string, collection: string[], setter: (values: string[]) => void) {
    setter(collection.includes(value) ? collection.filter((item) => item !== value) : [...collection, value]);
  }

  async function submit() {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<{ campaign_id: string }>(
        '/campaigns',
        {
          method: 'POST',
          body: JSON.stringify({
            title,
            brief: `${description}\nBrand tone: ${tone}`,
            platforms: selectedPlatforms.map((platform) => (platform === 'twitter' ? 'twitter' : platform)),
            goals: selectedGoals,
            target_audience: {
              summary: audience,
            },
          }),
        },
        token,
      );
      navigate(`/campaigns/${data.campaign_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Campaign creation failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="stack">
      <section className="card">
        <div className="wizard-steps">
          {steps.map((label, index) => (
            <div key={label} className={`wizard-step${index === step ? ' wizard-step--active' : ''}`}>
              <span>{index + 1}</span>
              {label}
            </div>
          ))}
        </div>
      </section>
      <section className="card form-card">
        {step === 0 ? (
          <>
            <h2>Product Brief</h2>
            <label>
              Campaign title
              <input value={title} onChange={(event) => setTitle(event.target.value)} minLength={3} required />
            </label>
            <label>
              Product description
              <textarea value={description} onChange={(event) => setDescription(event.target.value)} minLength={10} />
            </label>
            <label>
              Brand tone
              <input value={tone} onChange={(event) => setTone(event.target.value)} />
            </label>
            <label>
              Target audience
              <textarea value={audience} onChange={(event) => setAudience(event.target.value)} />
            </label>
          </>
        ) : null}
        {step === 1 ? (
          <>
            <h2>Platforms</h2>
            <div className="choice-grid">
              {platforms.map((platform) => (
                <button
                  key={platform}
                  type="button"
                  className={`choice${selectedPlatforms.includes(platform) ? ' choice--selected' : ''}`}
                  onClick={() => toggle(platform, selectedPlatforms, setSelectedPlatforms)}
                >
                  {platform}
                </button>
              ))}
            </div>
          </>
        ) : null}
        {step === 2 ? (
          <>
            <h2>Goals</h2>
            <div className="choice-grid">
              {goals.map((goal) => (
                <button
                  key={goal}
                  type="button"
                  className={`choice${selectedGoals.includes(goal) ? ' choice--selected' : ''}`}
                  onClick={() => toggle(goal, selectedGoals, setSelectedGoals)}
                >
                  {goal}
                </button>
              ))}
            </div>
          </>
        ) : null}
        {step === 3 ? (
          <>
            <h2>Review & Launch</h2>
            <div className="review-grid">
              <div>
                <strong>Title</strong>
                <p>{title}</p>
              </div>
              <div>
                <strong>Platforms</strong>
                <p>{selectedPlatforms.join(', ')}</p>
              </div>
              <div>
                <strong>Goals</strong>
                <p>{selectedGoals.join(', ')}</p>
              </div>
              <div>
                <strong>Audience</strong>
                <p>{audience}</p>
              </div>
            </div>
          </>
        ) : null}
        {error ? <div className="alert alert--error">{error}</div> : null}
        <div className="form-actions">
          <button type="button" className="button button--ghost" disabled={step === 0} onClick={() => setStep(step - 1)}>
            Back
          </button>
          {step < steps.length - 1 ? (
            <button
              type="button"
              className="button button--primary"
              onClick={() => setStep(step + 1)}
              disabled={(step === 0 && (title.length < 3 || description.length < 10)) || (step === 1 && !selectedPlatforms.length) || (step === 2 && !selectedGoals.length)}
            >
              Next
            </button>
          ) : (
            <button type="button" className="button button--primary" onClick={submit} disabled={loading}>
              {loading ? 'Launching...' : 'Launch Campaign'}
            </button>
          )}
        </div>
      </section>
    </div>
  );
}
