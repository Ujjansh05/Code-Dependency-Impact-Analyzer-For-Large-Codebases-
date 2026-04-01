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
export async function analyzeImpact(query, maxDepth = 5) {
  const response = await api.post('/analyze', {
    query,
    max_depth: maxDepth,
  });
  return response.data;
}

/** Fetch the full graph data for visualization. */
export async function fetchGraphData() {
  const response = await api.get('/graph-data');
  return response.data;
}

export default api;
