import { NavLink } from 'react-router-dom';

const links = [
  { to: '/', label: 'Home' },
  { to: '/campaigns/new', label: 'Create Campaign' },
  { to: '/campaigns', label: 'Campaigns' },
  { to: '/approvals', label: 'Approval Center' },
  { to: '/analytics', label: 'Analytics' },
  { to: '/api-console', label: 'API Console' },
  { to: '/settings', label: 'Settings' },
];

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand__eyebrow">AI Marketing Ops</span>
        <h1>Agentic Campaign Manager</h1>
      </div>
      <nav className="nav">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.to === '/'}
            className={({ isActive }) => `nav__link${isActive ? ' nav__link--active' : ''}`}
          >
            {link.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
