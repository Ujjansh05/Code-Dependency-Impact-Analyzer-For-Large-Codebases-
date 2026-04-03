import React, { useState, useCallback } from 'react';
import GraphCanvas from './components/GraphCanvas';
import QueryInput from './components/QueryInput';
import ImpactPanel from './components/ImpactPanel';
import FileUpload from './components/FileUpload';
import { analyzeImpact, fetchGraphData } from './api/client';

export default function App() {
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [impactResult, setImpactResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [highlightedNodes, setHighlightedNodes] = useState([]);


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

  return (
    <div className="app">

      <header className="app__header">
        <div className="app__logo">
          <span className="app__logo-icon" />
          Code Dependency Impact Analyzer
        </div>
        <div className="app__status">
          <span className="app__status-dot" />
          System Online
        </div>
      </header>


      <aside className="app__sidebar">
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
        <GraphCanvas data={graphData} highlightedNodes={highlightedNodes} />
      </main>
    </div>
  );
}
