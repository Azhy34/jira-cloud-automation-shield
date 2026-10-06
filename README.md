# 🛡️ Jira Cloud REST API v3 Integration & Two-Layer Shield

[![CI - Tests](https://github.com/Azhy34/jira-cloud-automation-shield/actions/workflows/ci.yml/badge.svg)](https://github.com/Azhy34/jira-cloud-automation-shield/actions)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2.5-brightgreen.svg)](https://docs.pydantic.dev/)
[![FastMCP](https://img.shields.io/badge/Model%20Context%20Protocol-FastMCP%20Server-8A2BE2.svg)](https://modelcontextprotocol.io/)
[![Jira API](https://img.shields.io/badge/Atlassian-Jira%20Cloud%20REST%20v3-0052CC.svg)](https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/)
[![Security](https://img.shields.io/badge/Security-Zero--Leak%20Vault-red.svg)](#security--zero-leak-guarantees)

Production-grade integration gateway, Model Context Protocol (MCP) server, automated contract discovery suite, and interactive IDE Kanban controller for **Atlassian Jira Cloud REST API v3**, architected for autonomous AI agents and enterprise engineering teams.

---

## 🏛️ System Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        Autonomous AI Agent                             │
│                 (Google ADK / Claude / Cursor / IDE)                   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Model Context Protocol (FastMCP)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│              FastMCP Gateway (`mcp_server/jira_mcp.py`)                │
│    • search_jira_issues    • create_jira_issue    • move_jira_issue    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│           Two-Layer Pydantic Error Shield (`shields/jira_shield.py`)   │
│    • Strict Contract Validation        • Normalized statusCategory     │
│    • Resilient Error Fallback          • Zero Hallucination Guarantee  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│              Resilient Jira Client (`client/jira_client.py`)           │
│    • Modern `/rest/api/3/search/jql` Protocol (Zero 410 Errors)        │
│    • Atlassian Document Format (ADF) Payload Engine                    │
│    • Basic Auth Header Scrubber (Zero-Leak Memory Vault)               │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTPS (TLS 1.3)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                 Atlassian Jira Cloud Platform                          │
│               (`https://*.atlassian.net`)                              │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🔍 Key Engineering Highlights & Breaking Change Discovery

During automated endpoint probing, this project proactively identified and mitigated a critical Atlassian breaking change:
* ⚠️ **Legacy Endpoint:** `GET /rest/api/3/search` was deprecated by Atlassian and returned **HTTP 410 Gone** (`CHANGE-2046`).
* 🛡️ **Seamless Migration:** The client immediately migrated to **`GET /rest/api/3/search/jql`** with explicit field projection masks (`fields: summary,status,issuetype,parent`), ensuring zero production downtime.

### SLA & Latency Benchmark Results
| Endpoint | Method | Latency | Status | Purpose |
|---|---|---|---|---|
| `/rest/api/3/myself` | `GET` | **455 ms** | `200 OK` | Identity handshake & permissions |
| `/rest/api/3/project` | `GET` | **347 ms** | `200 OK` | Workspace project enumeration |
| `/rest/api/3/project/{key}` | `GET` | **387 ms** | `200 OK` | Issue type metadata retrieval |
| `/rest/api/3/search/jql` | `GET` | **467 ms** | `200 OK` | JQL query execution with field masks |
| `/rest/api/3/issue` | `POST` | **1289 ms** | `201 Created` | ADF mutation testing (Issue creation) |

---

## 📋 Jira Work Breakdown Structure (WBS)

The integration was structured into a master Epic and atomic child phases directly deployed to the live **Jira Software Kanban Board (`KAN`)**:

```text
[ MASTER EPIC: KAN-1 ]
"[INT-CORE] Jira Cloud REST API v3 Integration & Automated Contract Discovery"
  ├── [KAN-2] [INT-101] Security & Identity Setup (Zero-Leak Credentials Vault)  [DONE]
  ├── [KAN-3] [INT-102] Postman MCP Workspace & Environment Orchestration       [DONE]
  ├── [KAN-4] [INT-103] API Probing & Breaking Changes Detection (/search/jql)    [DONE]
  ├── [KAN-9] [INT-106] Structured Runtime Observability & In-Issue Audit Tracing [DONE]
  ├── [KAN-5] [INT-104] Mutation Testing: End-to-End Issue Lifecycle Creation    [TO DO]
  ├── [KAN-6] [INT-105] Machine-Readable Audit Report & Handoff                 [TO DO]
  ├── [KAN-7] [AI-101]  Slack Bot Gateway & Ingestion Service                   [TO DO]
  └── [KAN-8] [AI-102]  Data Connectors & Enterprise RAG Pipeline               [TO DO]
```

---

## 🤖 Model Context Protocol (FastMCP) for AI Agents

Run the bundled FastMCP server to grant autonomous AI agents tool access to your Jira board:

```bash
python mcp_server/jira_mcp.py
```

### Registered Agent Tools:
1. `search_jira_issues(jql, max_results)` — Query board state via JQL.
2. `create_jira_issue(summary, description, project_key, issue_type, parent_key)` — Create work items with rich text ADF descriptions.
3. `move_jira_issue_status(issue_key, target_status)` — Transition issues across Kanban columns (*To Do*, *In Progress*, *Done*).

### 🧩 Extensibility Architecture: "What If an Operation is Missing?"

A critical architectural consideration for enterprise AI engineering: *Why expose 3 atomic tools instead of wrapping all 500+ Atlassian REST endpoints?*  
This design intentionally follows the **Principle of Least Privilege (PoLP)** and modular extensibility:

| Enterprise Scenario | Architectural Mechanism | How It Works in Production |
|---|---|---|
| **1. Complex or Niche Queries** | **Universal JQL Expressiveness** | Instead of polluting LLM context with dozens of rigid tools (`find_by_assignee`, `find_overdue`), the single `search_jira_issues` tool accepts full Jira Query Language. The LLM dynamically constructs compound filters (e.g., `issuetype = Bug AND created >= -7d AND assignee is EMPTY`). |
| **2. New Domain Workflows** | **60-Second FastMCP Extension Pattern** | Adding any new API operation (e.g., `assign_issue`, `add_attachment`) requires only 5 lines of Python with `@mcp.tool()`, inheriting automatic Pydantic validation and `JiraTracer` logging. |
| **3. Destructive / Admin Operations** | **Least Privilege & Human Escalation** | High-blast-radius operations (`delete_project`, `modify_billing`) are intentionally excluded from the agent toolset. When requested, the agent gracefully escalates to a human with direct Atlassian deep-links rather than hallucinating or executing destructive mutations. |


---

## 🚀 Quickstart & Interactive IDE Controller

### 1. Prerequisites & Installation
```bash
git clone https://github.com/Azhy34/jira-cloud-automation-shield.git
cd jira-cloud-automation-shield
pip install -r requirements.txt
```

### 2. Configure Environment (Zero-Leak)
```bash
cp .env.example .env
# Edit .env with your JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN, and JIRA_PROJECT_KEY
```

### 3. Run Automated Tests
```bash
pytest tests/ -v
```

### 4. Inspect Live Board from Terminal
```bash
python controller/jira_board_cli.py
```

### 5. Move Work Items Between Columns
```bash
# Move task to In Progress
python controller/jira_board_cli.py move KAN-5 "In Progress"

# Complete task
python controller/jira_board_cli.py move KAN-4 "Done"
```

---

## 🔒 Security & Zero-Leak Guarantees

* **Credential Isolation:** Strict `.gitignore` rules prevent `.env` or `.env.*` files from ever entering source control.
* **Header Scrubbing:** Basic Auth hashes are synthesized in-memory and never dumped to console or logging sinks.
* **Auditability:** Machine-readable probe reports (`discovery/jira_api_discovery_report.json`) record latency and response structures without leaking API tokens.

---

## 📄 License
MIT License. Created by [Mikhail Azhyshchev](https://github.com/Azhy34).
