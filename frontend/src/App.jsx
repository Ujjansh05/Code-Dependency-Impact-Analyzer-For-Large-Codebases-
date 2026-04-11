import React, { useState, useCallback, useEffect } from 'react';
import GraphCanvas from './components/GraphCanvas';
import QueryInput from './components/QueryInput';
import ImpactPanel from './components/ImpactPanel';
import FileUpload from './components/FileUpload';
import CodeEditor from './components/CodeEditor';
import ProjectSwitcher from './components/ProjectSwitcher';
import ModelManager from './components/ModelManager';
import { analyzeImpact, fetchGraphData, getActiveModel } from './api/client';

export default function App() {
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [impactResult, setImpactResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [highlightedNodes, setHighlightedNodes] = useState([]);
  const [selectedFileNode, setSelectedFileNode] = useState(null);
  const [activeProject, setActiveProject] = useState(null);
  const [activeModelName, setActiveModelName] = useState(null);

  // Load active model name on mount
  const refreshActiveModel = useCallback(async () => {
    try {
      const data = await getActiveModel();
      if (data?.model) {
        setActiveModelName(data.model.name);
      } else {
        setActiveModelName(null);
      }
    } catch {
      setActiveModelName(null);
    }
  }, []);

  // Auto-load graph data on mount
  useEffect(() => {
    fetchGraphData()
      .then((data) => {
        if (data && data.nodes && data.nodes.length > 0) {
          setGraphData(data);
        }
      })
      .catch(() => {});

    refreshActiveModel();
  }, [refreshActiveModel]);

  const handleUploadComplete = useCallback(async () => {
    try {
      setError(null);
      const data = await fetchGraphData();
      setGraphData(data);
    } catch (err) {
      setError('Failed to load graph data.');
    }
  }, []);

  const handleAnalyze = useCallback(async (query, mode = 'fast') => {
    setLoading(true);
    setError(null);
    setImpactResult(null);
    setHighlightedNodes([]);

    try {
      const result = await analyzeImpact(query, 5, mode);
      setImpactResult(result);
      setHighlightedNodes(result.affected_nodes.map((n) => n.id));
    } catch (err) {
      setError(err.response?.data?.detail || 'Analysis failed. Check backend connection.');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleNodeSelect = useCallback((node) => {
    if (node.type === 'File') {
      setSelectedFileNode(node);
    }
  }, []);

  const handleProjectLoaded = useCallback(async (project) => {
    setActiveProject(project);
    setSelectedFileNode(null);
    setImpactResult(null);
    setHighlightedNodes([]);
    setError(null);

    try {
      const data = await fetchGraphData();
      setGraphData(data);
    } catch (err) {
      setError('Failed to load graph after switching project.');
    }
  }, []);

  return (
    <div className="app">
      <header className="app__header">
        <div className="app__logo">
          <span className="app__logo-icon" />
          GraphXploit
        </div>
        <div className="app__header-right">
          {activeModelName && (
            <span className="app__active-model" title="Active LLM Model">
              <span className="app__model-dot" />
              {activeModelName}
            </span>
          )}
          {activeProject && (
            <span className="app__active-project">
              {activeProject.name}
            </span>
          )}
          <div className="app__status">
            <span className="app__status-dot" />
            System Online
          </div>
        </div>
      </header>

      <aside className="app__sidebar">
        <ModelManager onModelChange={refreshActiveModel} />
        <ProjectSwitcher onProjectLoaded={handleProjectLoaded} />
        <FileUpload onUploadComplete={handleUploadComplete} />
        <QueryInput onSubmit={handleAnalyze} loading={loading} />

        {error && (
          <div className="card" style={{ borderColor: 'var(--accent-red)' }}>
            <p style={{ color: 'var(--accent-red)', fontSize: '0.85rem' }}>
              {error}
            </p>
          </div>
        )}

        {impactResult && <ImpactPanel result={impactResult} />}
      </aside>

      <main className="app__main">
        <div className={`app__canvas-container ${selectedFileNode ? 'has-editor' : ''}`}>
          <GraphCanvas
            data={graphData}
            highlightedNodes={highlightedNodes}
            onNodeSelect={handleNodeSelect}
          />
        </div>
        {selectedFileNode && (
          <CodeEditor
            fileNode={selectedFileNode}
            onClose={() => setSelectedFileNode(null)}
          />
        )}
      </main>
    </div>
  );
}
