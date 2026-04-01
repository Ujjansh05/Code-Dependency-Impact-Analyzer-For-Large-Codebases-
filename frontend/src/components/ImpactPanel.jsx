import React from 'react';

/** Displays affected nodes + AI explanation. */
export default function ImpactPanel({ result }) {
  if (!result) return null;

  const { target, affected_nodes, explanation, total_affected } = result;

  return (
    <div className="card">
      <h3 className="card__title">
         Impact Results — <span style={{ color: 'var(--accent-cyan)' }}>{target}</span>
      </h3>

      <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 'var(--space-md)' }}>
        <strong style={{ color: total_affected > 5 ? 'var(--accent-red)' : 'var(--accent-green)' }}>
          {total_affected}
        </strong>{' '}
        affected {total_affected === 1 ? 'component' : 'components'} found
      </p>

      <div className="impact-panel" id="impact-nodes-list">
        {affected_nodes.map((node, i) => (
          <div key={node.id || i} className="impact-panel__node">
            <span
              className={`impact-panel__node-dot impact-panel__node-dot--${node.type.toLowerCase()}`}
            />
            <span>{node.name}</span>
            <span style={{ marginLeft: 'auto', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              {node.type}
            </span>
          </div>
        ))}
      </div>

      {explanation && (
        <div className="impact-panel__explanation" id="ai-explanation">
          {explanation}
        </div>
      )}
    </div>
  );
}
