import axios from 'axios';

/**
 * GraphXploit API client.
 *
 * Authentication
 * ──────────────
 * Every request carries the X-API-Key header.  The key is read (in
 * priority order) from:
 *
 *   1. window.__GX_API_KEY__  — injected by `graphxploit serve` into
 *      the built index.html so the key is available instantly.
 *   2. localStorage key "gx_api_key" — lets users paste the key once
 *      in the browser when running the raw dev server (npm run dev).
 *
 * If neither source yields a key the header is omitted and the backend
 * will return 401 for every protected endpoint.
 */

function _resolveApiKey() {
  // Source 1: injected by the CLI at build time or via a <script> in index.html.
  if (typeof window !== 'undefined' && window.__GX_API_KEY__) {
    return window.__GX_API_KEY__;
  }
  // Source 2: user-managed local storage (dev-server fallback).
  try {
    return localStorage.getItem('gx_api_key') || '';
  } catch {
    return '';
  }
}

const api = axios.create({
  baseURL: '/api',
  timeout: 120_000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach the API key before every request.
api.interceptors.request.use((config) => {
  const key = _resolveApiKey();
  if (key) {
    config.headers['X-API-Key'] = key;
  }
  return config;
});

// ── Codebase upload ──────────────────────────────────────────────────────────

/** Upload a codebase zip file for parsing. */
export async function uploadCodebase(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300_000,
  });
  return response.data;
}

// ── Analysis ─────────────────────────────────────────────────────────────────

/** Run an impact analysis query. */
export async function analyzeImpact(query, maxDepth = 5, inferenceMode = 'fast') {
  const response = await api.post('/analyze', {
    query,
    max_depth: maxDepth,
    inference_mode: inferenceMode,
  });
  return response.data;
}

// ── Graph visualization ───────────────────────────────────────────────────────

/** Fetch the full graph data for visualization. */
export async function fetchGraphData() {
  const response = await api.get('/graph-data');
  return response.data;
}

// ── Code editor ───────────────────────────────────────────────────────────────

/** Fetch the content of a source file (relative to the upload directory). */
export async function getFileContent(path) {
  const response = await api.get('/file', { params: { path } });
  return response.data;
}

/** Update the content of a source file (relative to the upload directory). */
export async function updateFileContent(path, content) {
  const response = await api.put('/file', { content }, { params: { path } });
  return response.data;
}

// ── Projects ──────────────────────────────────────────────────────────────────

/** Fetch the list of registered projects. */
export async function fetchProjects() {
  const response = await api.get('/projects');
  return response.data;
}

/** Load a registered project by ID. */
export async function loadProject(projectId) {
  const response = await api.post(`/projects/${projectId}/load`);
  return response.data;
}

// ── Model management ──────────────────────────────────────────────────────────

/** Fetch all mounted models. */
export async function fetchModels() {
  const response = await api.get('/models');
  return response.data;
}

/** Get the currently active model. */
export async function getActiveModel() {
  const response = await api.get('/models/active');
  return response.data;
}

/** Mount a new model. */
export async function mountModel(config) {
  const response = await api.post('/models', config);
  return response.data;
}

/** Set a model as active. */
export async function setActiveModel(modelId) {
  const response = await api.put(`/models/${modelId}/active`);
  return response.data;
}

/** Delete a mounted model. */
export async function deleteModel(modelId) {
  const response = await api.delete(`/models/${modelId}`);
  return response.data;
}

/** Health check a specific model. */
export async function checkModelHealth(modelId) {
  const response = await api.get(`/models/${modelId}/health`);
  return response.data;
}

/** Probe a model for capabilities. */
export async function probeModel(modelId) {
  const response = await api.post(`/models/${modelId}/probe`);
  return response.data;
}

/** Test a model configuration without saving it. */
export async function testModelConfig(config) {
  const response = await api.post('/models/test', config);
  return response.data;
}

export default api;
