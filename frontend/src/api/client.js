import axios from 'axios';

/** API client for the Code Dependency Impact Analyzer backend. */

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
  },
});

/** Upload a codebase zip file for parsing. */
export async function uploadCodebase(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000,
  });
  return response.data;
}

/** Run an impact analysis query. */
export async function analyzeImpact(query, maxDepth = 5, inferenceMode = 'fast') {
  const response = await api.post('/analyze', {
    query,
    max_depth: maxDepth,
    inference_mode: inferenceMode,
  });
  return response.data;
}

/** Fetch the full graph data for visualization. */
export async function fetchGraphData() {
  const response = await api.get('/graph-data');
  return response.data;
}

/** Fetch the content of a source file. */
export async function getFileContent(path) {
  const response = await api.get('/file', { params: { path } });
  return response.data;
}

/** Update the content of a source file. */
export async function updateFileContent(path, content) {
  const response = await api.put('/file', { content }, { params: { path } });
  return response.data;
}

/** Fetch the list of registered projects. */
export async function fetchProjects() {
  const response = await api.get('/projects');
  return response.data;
}

/** Load a registered project by ID (re-parses and updates graph CSVs). */
export async function loadProject(projectId) {
  const response = await api.post(`/projects/${projectId}/load`);
  return response.data;
}

export default api;
