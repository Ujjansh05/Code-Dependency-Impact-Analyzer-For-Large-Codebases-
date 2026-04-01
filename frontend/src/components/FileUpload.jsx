import React, { useState, useRef } from 'react';
import { uploadCodebase } from '../api/client';

/** Drag-and-drop / file picker for uploading codebase zip files. */
export default function FileUpload({ onUploadComplete }) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState(null);
  const fileInputRef = useRef(null);

  const handleFile = async (file) => {
    if (!file || !file.name.endsWith('.zip')) {
      setStatus({ type: 'error', text: 'Please upload a .zip file.' });
      return;
    }

    setUploading(true);
    setStatus(null);

    try {
      const result = await uploadCodebase(file);
      setStatus({
        type: 'success',
        text: `${result.files_parsed} files parsed, ${result.vertices_count} nodes, ${result.edges_count} edges`,
      });
      onUploadComplete?.();
    } catch (err) {
      setStatus({
        type: 'error',
        text: err.response?.data?.detail || 'Upload failed.',
      });
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    handleFile(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const handleClick = () => fileInputRef.current?.click();

  const handleInputChange = (e) => {
    const file = e.target.files[0];
    handleFile(file);
  };

  return (
    <div className="card">
      <h3 className="card__title"> Upload Codebase</h3>

      <div
        id="file-dropzone"
        className={`file-upload__dropzone ${isDragging ? 'file-upload__dropzone--active' : ''}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={handleClick}
        role="button"
        tabIndex={0}
      >
        {uploading ? (
          <>
            <div className="spinner" style={{ margin: '0 auto var(--space-sm)' }} />
            <p className="file-upload__text">Parsing codebase…</p>
          </>
        ) : (
          <>
            <div className="file-upload__icon"></div>
            <p className="file-upload__text">
              Drop a <strong>.zip</strong> file here or <strong>click to browse</strong>
            </p>
          </>
        )}
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept=".zip"
        style={{ display: 'none' }}
        onChange={handleInputChange}
      />

      {status && (
        <p
          style={{
            marginTop: 'var(--space-sm)',
            fontSize: '0.8rem',
            color: status.type === 'error' ? 'var(--accent-red)' : 'var(--accent-green)',
          }}
        >
          {status.text}
        </p>
      )}
    </div>
  );
}
