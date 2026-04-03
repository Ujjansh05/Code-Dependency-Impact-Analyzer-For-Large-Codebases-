# ⚡ Code Dependency Impact Analyzer

> **"If I change this file/function → what will break?"**

A full-stack tool that parses Python codebases, builds a dependency graph in TigerGraph, and uses LLaMA (via Ollama) to provide natural language impact analysis.

---

## 📦 Install via pip (Recommended)

```bash
pip install code-impact-analyzer
```

### Quick Start

```bash
# 1. Start TigerGraph + Ollama (requires Docker)
code-impact start

# 2. Analyze a Python project (full pipeline)
code-impact analyze ./myproject

# 3. Ask impact questions in plain English
code-impact query "What breaks if I change the login function?"

# 4. Check service health
code-impact status

# 5. Stop services when done
code-impact stop
```

### All CLI Commands

| Command | Description |
|---------|-------------|
| `code-impact start` | 🚀 Start TigerGraph + Ollama Docker containers |
| `code-impact stop` | 🛑 Stop containers (use `--volumes` to wipe data) |
| `code-impact status` | 📊 Health-check all services |
| `code-impact analyze ./path` | ⚡ Full pipeline: parse → graph → load → query |
| `code-impact parse ./path` | 📝 Parse only — emit CSVs (no Docker needed) |
| `code-impact query "..."` | 🔍 NL impact query against loaded graph |
| `code-impact serve` | 🌐 Start FastAPI backend on `:8000` |

### Inference Modes (Fast / Slow)

The analyzer now supports three LLM profiles:

- `fast` → lower latency, shorter explanations
- `balanced` → previous default-style behavior
- `slow` → higher context and better quality, slower output

CLI examples:

```bash
code-impact query "What breaks if I change login?" --mode fast
code-impact query "What breaks if I change login?" --mode slow
code-impact analyze ./myproject -q "Impact of auth.py" --mode balanced
```

API example:

```json
{
  "query": "What breaks if I change login?",
  "max_depth": 5,
  "inference_mode": "fast"
}
```

### Lightweight Mode (No Docker)

```bash
# Just parse and emit dependency CSVs — no TigerGraph needed
code-impact parse ./myproject
code-impact parse ./myproject --format json -o ./output
```

### Development Install

```bash
git clone https://github.com/Ujjansh05/Code-Dependency-Impact-Analyzer-For-Large-Codebases-.git
cd Code-Dependency-Impact-Analyzer-For-Large-Codebases-
pip install -e ".[dev]"
code-impact --help
```

---

## 🏗️ Architecture

```
┌──────────────┐     REST      ┌──────────────┐    pyTigerGraph   ┌──────────────┐
│   React +    │ ──────────▶  │   FastAPI     │ ───────────────▶ │  TigerGraph  │
│  vis-network │   :3000      │   Backend     │    :9000          │   (Docker)   │
└──────────────┘              │   :8000       │                   └──────────────┘
                              │               │    HTTP
                              │               │ ───────────────▶ ┌──────────────┐
                              └──────────────┘    :11434          │   Ollama     │
                                                                  │   (LLaMA)   │
                                                                  └──────────────┘
```

### Schema Diagram

```
  ┌──────────┐  CONTAINS   ┌──────────────┐
  │   File   │ ──────────▶ │   Function   │
  └──────────┘             └──────────────┘
       │                          │
       │ IMPORTS                  │ CALLS
       ▼                          ▼
  ┌──────────┐             ┌──────────────┐
  │   File   │             │   Function   │
  └──────────┘             └──────────────┘
```

---

## 📁 Project Structure

```
├── docker-compose.yml          # TigerGraph + FastAPI + Ollama
├── .env.example                # Environment variables template
├── requirements.txt            # Python dependencies
│
├── config/
│   ├── tigergraph.env          # TG host, port, credentials
│   └── llama.env               # Ollama URL, model name
│
├── parser/                     # Core AST parser engine
│   ├── ast_parser.py           # Extract funcs, calls, imports
│   ├── graph_builder.py        # Emit vertices.csv + edges.csv
│   └── utils.py                # File discovery, helpers
│
├── graph/                      # TigerGraph layer
│   ├── schema.gsql             # Vertex & edge definitions
│   ├── queries.gsql            # Impact traversal queries
│   ├── load_data.py            # Wait for TG, push CSVs
│   ├── tigergraph_client.py    # pyTigerGraph connection
│   └── wait_for_tg.py          # Health-check loop
│
├── llm/                        # LLaMA layer (via Ollama)
│   ├── llama_client.py         # Ollama HTTP client
│   ├── query_parser.py         # NL → function name
│   └── explainer.py            # Graph results → explanation
│
├── backend/                    # FastAPI backend
│   ├── Dockerfile
│   ├── main.py                 # App entry point
│   ├── models.py               # Pydantic schemas
│   └── routes/
│       ├── analyze.py          # POST /api/analyze
│       ├── upload.py           # POST /api/upload
│       └── graph.py            # GET /api/graph-data
│
├── frontend/                   # React frontend
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── index.css
│       ├── api/
│       │   └── client.js       # Axios → FastAPI
│       └── components/
│           ├── GraphCanvas.jsx  # vis-network graph viz
│           ├── QueryInput.jsx   # NL search bar
│           ├── ImpactPanel.jsx  # Results + AI explanation
│           └── FileUpload.jsx   # Upload codebase
│
└── data/
    ├── sample_code/            # Demo Python project
    ├── vertices.csv            # Parser output → TG load
    └── edges.csv
```

---

## 🚀 Quick Start

### Prerequisites

- **Docker** & **Docker Compose**
- **Node.js** ≥ 18 (for frontend dev)
- **Python** ≥ 3.11 (for local backend dev)

### 1. Clone & Configure

```bash
git clone https://github.com/your-repo/Code-Dependency-Impact-Analyzer.git
cd Code-Dependency-Impact-Analyzer
cp .env.example .env
```

### 2. Start All Services

```bash
docker-compose up -d
```

This starts:
| Service     | Port   | Description              |
|-------------|--------|--------------------------|
| TigerGraph  | 9000   | Graph database REST API  |
| TigerGraph  | 14240  | GraphStudio UI           |
| Backend     | 8000   | FastAPI + Swagger docs   |
| Ollama      | 11434  | LLaMA model server       |

### 3. Pull the LLM Model

```bash
docker exec -it ollama ollama pull qwen2.5-coder:14b
```

### 4. Start the Frontend (dev mode)

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000** in your browser.

### 5. Load the Sample Data

```bash
# Parse the sample code and load into TigerGraph
python -m parser.ast_parser      # → generates CSVs
python -m graph.load_data        # → loads into TG
```

---

## 🔌 API Endpoints

| Method | Endpoint          | Description                          |
|--------|-------------------|--------------------------------------|
| GET    | `/`               | Health check                         |
| GET    | `/health`         | Detailed health (API + Ollama)       |
| POST   | `/api/upload`     | Upload codebase (.zip)               |
| POST   | `/api/analyze`    | Run impact analysis (NL query)       |
| GET    | `/api/graph-data` | Get full graph for visualization     |
| GET    | `/docs`           | Swagger UI (auto-generated)          |

### Example: Analyze Impact

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "What happens if I change the authenticate function?"}'
```

---

## 🛠️ Development

### Backend (standalone)

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## 📝 License

MIT
