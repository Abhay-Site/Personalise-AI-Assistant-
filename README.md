# ORBIT 180: An Observable, Memory-Augmented Productivity Agent

> **A Unified Natural Language Interface for Cross-Application Workflows**  
> *One AI Agent. Every App. Every Task.*

---

## 🎯 Project Overview

ORBIT 180 is an observable, memory-augmented productivity agent designed for students and professionals. It provides a single natural-language conversational interface that coordinates actions across **Gmail**, **Google Calendar**, and **Google Drive**.

Instead of switching between disconnected apps, ORBIT 180:
1. **Decomposes natural language requests** into sequential, multi-step action plans.
2. **Maintains persistent user memory** (study hours, meeting preferences, rules).
3. **Chains parameters dynamically** across services (e.g. finds meeting attendees on Calendar, locates documents on Drive, and prepares Gmail drafts automatically).
4. **Enforces Human-in-the-Loop (HITL) safety** — sensitive actions (sending emails, deleting events) are paused before execution until explicitly approved.
5. **Provides glass-box observability** through live execution traces and sanitized audit logging.
6. **Features proactive intelligence** with a Daily Morning Briefing, Schedule Conflict Auditor, and Privacy Shield.

---

## 🏗️ Architecture

```mermaid
flowchart TD
    User([User / Browser]) <--> NextUI[Next.js 15 Frontend<br/>(Dashboard, Chat, Workflows, Memory, Audit)]
    NextUI <--> FastAPIServer[FastAPI Backend Server<br/>(Port 8000)]
    
    subgraph Core Agent Pipeline
        FastAPIServer --> Orchestrator[Agent Orchestrator]
        Orchestrator --> MemorySvc[Memory Service]
        Orchestrator --> Planner[Action Planner]
        Orchestrator --> PrivacyShield[Privacy Shield<br/>(PII & Secret Redaction)]
        PrivacyShield --> GeminiLLM[Google Gemini 1.5 Flash]
        Orchestrator --> WorkflowCtx[Workflow Parameter Chaining]
    end

    subgraph Security & Tools
        WorkflowCtx --> ToolRegistry[Tool Execution Engine]
        ToolRegistry --> ReadOps[Safe Read Tools<br/>Auto-Executed]
        ToolRegistry --> SensitiveOps[Sensitive Tools<br/>PAUSED for Approval]
        SensitiveOps --> HITL[Human Approval Modal]
        HITL --> ApprovedExec[Execute Approved Action]
        ApprovedExec --> AuditLog[Sanitized Audit Trail]
    end

    subgraph External Connectors
        ToolRegistry <--> GmailTool[Gmail Service]
        ToolRegistry <--> CalendarTool[Calendar Service]
        ToolRegistry <--> DriveTool[Drive Service]
        GmailTool <--> GoogleOAuth[Google OAuth 2.0 / Demo Provider]
        CalendarTool <--> GoogleOAuth
        DriveTool <--> GoogleOAuth
    end
```

---

## 🚀 Quickstart Guide

### Prerequisites
- **Python 3.11+** (Python 3.14 fully supported)
- **Node.js 18+** & npm

---

### 1. Backend Setup
```powershell
cd D:\orbit180\backend

# Activate virtual environment
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run all 36 automated unit & integration tests
python -m pytest tests/ -v

# Start backend server
uvicorn app.main:app --reload --port 8000
```
*API documentation will be live at: **http://localhost:8000/docs***

---

### 2. Frontend Setup
```powershell
cd D:\orbit180\frontend

# Install dependencies & run development server
npm run dev
```
*Frontend UI will be live at: **http://localhost:3000***

---

## 🔑 Configuration (`backend/.env`)

| Variable | Description | Default / Mode |
|---|---|---|
| `GEMINI_API_KEY` | Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/apikey) | Optional (Uses local agent synthesizer if blank) |
| `GEMINI_MODEL` | Gemini model name | `gemini-1.5-flash` |
| `GOOGLE_CLIENT_ID` | Google Cloud OAuth Client ID | Optional (Uses high-fidelity Demo Provider if blank) |
| `GOOGLE_CLIENT_SECRET` | Google Cloud OAuth Client Secret | Optional (Uses high-fidelity Demo Provider if blank) |
| `DATABASE_URL` | SQLite database URI | `sqlite:///./orbit180.db` |
| `FRONTEND_URL` | CORS authorized frontend origin | `http://localhost:3000` |

---

## 🧪 Comprehensive Verification Suite (36/36 Tests)

ORBIT 180 includes automated test coverage across all layers:

```powershell
pytest tests/ -v
```

1. **System & Health** (`test_health.py`): Endpoint status, CORS, JSON structure.
2. **Database & Persistence** (`test_db.py`): User lifecycle, memory CRUD, preference toggling.
3. **AI Pipeline & Traces** (`test_chat.py`): Intent classification, glass-box trace generation, conversation history.
4. **HITL Approvals** (`test_approvals.py`): Security boundary enforcement, approve-to-execute, reject-to-abort.
5. **Google Integration** (`test_google_integration.py`): Dual-mode Gmail, Calendar, Drive connectors, OAuth flow.
6. **Cross-App Chaining** (`test_workflows.py`): Dynamic parameter extraction (Calendar attendees ➔ Drive report ➔ Gmail draft).
7. **Safety & Audit** (`test_safety_audit.py`): Regex secret sanitization, parameter-edited approvals, multi-criteria audit search.
8. **Differentiation** (`test_differentiation.py`): Privacy Shield PII redaction (phones, cards, passwords), Conflict Auditor, Morning Briefing API.
9. **Master End-to-End Demo** (`test_master_demo.py`): Complete journey from briefing to multi-app execution and approved dispatch.

---

## 🌟 Primary Demo Scenario

Try this prompt in the Chat interface:

> *"Find tomorrow's project review meeting, locate the latest ORBIT 180 report, and prepare an email for the participants"*

**What happens:**
1. **Decomposes** into a 4-step Action Plan (`calendar` ➔ `drive` ➔ `gmail` ➔ `gmail`).
2. **Calendar tool** finds the meeting and extracts attendee email addresses.
3. **Drive tool** locates `ORBIT_180_Project_Report_Final.pdf`.
4. **Gmail tool** prepares an email draft addressed to the calendar attendees with the report link attached.
5. **Security Pause**: The agent pauses before sending, flagging `requires_approval = True`.
6. **Human-in-the-Loop Dialog**: The user inspects the draft, optionally edits parameters, and clicks **Approve**.
7. **Execution**: The email is dispatched, an execution trace is displayed, and an immutable, sanitized audit record is written.
