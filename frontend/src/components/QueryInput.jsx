import React, { useState } from 'react';

/** Natural language search bar for impact queries. */
export default function QueryInput({ onSubmit, loading = false }) {
  const [query, setQuery] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (trimmed && !loading) {
      onSubmit(trimmed);
    }
  };

  return (
    <div className="card">
      <h3 className="card__title"> Impact Query</h3>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
        <input
          id="query-input"
          className="input"
          type="text"
          placeholder="What happens if I change the login function?"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={loading}
        />
        <button
          id="analyze-btn"
          className="btn btn--primary"
          type="submit"
          disabled={!query.trim() || loading}
        >
          {loading ? (
            <>
              <span className="spinner" />
              Analyzing…
            </>
          ) : (
            'Analyze Impact'
          )}
        </button>
      </form>
    </div>
  );
}
