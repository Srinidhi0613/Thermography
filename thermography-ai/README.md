# 🔥 Thermography Compliance AI

**Enterprise-grade Industrial Thermography Monitoring Platform**

A full-stack AI-powered platform for electrical maintenance, thermographic inspections, predictive maintenance, and compliance monitoring. Built with FastAPI, MongoDB Atlas, Ollama (Llama 3), MCP tools, and a premium dark glassmorphism UI.

---

## 📸 Features

| Feature | Description |
|---|---|
| **Dashboard** | KPI cards, severity distribution, compliance gauge, live alerts |
| **Inspections** | Full inspection history with filters, pagination, compliance scores |
| **Equipment Registry** | 8 monitored assets with health scores and inspection history |
| **Critical Alerts** | Real-time critical/serious alerts with one-click report download |
| **Thermal Upload** | Upload IR images → OpenCV hotspot detection → Delta-T classification |
| **PDF Reports** | Auto-generated compliance reports per NFPA 70B |
| **AI Assistant** | Streaming chat powered by Llama 3 + MCP tools + MongoDB live data |
| **MCP Tools** | 6 tools: dashboard stats, inspection history, critical alerts, equipment details, temperature analysis, compliance status |

---

## 🏗️ Architecture

```
thermography-ai/
├── backend/
│   ├── main.py                  # FastAPI app, lifespan, routing
│   ├── database.py              # MongoDB Atlas connection + seed data
│   ├── routers/
│   │   ├── dashboard.py         # Dashboard stats, trends, alerts APIs
│   │   ├── inspections.py       # Inspection CRUD + history
│   │   ├── equipment.py         # Equipment registry + health scores
│   │   ├── reports.py           # Report generation
│   │   ├── uploads.py           # Thermal image upload + OpenCV analysis
│   │   └── ai_assistant.py      # Ollama streaming + MCP orchestration
│   └── mcp/
│       └── tools.py             # 6 MCP tools with MongoDB queries
├── frontend/
│   ├── templates/
│   │   └── index.html           # Single-page dashboard
│   └── static/
│       ├── css/main.css         # Dark glassmorphism theme
│       └── js/app.js            # Full SPA logic
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Quick Start

### 1. Clone / Extract

```bash
cd thermography-ai
```

### 2. Create Python virtual environment

```bash
python3 -m venv venv
source venv/bin/activate        # Linux/Mac
# or
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env with your MongoDB Atlas URL (or leave localhost for local MongoDB)
```

### 5. Install and start Ollama (for AI features)

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama server
ollama serve

taskkill /IM "ollama app.exe" /F
taskkill /IM ollama.exe /F

# Pull Llama 3 model (in a new terminal)
ollama pull llama3
```

> **Note:** The platform works without Ollama — AI responses fall back to built-in engineering knowledge. Full streaming AI requires Ollama running locally.

### 6. (Optional) MongoDB Atlas

For production use, update `.env` with your Atlas connection string:
```
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net
```

The app automatically seeds 300+ demo inspections and 8 equipment records on first run.

### 7. Start the server

```bash
cd backend
python main.py
```

Open **http://localhost:8000** in your browser.

---

## 🧠 AI Assistant — How It Works

```
User Question
     ↓
Keyword Detection (detect_required_tool)
     ↓
MCP Tool Execution (if platform question)
     ↓
MongoDB Query → Structured Result
     ↓
Augmented Prompt → Ollama Llama 3
     ↓
Streaming Response → Frontend SSE
```

### MCP Tools Available

| Tool | Trigger Keywords | Data Source |
|---|---|---|
| `get_dashboard_stats` | dashboard, stats, total inspections | MongoDB aggregation |
| `get_inspection_history` | recent inspections, history, findings | MongoDB find |
| `get_critical_alerts` | critical alerts, urgent, immediate | MongoDB filter |
| `get_equipment_details` | equipment, transformer, motor | MongoDB lookup |
| `analyze_temperatures` | delta-t, temperature °C | Local calculation |
| `get_compliance_status` | compliance, score, NFPA | MongoDB aggregation |

---

## 🌡️ Thermal Analysis — Severity Classification

Per **NFPA 70B-2023** and **ISO 18434-1:2008**:

| Delta-T (°C) | Severity | Action | Timeframe |
|---|---|---|---|
| ≥ 40°C | **Critical** | Immediate shutdown | Now |
| 25–39°C | **Serious** | Schedule repair | Within 72 hours |
| 10–24°C | **Moderate** | Plan maintenance | Within 30 days |
| 3–9°C | **Minor** | Document & monitor | Next PM window |
| < 3°C | **Normal** | No action | Continue monitoring |

---

## 🔌 API Endpoints

### Dashboard
- `GET /api/dashboard/stats` — KPIs, severity breakdown
- `GET /api/dashboard/recent-alerts` — Latest critical/serious alerts
- `GET /api/dashboard/trends` — 30-day inspection trend

### Inspections
- `GET /api/inspections/` — Paginated inspection list (filterable)
- `GET /api/inspections/critical` — Critical & serious findings
- `GET /api/inspections/history?days=30` — History with breakdown
- `GET /api/inspections/{id}` — Single inspection detail

### Equipment
- `GET /api/equipment/` — All monitored equipment
- `GET /api/equipment/{id}` — Equipment detail + recent inspections
- `GET /api/equipment/{id}/stats` — Equipment statistics

### Uploads
- `POST /api/uploads/thermal-image` — Upload + analyze thermal image

### Reports
- `GET /api/reports/generate/{id}` — Download inspection report
- `GET /api/reports/summary` — Platform report summary

### AI Assistant
- `POST /api/ai/chat/stream` — SSE streaming chat with MCP
- `GET /api/ai/status` — Ollama connection status
- `GET /api/ai/tools` — List available MCP tools

---

## 🛡️ Standards & Compliance

- **NFPA 70B-2023** — Recommended Practice for Electrical Equipment Maintenance
- **IEC 60076** — Power transformer standards
- **ISO 18434-1:2008** — Condition monitoring via thermography
- **NETA MTS** — Maintenance Testing Specifications
- **NFPA 70E** — Electrical safety in the workplace

---

## 🔧 Customization

### Add Equipment
Edit `EQUIPMENT_LIST` in `backend/database.py`

### Add MCP Tools
Add tool definition to `MCP_TOOLS` in `backend/mcp/tools.py` and implement the handler in `execute_tool()`

### Change AI Model
Update `MODEL_NAME` in `backend/routers/ai_assistant.py` (any Ollama-compatible model)

### Connect Different Database
Update `MONGODB_URL` in `.env` — supports any MongoDB-compatible URI

---

## 📦 Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.11+) |
| Database | MongoDB Atlas (Motor async driver) |
| AI/LLM | Ollama + Llama 3 (local, no API keys) |
| AI Protocol | MCP (Model Context Protocol) tools |
| Image Analysis | OpenCV + NumPy |
| Frontend | Vanilla HTML/CSS/JS (no framework) |
| Streaming | Server-Sent Events (SSE) |
| Theme | Dark Glassmorphism |

---

## 📄 License

MIT License — Free for commercial and personal use.

---

*Built for industrial reliability engineers, electrical maintenance teams, and predictive maintenance professionals.*
