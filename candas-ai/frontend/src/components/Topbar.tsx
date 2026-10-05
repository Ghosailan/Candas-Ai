import { Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

export function Topbar() {
  const { user, logout } = useAuth();

  return (
    <header className="topbar">
      <div>
        <div className="topbar__label">Campaign Command Center</div>
        <div className="topbar__subtle">Nothing will be published until an approver signs off.</div>
      </div>
      <div className="topbar__actions">
        <Link to="/campaigns/new" className="button button--primary">
          Create New Campaign
        </Link>
        <div className="user-chip">
          <strong>{user?.name}</strong>
          <span>{user?.role}</span>
        </div>
        <button type="button" className="button button--ghost" onClick={logout}>
          Logout
        </button>
      </div>
    </header>
  );
}
