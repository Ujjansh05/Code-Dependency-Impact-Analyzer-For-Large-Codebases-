import React, { useEffect, useRef } from 'react';
import { Network } from 'vis-network';
import { DataSet } from 'vis-data';

/** vis-network powered dependency graph visualization. */
export default function GraphCanvas({ data, highlightedNodes = [] }) {
  const containerRef = useRef(null);
  const networkRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return;
    if (!data.nodes.length) return;

    const highlightSet = new Set(highlightedNodes);


    const visNodes = new DataSet(
      data.nodes.map((node) => ({
        id: node.id,
        label: node.label,
        group: node.type,
        shape: node.type === 'File' ? 'box' : 'dot',
        size: node.type === 'File' ? 20 : 14,
        font: {
          color: '#e2e8f0',
          size: 12,
          face: "'Inter', sans-serif",
        },
        color: highlightSet.has(node.id)
          ? {
              background: '#ef4444',
              border: '#ef4444',
              highlight: { background: '#f87171', border: '#ef4444' },
            }
          : node.type === 'File'
            ? {
                background: '#8b5cf6',
                border: '#7c3aed',
                highlight: { background: '#a78bfa', border: '#8b5cf6' },
              }
            : {
                background: '#06b6d4',
                border: '#0891b2',
                highlight: { background: '#22d3ee', border: '#06b6d4' },
              },
        shadow: highlightSet.has(node.id)
          ? { enabled: true, color: 'rgba(239,68,68,0.4)', size: 15 }
          : { enabled: true, color: 'rgba(0,0,0,0.3)', size: 8 },
      }))
    );


    const edgeColors = {
      CALLS: '#3b82f6',
      IMPORTS: '#8b5cf6',
      CONTAINS: '#64748b',
    };

    const visEdges = new DataSet(
      data.edges.map((edge, i) => ({
        id: `edge-${i}`,
        from: edge.source,
        to: edge.target,
        arrows: 'to',
        color: {
          color: edgeColors[edge.type] || '#64748b',
          opacity: 0.6,
          highlight: edgeColors[edge.type] || '#94a3b8',
        },
        width: edge.type === 'CALLS' ? 2 : 1,
        dashes: edge.type === 'CONTAINS',
        smooth: { type: 'cubicBezier', roundness: 0.4 },
        title: edge.type,
      }))
    );

    const options = {
      physics: {
        solver: 'forceAtlas2Based',
        forceAtlas2Based: {
          gravitationalConstant: -30,
          centralGravity: 0.005,
          springLength: 120,
          springConstant: 0.08,
          damping: 0.4,
        },
        stabilization: { iterations: 200 },
      },
      interaction: {
        hover: true,
        tooltipDelay: 150,
        zoomView: true,
        dragView: true,
      },
      layout: {
        improvedLayout: true,
      },
    };

    networkRef.current = new Network(
      containerRef.current,
      { nodes: visNodes, edges: visEdges },
      options
    );

    return () => {
      if (networkRef.current) {
        networkRef.current.destroy();
      }
    };
  }, [data, highlightedNodes]);

  if (!data.nodes.length) {
    return (
      <div className="graph-canvas">
        <div className="graph-canvas__empty">
          <div className="graph-canvas__empty-icon"></div>
          <p>Upload a codebase to visualize its dependency graph</p>
        </div>
      </div>
    );
  }

  return (
    <div className="graph-canvas">
      <div className="graph-canvas__container" ref={containerRef} />
    </div>
  );
}
