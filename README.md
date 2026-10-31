# 🧠 Context Bank
### A Portable, Trigger-Based Context Management System for AI

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Streamlit-Frontend-FF4B4B?logo=streamlit&logoColor=white" />
  <img src="https://img.shields.io/badge/PostgreSQL-Database-4169E1?logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/AI-Powered-purple" />
  <img src="https://img.shields.io/badge/Status-Development-orange" />
</p>

---

## 📌 Overview

**Context Bank** is a reusable, trigger-based context management system that allows users to store, organize, and retrieve project knowledge using custom trigger words.

Instead of repeatedly explaining previous conversations, project architectures, technical decisions, and development progress to AI models, users can save this information under memorable triggers.

For example:

```text
Trigger: VOXCENT

Stored Context:
- Project architecture
- Technology stack
- Development progress
- Technical decisions
- Pending tasks
```

Simply enter:

```text
Continue VOXCENT from where I stopped.
```

Context Bank resolves the trigger and generates a structured context package that can be provided to an AI model to continue the work.

**One trigger. One stored context. Seamless continuation.**

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🔑 Trigger-Based Retrieval | Retrieve stored contexts using unique trigger words. |
| 🧠 Context Management | Create, update, organize, and delete project contexts. |
| 🔍 Semantic Search | Search contexts using natural language and vector-based retrieval. |
| 👤 User Isolation | Separate user data using namespace-based ownership. |
| 📦 Context Packaging | Generate structured Markdown, JSON, and AI-ready prompts. |
| 🕒 Version History | Track changes, compare versions, and restore previous snapshots. |
| 🤖 AI Integration | Integrate Google Gemini for embeddings and summarization. |
| 🔌 MCP Integration | Connect Context Bank with compatible AI applications through MCP. |
| 🔐 Secure Authentication | JWT authentication, API keys, and password hashing. |
| 💾 Adaptive Storage | PostgreSQL with pgvector and lightweight local database support. |

---

## ⚙️ How It Works

```mermaid
flowchart TD
    A["User Input: VOXCENT"] --> B["Trigger Resolution"]
    B --> C["Context Bank"]
    C --> D["Retrieve Stored Context"]
    D --> E["Context Packager"]
    E --> F["Structured Context Package"]
    F --> G["AI Application / LLM"]
    G --> H["Continue Previous Work"]
```

### Example Workflow

**1. Store a context**

Create a context and assign a trigger word.

```text
Trigger: SQLPATH

Context:
SQL learning roadmap, completed topics,
practice progress and pending concepts.
```

**2. Retrieve a context**

```text
User: SQLPATH
```

**3. Resolve the trigger**

```text
SQLPATH → Context ID → Stored Context
```

**4. Generate an AI-ready package**

Context Bank retrieves the relevant information and formats it into a structured prompt.

**5. Continue working**

The generated package can be supplied to a compatible AI application to continue from the previous state.

---

## 🛠️ Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python 3.11+ |
| Frontend | Streamlit |
| Backend | FastAPI |
| API Server | Uvicorn |
| Database | PostgreSQL |
| Vector Database | pgvector |
| Local Database | SQLite |
| ORM | SQLAlchemy 2.0 |
| Database Migrations | Alembic |
| Data Validation | Pydantic v2 |
| Embeddings | TF-IDF / HashingVectorizer / Gemini |
| AI Summarization | Google Gemini API |
| Integration | REST API / MCP |
| Testing | Pytest |
| Containerization | Docker / Docker Compose |

---

## 🏗️ Project Architecture

```text
Context-Bank/
│
├── backend/
│   ├── api/
│   │   ├── auth.py
│   │   ├── contexts.py
│   │   ├── triggers.py
│   │   ├── search.py
│   │   ├── versions.py
│   │   └── integrations.py
│   │
│   ├── context_bank/
│   │   ├── trigger_registry.py
│   │   ├── storage.py
│   │   ├── retrieval.py
│   │   ├── context_packager.py
│   │   ├── versioning.py
│   │   └── permissions.py
│   │
│   ├── services/
│   ├── database/
│   ├── schemas/
│   ├── core/
│   └── integrations/
│
├── frontend/
│   ├── app.py
│   ├── pages/
│   └── components/
│
├── migrations/
├── tests/
├── scripts/
│
├── .env.example
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or later
- Git
- PostgreSQL (optional for local development)
- Docker (optional)

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/context-bank.git

cd context-bank
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it:

**Windows**

```bash
venv\Scripts\activate
```

**Linux / macOS**

```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
```

Configure the required environment variables in `.env`.

For PostgreSQL, configure:

```env
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/context_bank
```

SQLite is supported for local development.

### 5. Initialize the Database

```bash
python scripts/init_db.py
```

### 6. Start the Backend

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Backend API:

```text
http://127.0.0.1:8000
```

Interactive API Documentation:

```text
http://127.0.0.1:8000/docs
```

### 7. Start the Frontend

Open another terminal:

```bash
streamlit run frontend/app.py
```

Frontend:

```text
http://localhost:8501
```

---

## 🐳 Docker Deployment

Run the application using Docker Compose:

```bash
docker compose up --build
```

This starts:

- PostgreSQL with pgvector
- FastAPI backend
- Streamlit frontend

---

## 🧪 Running Tests

Execute the automated test suite:

```bash
python -m pytest tests -v
```

The tests cover:

- Trigger creation and normalization
- Duplicate trigger handling
- Context creation and retrieval
- User permission isolation
- Context versioning and restoration
- API validation and error handling
- Natural language context retrieval

---

## 🔌 AI & MCP Integration

Context Bank is designed to work with compatible external AI applications.

### REST API Integration

External applications can retrieve context packages through the REST API.

Example:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/contexts/retrieve-prompt" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "prompt": "Continue VOXCENT from where I stopped.",
    "detail_level": "summary_and_state",
    "output_format": "prompt"
  }'
```

### Model Context Protocol (MCP)

Context Bank provides an MCP server that exposes tools for compatible AI clients.

Available tools include:

- `resolve_trigger`
- `retrieve_context`
- `search_contexts`
- `list_contexts`
- `create_context`
- `update_context`

---

## 🔐 Security

Security and data isolation are important parts of Context Bank.

- JWT-based authentication.
- API key authentication.
- Password hashing using PBKDF2.
- Namespace-based user isolation.
- Ownership verification for context operations.
- Context data fencing to distinguish retrieved reference data from AI instructions.

---

## 🎯 Project Objectives

1. Reduce repetitive context sharing between AI conversations.
2. Provide a reusable memory management mechanism for AI workflows.
3. Enable structured project knowledge retrieval through trigger words.
4. Support integration with external AI applications.
5. Maintain context history and project continuity.

---

## 🔮 Future Enhancements

- Browser extensions for one-click context retrieval.
- More AI provider integrations.
- Cross-platform AI assistant integrations.
- Advanced context compression.
- Automated context synchronization.
- Improved conversational context extraction.

---

## 👨‍💻 Author

**Satya Sai Gollapalli**

B.Tech | Computer Science & Engineering (AI & ML)

Interested in Artificial Intelligence, Machine Learning, Backend Development, and building practical AI-powered applications.

---

<p align="center">
  ⭐ If you find this project interesting, consider giving it a star!
</p>

<p align="center">
  Built with ❤️ using Python and AI technologies.
</p>
