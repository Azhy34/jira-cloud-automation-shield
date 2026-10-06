# 🛡️ Jira Cloud REST API v3 Integration & Two-Layer Shield

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2.5-brightgreen.svg)](https://docs.pydantic.dev/)
[![Jira API](https://img.shields.io/badge/Atlassian-Jira%20Cloud%20REST%20v3-0052CC.svg)](https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/)
[![Postman MCP](https://img.shields.io/badge/Postman-MCP%20Orchestrated-FF6C37.svg)](https://www.postman.com/)
[![Security](https://img.shields.io/badge/Security-Zero--Leak%20Vault-red.svg)](#security--zero-leak-guarantees)

Production-grade integration gateway, automated contract discovery suite, and interactive IDE Kanban controller for **Atlassian Jira Cloud REST API v3**, architected for autonomous AI agents and enterprise engineering teams.

---

## 🏛️ System Architecture

```text
[ Developer / AI Agent in IDE ]
           │
           ├── 1. Proactive Contract Discovery & Probing (Postman MCP)
           ▼
[ Two-Layer Pydantic Error Shield (`shields/jira_shield.py`) ]
           │  ├── Strict Schema Validation (JiraIssue, JiraSearchResponse)
           │  └── Resilient Error Fallback (Zero Hallucination)
           ▼
[ Resilient Jira Cloud Client (`client/jira_client.py`) ]
           │  ├── Modern `/rest/api/3/search/jql` Protocol
           │  ├── Atlassian Document Format (ADF) Payload Engine
           │  └── Board Transition Controller (To Do ➔ In Progress ➔ Done)
           ▼
[ Atlassian Jira Cloud Platform (`https://*.atlassian.net`) ]
```

---

## 🔍 Key Engineering Highlights & Breaking Change Discovery

During automated endpoint probing, this project proactively identified and mitigated a major Atlassian breaking change:
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
  ├── [KAN-4] [INT-103] API Probing & Breaking Changes Detection (/search/jql)    [IN PROGRESS]
  ├── [KAN-5] [INT-104] Mutation Testing: End-to-End Issue Lifecycle Creation    [TO DO]
  ├── [KAN-6] [INT-105] Machine-Readable Audit Report & Handoff                 [TO DO]
  ├── [KAN-7] [AI-101]  Slack Bot Gateway & Ingestion Service                   [TO DO]
  └── [KAN-8] [AI-102]  Data Connectors & Enterprise RAG Pipeline               [TO DO]
```

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

### 3. Inspect Live Board from Terminal
```bash
python controller/jira_board_cli.py
```
*Output:*
```text
=================================================================
📊 LIVE JIRA KANBAN BOARD CONTROLLER (Project: KAN)
=================================================================

📌 COLUMN: [TO DO] (5 items)
   • [KAN-1] (Эпик) [INT-CORE] Jira Cloud REST API v3 Integration...
   • [KAN-5] (Задача) [INT-104] Mutation Testing: End-to-End Issue Lifecycle Creation
   • [KAN-6] (Задача) [INT-105] Machine-Readable Audit Report & Handoff
   ...

📌 COLUMN: [IN PROGRESS] (1 items)
   • [KAN-4] (Задача) [INT-103] API Probing & Breaking Changes Detection (/search/jql)

📌 COLUMN: [DONE] (2 items)
   • [KAN-2] (Задача) [INT-101] Security & Identity Setup (Zero-Leak Credentials Vault)
   • [KAN-3] (Задача) [INT-102] Postman MCP Workspace & Environment Orchestration
```

### 4. Move Work Items Between Columns
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
