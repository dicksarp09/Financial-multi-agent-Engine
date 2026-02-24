# Financial Agent - Multi-Agent Financial Decision System

A comprehensive multi-agent financial decision system built with LangGraph (Groq LLM), featuring a React/Next.js frontend with dark fintech design and a FastAPI backend.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                           │
│  Dashboard • Upload • Execution • Report • History • Settings    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                              │
│  Sessions • Workflow • Approval • Reports • Conversation         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Python Agent Core                            │
│  Orchestrator • Agents • Security • Memory • Reliability          │
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
.
├── backend/                     # FastAPI backend
│   ├── main.py                # API endpoints
│   └── pyproject.toml         # Dependencies
│
├── frontend/                   # Next.js frontend
│   ├── app/
│   │   ├── layout.tsx        # Root layout
│   │   ├── page.tsx          # Main router
│   │   └── globals.css       # Dark fintech styles
│   ├── components/
│   │   ├── Navigation.tsx    # Top navigation
│   │   ├── Dashboard.tsx      # Dashboard screen
│   │   ├── UploadSession.tsx  # CSV upload
│   │   ├── ExecutionView.tsx   # Live workflow
│   │   ├── ReportScreen.tsx   # Report with charts
│   │   ├── SessionHistory.tsx # History table
│   │   └── SettingsScreen.tsx # Settings
│   ├── store/
│   │   └── index.ts          # Zustand state
│   └── lib/
│       ├── types.ts           # TypeScript types
│       └── api.ts             # API client
│
├── orchestrator.py            # Main supervisor
├── logging_system.py          # SQLite logging
├── schemas.py                 # Pydantic models
│
├── compute/                   # Deterministic modules
├── agents/                    # Agent implementations
├── security/                  # Security layer
├── memory/                    # Memory management
├── reliability/              # Reliability patterns
└── observability/             # Monitoring
```

## Quick Start

### 1. Start the Backend

```bash
cd backend
pip install -r requirements.txt  # or uv pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 2. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

### 3. Open Browser

Navigate to http://localhost:3000

## Features

### Frontend Screens

| Screen | Description |
|--------|-------------|
| **Dashboard** | Recent sessions, system status, quick actions |
| **Upload** | Drag-drop CSV with validation preview |
| **Execution** | Live workflow timeline, agent logs |
| **Report** | Summary, categories, anomalies, budget, trace |
| **History** | Session versions with revert option |
| **Settings** | Thresholds, LLM config, token limits |

### Backend API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/sessions` | GET | List all sessions |
| `/api/sessions` | POST | Create new session |
| `/api/upload/validate` | POST | Validate CSV file |
| `/api/workflow/{id}` | GET | Get workflow state |
| `/api/workflow/{id}/execute` | POST | Start execution |
| `/api/workflow/{id}/logs` | GET | Get execution logs |
| `/api/approvals/{id}` | GET | Get pending approval |
| `/api/approvals/{id}/respond` | POST | Approve/reject |
| `/api/reports/{id}` | GET | Get report data |
| `/api/reports/{id}/refine` | POST | Refine report |
| `/api/reports/{id}/export` | GET | Export (JSON/CSV) |
| `/api/conversation/{id}` | POST | Chat message |
| `/api/system/status` | GET | System status |
| `/api/system/settings` | GET/PUT | Settings |

## Design System

### Colors

- **Background**: `#0a0f1a` (dark), `#050810` (darker)
- **Card**: `#0d1424` with glass effect
- **Primary**: `#10b981` (emerald green)
- **Accent**: `#34d399` (light emerald)

### Typography

- **Headings**: Inter, system-ui
- **Numbers**: JetBrains Mono (tabular-nums)

### Effects

- Glass cards with backdrop blur
- Emerald glow shadows
- Smooth animations (fade, slide, scale)
- Pulsing status indicators

## Configuration

### Backend Environment

```bash
# Optional: Set Groq API key
export GROQ_API_KEY=your_key_here
```

### Frontend API Base

The frontend connects to `http://localhost:8000/api` by default. Update in `frontend/lib/api.ts` for production.

## Development

```bash
# Backend
cd backend
uvicorn main:app --reload

# Frontend
cd frontend
npm run dev

# Both
# Terminal 1: backend
# Terminal 2: frontend
```

## Demo Flow

1. **Dashboard** - View existing sessions
2. **Upload** - Drag CSV file, validate, preview
3. **Execute** - Watch workflow progress in real-time
4. **Approval** - Handle anomaly alerts
5. **Report** - View charts, export data
6. **Refine** - Conversational budget adjustments
