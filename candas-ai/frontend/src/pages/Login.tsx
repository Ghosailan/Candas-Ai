import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

export function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState('approver@example.com');
  const [name, setName] = useState('Local Approver');
  const [role, setRole] = useState('approver');
  const [orgName, setOrgName] = useState('Local Dev Organisation');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login({ email, name, role, org_name: orgName });
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to log in');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-shell">
      <form className="card login-card" onSubmit={handleSubmit}>
        <span className="hero__eyebrow">Local Auth</span>
        <h1>Agentic Campaign Manager</h1>
        <p>Use local JWT mode for development and production-test environments.</p>
        <label>
          Email
          <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required />
        </label>
        <label>
          Name
          <input value={name} onChange={(event) => setName(event.target.value)} required />
        </label>
        <label>
          Role
          <select value={role} onChange={(event) => setRole(event.target.value)}>
            <option value="viewer">viewer</option>
            <option value="editor">editor</option>
            <option value="approver">approver</option>
            <option value="admin">admin</option>
          </select>
        </label>
        <label>
          Organisation
          <input value={orgName} onChange={(event) => setOrgName(event.target.value)} required />
        </label>
        {error ? <div className="alert alert--error">{error}</div> : null}
        <button className="button button--primary" disabled={loading} type="submit">
          {loading ? 'Signing in...' : 'Generate Local JWT'}
        </button>
      </form>
    </div>
  );
}
