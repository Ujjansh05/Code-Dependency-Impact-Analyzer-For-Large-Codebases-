import React, { useState, useEffect } from 'react';
import { fetchProjects, loadProject } from '../api/client';

export default function ProjectSwitcher({ onProjectLoaded }) {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingId, setLoadingId] = useState(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    fetchProjects()
      .then((data) => setProjects(data.projects || []))
      .catch(() => {});
  }, []);

  const handleLoad = async (project) => {
    setLoadingId(project.id);
    setLoading(true);
    try {
      await loadProject(project.id);
      if (onProjectLoaded) {
        onProjectLoaded(project);
      }
    } catch (err) {
      console.error('Failed to load project:', err);
    } finally {
      setLoading(false);
      setLoadingId(null);
    }
  };

  if (projects.length === 0) return null;

  return (
    <div className="card project-switcher">
      <div 
        className="project-switcher__header"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="card__title" style={{ margin: 0, cursor: 'pointer' }}>
          My Projects ({projects.length})
        </span>
        <span className="project-switcher__toggle">
          {expanded ? '▾' : '▸'}
        </span>
      </div>

      {expanded && (
        <div className="project-switcher__list">
          {projects.map((p) => (
            <div key={p.id} className="project-switcher__item">
              <div className="project-switcher__info">
                <span className="project-switcher__name">{p.name}</span>
                <span className="project-switcher__meta">
                  {p.files} files · {p.vertices} vertices
                </span>
              </div>
              <button
                className="btn btn--small"
                disabled={loading}
                onClick={() => handleLoad(p)}
              >
                {loadingId === p.id ? '...' : 'Load'}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
