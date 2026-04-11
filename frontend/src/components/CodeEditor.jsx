import React, { useState, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import { getFileContent, updateFileContent } from '../api/client';

export default function CodeEditor({ fileNode, onClose }) {
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState('');

  useEffect(() => {
    if (!fileNode || !fileNode.filepath) return;
    
    setLoading(true);
    setError(null);
    setSuccessMsg('');
    
    getFileContent(fileNode.filepath)
      .then((data) => {
        setContent(data.content);
      })
      .catch((err) => {
        setError(err.response?.data?.detail || 'Failed to load file context');
      })
      .finally(() => {
        setLoading(false);
      });
  }, [fileNode]);

  const handleEditorChange = (value) => {
    setContent(value);
  };

  const handleSave = async () => {
    if (!fileNode || !fileNode.filepath) return;
    
    setSaving(true);
    setError(null);
    setSuccessMsg('');
    
    try {
      await updateFileContent(fileNode.filepath, content);
      setSuccessMsg('File saved successfully!');
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save file');
    } finally {
      setSaving(false);
    }
  };

  if (!fileNode) return null;

  return (
    <div className="code-editor-panel">
      <div className="code-editor-panel__header">
        <div className="code-editor-panel__title">
          <span>{fileNode.label}</span>
          <span className="code-editor-panel__path">{fileNode.filepath}</span>
        </div>
        <button className="code-editor-panel__close" onClick={onClose}>×</button>
      </div>

      {error && <div className="code-editor-panel__error">{error}</div>}
      {successMsg && <div className="code-editor-panel__success">{successMsg}</div>}

      <div className="code-editor-panel__content">
        {loading ? (
          <div className="code-editor-panel__loading">Loading file...</div>
        ) : (
          <Editor
            height="100%"
            defaultLanguage="python"
            theme="vs-dark"
            value={content}
            onChange={handleEditorChange}
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              fontFamily: "'Inter', 'Consolas', monospace",
              scrollbar: { vertical: 'hidden', horizontal: 'hidden' },
              padding: { top: 16 }
            }}
          />
        )}
      </div>

      <div className="code-editor-panel__footer">
        <button 
          className="btn btn-primary" 
          onClick={handleSave} 
          disabled={loading || saving}
        >
          {saving ? 'Saving...' : 'Save File'}
        </button>
      </div>
    </div>
  );
}
