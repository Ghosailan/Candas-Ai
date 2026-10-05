import { Link } from 'react-router-dom';

const cards = [
  { title: 'Create Campaign', description: 'Start a guided campaign brief and launch the agent workflow.', to: '/campaigns/new' },
  { title: 'Campaigns', description: 'Browse active, paused, failed, and completed campaign runs.', to: '/campaigns' },
  { title: 'Approval Center', description: 'Review pending campaigns before any publishing action is allowed.', to: '/approvals' },
  { title: 'Analytics', description: 'Compare platform performance, reach, clicks, and best posts.', to: '/analytics' },
  { title: 'API Console', description: 'Inspect and call backend endpoints using the live OpenAPI document.', to: '/api-console' },
];

export function Home() {
  return (
    <div className="stack">
      <section className="hero">
        <span className="hero__eyebrow">Agentic AI Marketing Dashboard</span>
        <h2>Agentic Campaign Manager</h2>
        <p>Plan, generate, approve, schedule, and analyze social media campaigns with agentic AI.</p>
        <Link to="/campaigns/new" className="button button--primary">
          Create New Campaign
        </Link>
      </section>
      <section className="grid grid--cards">
        {cards.map((card) => (
          <Link key={card.title} to={card.to} className="card quick-card">
            <h3>{card.title}</h3>
            <p>{card.description}</p>
          </Link>
        ))}
      </section>
    </div>
  );
}
