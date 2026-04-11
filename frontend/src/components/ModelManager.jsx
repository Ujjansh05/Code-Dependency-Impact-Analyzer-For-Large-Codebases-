import React, { useState, useEffect, useCallback } from 'react';
import {
  fetchModels,
  mountModel,
  setActiveModel,
  deleteModel,
  testModelConfig,
} from '../api/client';

const PROVIDERS = [
  { id: 'ollama', label: 'Ollama', desc: 'Local LLMs (llama3, qwen, mistral)' },
  { id: 'openai', label: 'OpenAI', desc: 'GPT-4o, or any OpenAI-compatible API' },
  { id: 'huggingface', label: 'HuggingFace', desc: 'Inference API — any HF model' },
  { id: 'custom', label: 'Custom', desc: 'Any OpenAI-compatible endpoint' },
];

const DEFAULT_URLS = {
  ollama: 'http://localhost:11434',
  openai: 'https://api.openai.com/v1',
  huggingface: 'https://api-inference.huggingface.co/models',
  custom: '',
};

const DEFAULT_MODELS = {
  ollama: 'qwen2.5-coder:7b',
  openai: 'gpt-4o-mini',
  huggingface: 'mistralai/Mistral-7B-Instruct-v0.3',
  custom: '',
};

export default function ModelManager({ onModelChange }) {
  const [models, setModels] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [error, setError] = useState(null);

  // Form state
  const [provider, setProvider] = useState('ollama');
  const [baseUrl, setBaseUrl] = useState(DEFAULT_URLS.ollama);
  const [apiKey, setApiKey] = useState('');
  const [modelName, setModelName] = useState(DEFAULT_MODELS.ollama);
  const [displayName, setDisplayName] = useState('');

  const loadModels = useCallback(async () => {
    try {
      const data = await fetchModels();
      setModels(data.models || []);
    } catch {
      setModels([]);
    }
  }, []);

  useEffect(() => {
    loadModels();
  }, [loadModels]);

  const handleProviderChange = (newProvider) => {
    setProvider(newProvider);
    setBaseUrl(DEFAULT_URLS[newProvider] || '');
    setModelName(DEFAULT_MODELS[newProvider] || '');
    setApiKey('');
    setTestResult(null);
    setError(null);
  };

  const handleTest = async () => {
    setLoading(true);
    setTestResult(null);
    setError(null);
    try {
      const result = await testModelConfig({
        provider,
        base_url: baseUrl || null,
        api_key: apiKey || null,
        model_name: modelName,
      });
      setTestResult(result);
    } catch (err) {
      setError(err.response?.data?.detail || 'Test failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleMount = async () => {
    setLoading(true);
    setError(null);
    try {
      await mountModel({
        name: displayName || `${provider.charAt(0).toUpperCase() + provider.slice(1)} (${modelName})`,
        provider,
        base_url: baseUrl || null,
        api_key: apiKey || null,
        model_name: modelName,
        set_active: true,
      });
      setShowForm(false);
      resetForm();
      await loadModels();
      if (onModelChange) onModelChange();
    } catch (err) {
      setError(err.response?.data?.detail || 'Mount failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleSetActive = async (modelId) => {
    try {
      await setActiveModel(modelId);
      await loadModels();
      if (onModelChange) onModelChange();
    } catch (err) {
      setError('Failed to switch model.');
    }
  };

  const handleDelete = async (modelId) => {
    if (!window.confirm('Remove this model?')) return;
    try {
      await deleteModel(modelId);
      await loadModels();
      if (onModelChange) onModelChange();
    } catch {
      setError('Failed to delete model.');
    }
  };

  const resetForm = () => {
    setProvider('ollama');
    setBaseUrl(DEFAULT_URLS.ollama);
    setApiKey('');
    setModelName(DEFAULT_MODELS.ollama);
    setDisplayName('');
    setTestResult(null);
    setError(null);
  };

  const activeModel = models.find((m) => m.is_active);

  return (
    <div className="card model-manager" id="model-manager">
      <div className="model-manager__header">
        <h3 className="card__title">LLM Model</h3>
        <button
          className="model-manager__add-btn"
          onClick={() => { setShowForm(!showForm); setError(null); setTestResult(null); }}
          title="Mount new model"
        >
          {showForm ? '×' : '+'}
        </button>
      </div>

      {/* Active model badge */}
      {activeModel && !showForm && (
        <div className="model-badge model-badge--active">
          <span className="model-badge__dot" />
          <div className="model-badge__info">
            <span className="model-badge__name">{activeModel.name}</span>
            <span className="model-badge__meta">
              {activeModel.provider} / {activeModel.model_name}
            </span>
          </div>
        </div>
      )}

      {!activeModel && !showForm && models.length === 0 && (
        <p className="model-manager__empty">
          No models mounted. Click + to add one.
        </p>
      )}

      {/* Mount form */}
      {showForm && (
        <div className="model-mount-form">
          <div className="provider-selector">
            {PROVIDERS.map((p) => (
              <button
                key={p.id}
                className={`provider-selector__btn ${provider === p.id ? 'provider-selector__btn--active' : ''}`}
                onClick={() => handleProviderChange(p.id)}
              >
                <span className="provider-selector__label">{p.label}</span>
                <span className="provider-selector__desc">{p.desc}</span>
              </button>
            ))}
          </div>

          <div className="model-mount-form__fields">
            {provider !== 'ollama' && (
              <div className="model-mount-form__field">
                <label>API Key</label>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder={provider === 'openai' ? 'sk-...' : 'hf_...'}
                />
              </div>
            )}

            <div className="model-mount-form__field">
              <label>Base URL</label>
              <input
                type="text"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="Endpoint URL"
              />
            </div>

            <div className="model-mount-form__field">
              <label>Model Name</label>
              <input
                type="text"
                value={modelName}
                onChange={(e) => setModelName(e.target.value)}
                placeholder="e.g. gpt-4o, llama3, etc."
              />
            </div>

            <div className="model-mount-form__field">
              <label>Display Name <span className="model-mount-form__optional">(optional)</span></label>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="My GPT-4o"
              />
            </div>
          </div>

          {/* Test result */}
          {testResult && (
            <div className={`model-test-result ${testResult.healthy ? 'model-test-result--pass' : 'model-test-result--fail'}`}>
              <span className="model-test-result__icon">{testResult.healthy ? '✓' : '✗'}</span>
              <div>
                <div>{testResult.healthy ? 'Connection successful' : 'Connection failed'}</div>
                {testResult.validation_message && (
                  <div className="model-test-result__detail">{testResult.validation_message}</div>
                )}
                {testResult.capabilities && (
                  <div className="model-test-result__detail">
                    Context: {testResult.capabilities.context_window?.toLocaleString()} tokens
                    {' · '}Speed: {testResult.capabilities.estimated_speed}
                  </div>
                )}
              </div>
            </div>
          )}

          {error && (
            <div className="model-test-result model-test-result--fail">
              <span className="model-test-result__icon">✗</span>
              <div>{error}</div>
            </div>
          )}

          <div className="model-mount-form__actions">
            <button
              className="btn btn--secondary"
              onClick={handleTest}
              disabled={loading || !modelName}
            >
              {loading ? 'Testing...' : 'Test Connection'}
            </button>
            <button
              className="btn btn--primary"
              onClick={handleMount}
              disabled={loading || !modelName}
            >
              {loading ? 'Mounting...' : 'Mount Model'}
            </button>
          </div>
        </div>
      )}

      {/* Model list */}
      {!showForm && models.length > 0 && (
        <div className="model-list">
          {models.map((m) => (
            <div
              key={m.id}
              className={`model-list__item ${m.is_active ? 'model-list__item--active' : ''}`}
            >
              <div className="model-list__info">
                <span className="model-list__name">{m.name}</span>
                <span className="model-list__meta">{m.provider} / {m.model_name}</span>
              </div>
              <div className="model-list__actions">
                {!m.is_active && (
                  <button
                    className="model-list__btn model-list__btn--activate"
                    onClick={() => handleSetActive(m.id)}
                    title="Set as active"
                  >
                    Use
                  </button>
                )}
                <button
                  className="model-list__btn model-list__btn--delete"
                  onClick={() => handleDelete(m.id)}
                  title="Remove model"
                >
                  ×
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
