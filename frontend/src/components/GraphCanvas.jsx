import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Network } from 'vis-network';
import { DataSet } from 'vis-data';

const EDGE_COLORS = {
  CALLS: '#3b82f6',
  IMPORTS: '#8b5cf6',
  CONTAINS: '#64748b',
};

const NODE_COLORS = {
  File: { background: '#8b5cf6', border: '#7c3aed', highlight: { background: '#a78bfa', border: '#8b5cf6' } },
  Function: { background: '#06b6d4', border: '#0891b2', highlight: { background: '#22d3ee', border: '#06b6d4' } },
  highlighted: { background: '#ef4444', border: '#ef4444', highlight: { background: '#f87171', border: '#ef4444' } },
};

const DIM_OPACITY = 0.12;

export default function GraphCanvas({ data, highlightedNodes = [], onNodeSelect }) {
  const containerRef = useRef(null);
  const networkRef = useRef(null);
  const nodesRef = useRef(null);
  const edgesRef = useRef(null);

  const [search, setSearch] = useState('');
  const [filters, setFilters] = useState({ CALLS: true, IMPORTS: true, CONTAINS: true });
  const [selectedNode, setSelectedNode] = useState(null);
  const [nodeInfo, setNodeInfo] = useState(null);
  const [stats, setStats] = useState({ nodes: 0, edges: 0, files: 0, functions: 0 });
  const [physicsEnabled, setPhysicsEnabled] = useState(true);

  // Compute stats
  useEffect(() => {
    if (!data.nodes.length) return;
    setStats({
      nodes: data.nodes.length,
      edges: data.edges.length,
      files: data.nodes.filter(n => n.type === 'File').length,
      functions: data.nodes.filter(n => n.type === 'Function').length,
    });
  }, [data]);

  // Build & render the network
  useEffect(() => {
    if (!containerRef.current || !data.nodes.length) return;

    const highlightSet = new Set(highlightedNodes);

    const visNodes = new DataSet(
      data.nodes.map((node) => ({
        id: node.id,
        label: node.label,
        group: node.type,
        shape: node.type === 'File' ? 'box' : 'dot',
        size: node.type === 'File' ? 22 : 12,
        font: { color: '#e2e8f0', size: node.type === 'File' ? 13 : 11, face: "'Inter', sans-serif" },
        borderWidth: node.type === 'File' ? 2 : 1,
        color: highlightSet.has(node.id) ? NODE_COLORS.highlighted : NODE_COLORS[node.type] || NODE_COLORS.Function,
        shadow: highlightSet.has(node.id)
          ? { enabled: true, color: 'rgba(239,68,68,0.4)', size: 15 }
          : { enabled: true, color: 'rgba(0,0,0,0.25)', size: 6 },
        _type: node.type,
        _filepath: node.filepath,
      }))
    );

    const visEdges = new DataSet(
      data.edges
        .filter(e => filters[e.type] !== false)
        .map((edge, i) => ({
          id: `edge-${i}`,
          from: edge.source,
          to: edge.target,
          arrows: { to: { enabled: true, scaleFactor: 0.5 } },
          color: { color: EDGE_COLORS[edge.type] || '#64748b', opacity: 0.5, highlight: EDGE_COLORS[edge.type] || '#94a3b8' },
          width: edge.type === 'CALLS' ? 1.8 : 1,
          dashes: edge.type === 'CONTAINS' ? [4, 4] : false,
          smooth: { type: 'cubicBezier', roundness: 0.35 },
          title: edge.type,
          _edgeType: edge.type,
        }))
    );

    nodesRef.current = visNodes;
    edgesRef.current = visEdges;

    const options = {
      physics: {
        enabled: physicsEnabled,
        solver: 'forceAtlas2Based',
        forceAtlas2Based: {
          gravitationalConstant: -40,
          centralGravity: 0.006,
          springLength: 140,
          springConstant: 0.06,
          damping: 0.45,
          avoidOverlap: 0.4,
        },
        stabilization: { iterations: 250, fit: true },
      },
      interaction: {
        hover: true,
        tooltipDelay: 100,
        zoomView: true,
        dragView: true,
        multiselect: true,
        navigationButtons: false,
        keyboard: { enabled: true, speed: { x: 10, y: 10, zoom: 0.03 } },
      },
      layout: { improvedLayout: true },
      nodes: { chosen: true },
      edges: { chosen: true },
    };

    const net = new Network(containerRef.current, { nodes: visNodes, edges: visEdges }, options);
    networkRef.current = net;

    // ── Single click: highlight neighbors ──
    net.on('click', (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        const connectedNodes = net.getConnectedNodes(nodeId);
        const connectedEdges = net.getConnectedEdges(nodeId);
        const allNodes = visNodes.getIds();
        const allEdges = visEdges.getIds();

        // Dim everything
        const nodeUpdates = allNodes.map(id => ({
          id,
          opacity: (id === nodeId || connectedNodes.includes(id)) ? 1 : DIM_OPACITY,
          font: { color: (id === nodeId || connectedNodes.includes(id)) ? '#e2e8f0' : 'rgba(226,232,240,0.15)' },
        }));
        const edgeUpdates = allEdges.map(id => ({
          id,
          color: { ...visEdges.get(id).color, opacity: connectedEdges.includes(id) ? 0.8 : 0.04 },
        }));
        visNodes.update(nodeUpdates);
        visEdges.update(edgeUpdates);

        // Show info
        const nodeData = data.nodes.find(n => n.id === nodeId);
        if (nodeData) {
          const incoming = data.edges.filter(e => e.target === nodeId);
          const outgoing = data.edges.filter(e => e.source === nodeId);
          setNodeInfo({
            ...nodeData,
            inDegree: incoming.length,
            outDegree: outgoing.length,
            connections: connectedNodes.length,
            incomingTypes: [...new Set(incoming.map(e => e.type))],
            outgoingTypes: [...new Set(outgoing.map(e => e.type))],
          });
          setSelectedNode(nodeId);
        }
      } else {
        // Click on canvas: reset opacity
        const allNodes = visNodes.getIds();
        const allEdges = visEdges.getIds();
        visNodes.update(allNodes.map(id => ({ id, opacity: 1, font: { color: '#e2e8f0' } })));
        visEdges.update(allEdges.map(id => ({ id, color: { ...visEdges.get(id).color, opacity: 0.5 } })));
        setNodeInfo(null);
        setSelectedNode(null);
      }
    });

    // ── Double click: open code editor ──
    if (onNodeSelect) {
      net.on('doubleClick', (params) => {
        if (params.nodes.length > 0) {
          const nodeId = params.nodes[0];
          const selectedNodeInfo = data.nodes.find(n => n.id === nodeId);
          if (selectedNodeInfo) {
            onNodeSelect(selectedNodeInfo);
          }
        }
      });
    }

    // ── Hover cursor ──
    net.on('hoverNode', () => { containerRef.current.style.cursor = 'pointer'; });
    net.on('blurNode', () => { containerRef.current.style.cursor = 'default'; });

    return () => { net.destroy(); };
  }, [data, highlightedNodes, onNodeSelect, filters, physicsEnabled]);

  // ── Search: find and focus ──
  const handleSearch = useCallback((term) => {
    setSearch(term);
    if (!term.trim() || !networkRef.current || !nodesRef.current) return;

    const lower = term.toLowerCase();
    const matches = data.nodes.filter(n => n.label.toLowerCase().includes(lower));

    if (matches.length > 0) {
      const matchIds = matches.map(m => m.id);
      networkRef.current.selectNodes(matchIds);
      if (matches.length === 1) {
        networkRef.current.focus(matchIds[0], { scale: 1.5, animation: { duration: 600, easingFunction: 'easeInOutQuad' } });
      } else {
        networkRef.current.fit({ nodes: matchIds, animation: { duration: 600, easingFunction: 'easeInOutQuad' } });
      }

      // Highlight matches, dim the rest
      const allNodes = nodesRef.current.getIds();
      const matchSet = new Set(matchIds);
      nodesRef.current.update(allNodes.map(id => ({
        id,
        opacity: matchSet.has(id) ? 1 : DIM_OPACITY,
        font: { color: matchSet.has(id) ? '#e2e8f0' : 'rgba(226,232,240,0.15)' },
      })));
    }
  }, [data]);

  const clearSearch = useCallback(() => {
    setSearch('');
    if (!nodesRef.current) return;
    const allNodes = nodesRef.current.getIds();
    nodesRef.current.update(allNodes.map(id => ({ id, opacity: 1, font: { color: '#e2e8f0' } })));
    if (networkRef.current) networkRef.current.unselectAll();
  }, []);

  // ── Zoom controls ──
  const zoomIn = () => { const s = networkRef.current?.getScale(); networkRef.current?.moveTo({ scale: s * 1.4, animation: { duration: 300 } }); };
  const zoomOut = () => { const s = networkRef.current?.getScale(); networkRef.current?.moveTo({ scale: s / 1.4, animation: { duration: 300 } }); };
  const fitAll = () => { networkRef.current?.fit({ animation: { duration: 500, easingFunction: 'easeInOutQuad' } }); };

  // ── Filter toggle ──
  const toggleFilter = (type) => {
    setFilters(prev => ({ ...prev, [type]: !prev[type] }));
  };

  if (!data.nodes.length) {
    return (
      <div className="graph-canvas">
        <div className="graph-canvas__empty">
          <div className="graph-canvas__empty-icon">⟁</div>
          <p>Upload a codebase or load a project to visualize its dependency graph</p>
          <p className="graph-canvas__empty-hint">Double-click a file node to open it in the code editor</p>
        </div>
      </div>
    );
  }

  return (
    <div className="graph-canvas">
      {/* ── Toolbar ── */}
      <div className="graph-toolbar">
        <div className="graph-toolbar__search">
          <input
            type="text"
            placeholder="Search nodes…"
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
            className="graph-toolbar__input"
          />
          {search && (
            <button className="graph-toolbar__clear" onClick={clearSearch}>✕</button>
          )}
        </div>

        <div className="graph-toolbar__filters">
          {Object.entries(EDGE_COLORS).map(([type, color]) => (
            <button
              key={type}
              className={`graph-toolbar__filter ${filters[type] ? 'active' : 'inactive'}`}
              onClick={() => toggleFilter(type)}
              style={{ '--filter-color': color }}
            >
              <span className="graph-toolbar__filter-dot" />
              {type}
            </button>
          ))}
        </div>

        <div className="graph-toolbar__actions">
          <button className="graph-toolbar__btn" onClick={zoomIn} title="Zoom In">+</button>
          <button className="graph-toolbar__btn" onClick={zoomOut} title="Zoom Out">−</button>
          <button className="graph-toolbar__btn" onClick={fitAll} title="Fit All">⊡</button>
          <button
            className={`graph-toolbar__btn ${physicsEnabled ? 'active' : ''}`}
            onClick={() => setPhysicsEnabled(p => !p)}
            title={physicsEnabled ? 'Disable Physics' : 'Enable Physics'}
          >
            ⚛
          </button>
        </div>
      </div>

      {/* ── Graph ── */}
      <div className="graph-canvas__container" ref={containerRef} />

      {/* ── Legend ── */}
      <div className="graph-legend">
        <div className="graph-legend__item">
          <span className="graph-legend__dot" style={{ background: '#8b5cf6', borderRadius: '3px' }} />
          <span>File</span>
        </div>
        <div className="graph-legend__item">
          <span className="graph-legend__dot" style={{ background: '#06b6d4' }} />
          <span>Function</span>
        </div>
        <div className="graph-legend__sep" />
        <div className="graph-legend__item">
          <span className="graph-legend__line" style={{ background: '#3b82f6' }} />
          <span>Calls</span>
        </div>
        <div className="graph-legend__item">
          <span className="graph-legend__line" style={{ background: '#8b5cf6' }} />
          <span>Imports</span>
        </div>
        <div className="graph-legend__item">
          <span className="graph-legend__line dashed" style={{ background: '#64748b' }} />
          <span>Contains</span>
        </div>
      </div>

      {/* ── Stats badge ── */}
      <div className="graph-stats">
        <span>{stats.files} files</span>
        <span className="graph-stats__sep">·</span>
        <span>{stats.functions} functions</span>
        <span className="graph-stats__sep">·</span>
        <span>{stats.edges} edges</span>
      </div>

      {/* ── Node Info Panel ── */}
      {nodeInfo && (
        <div className="graph-node-info">
          <div className="graph-node-info__header">
            <span className={`graph-node-info__badge ${nodeInfo.type === 'File' ? 'file' : 'func'}`}>
              {nodeInfo.type}
            </span>
            <button className="graph-node-info__close" onClick={() => { setNodeInfo(null); setSelectedNode(null); }}>✕</button>
          </div>
          <h3 className="graph-node-info__name">{nodeInfo.label}</h3>
          {nodeInfo.filepath && (
            <p className="graph-node-info__path">{nodeInfo.filepath.split(/[\\/]/).slice(-3).join('/')}</p>
          )}
          <div className="graph-node-info__stats">
            <div className="graph-node-info__stat">
              <span className="graph-node-info__stat-value">{nodeInfo.inDegree}</span>
              <span className="graph-node-info__stat-label">Incoming</span>
            </div>
            <div className="graph-node-info__stat">
              <span className="graph-node-info__stat-value">{nodeInfo.outDegree}</span>
              <span className="graph-node-info__stat-label">Outgoing</span>
            </div>
            <div className="graph-node-info__stat">
              <span className="graph-node-info__stat-value">{nodeInfo.connections}</span>
              <span className="graph-node-info__stat-label">Connected</span>
            </div>
          </div>
          {nodeInfo.type === 'File' && (
            <button
              className="graph-node-info__edit-btn"
              onClick={() => onNodeSelect && onNodeSelect(nodeInfo)}
            >
              Open in Editor
            </button>
          )}
          <p className="graph-node-info__hint">Double-click node to edit</p>
        </div>
      )}
    </div>
  );
}
