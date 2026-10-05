const NODES = ['memory', 'planner', 'researcher', 'creator', 'reflection', 'approval', 'scheduler', 'publisher', 'analyst'];

type NodeStatus = 'waiting' | 'running' | 'completed' | 'failed';

export function AgentTimeline({ statuses }: { statuses: Record<string, NodeStatus> }) {
  return (
    <section className="card">
      <div className="card__header">
        <h3>Agent Timeline</h3>
      </div>
      <div className="timeline">
        {NODES.map((node) => (
          <div key={node} className={`timeline__item timeline__item--${statuses[node] || 'waiting'}`}>
            <div className="timeline__dot" />
            <div>
              <div className="timeline__title">{node}</div>
              <div className="timeline__status">{statuses[node] || 'waiting'}</div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
