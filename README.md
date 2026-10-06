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
"[INT-CORE] Jira Cloud REST API v3 Integration & Automated Contract Discovery" [DONE]
  ├── [KAN-10] [INT-100] Step 0: Atlassian Jira Fundamentals Certification          [DONE]
  ├── [KAN-2]  [INT-101] Step 1: Security & Identity Setup (Zero-Leak Vault)        [DONE]
  ├── [KAN-3]  [INT-102] Step 2: Postman MCP & Jira Endpoints Discovery              [DONE]
  ├── [KAN-4]  [INT-103] Step 3: API Probing & Breaking Changes Detection (/search) [DONE]
  ├── [KAN-5]  [INT-104] Step 4: Mutation Testing: End-to-End Issue Lifecycle       [DONE]
  ├── [KAN-6]  [INT-105] Step 5: Machine-Readable Audit Report & Contract Handoff    [DONE]
  ├── [KAN-12] [INT-106] Step 6: Two-Layer Pydantic Error Shield & FastMCP Gateway   [DONE]
  ├── [KAN-9]  [INT-107] Step 7: Structured Runtime Observability & In-Issue Tracing [DONE]
  ├── [KAN-11] [INT-108] Step 8: Public GitHub Repository, Test Suite & CI Pipeline    [DONE]
  └── [KAN-13] [INT-109] Step 9: Architectural Hardening & Official Skills Remediation [DONE]
```

> 💡 **Step 0 Prerequisite (`KAN-10`):** Completed official Atlassian Learning Path [Get the Most Out of Jira](https://community.atlassian.com/learning/path/get-the-most-out-of-jira) prior to building custom automation, ensuring deep domain understanding of Jira issue types, Kanban workflows, timeline views, and JQL syntax before diving into REST API development.

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
4. `check_duplicate_issues(summary, project_key)` — Pre-creation triage tool preventing duplicate tickets via JQL similarity matching.
5. `get_required_fields_meta(project_key, issue_type)` — Introspects required enterprise custom fields (`createmeta`) to prevent 400 Bad Request errors.
6. `link_jira_issues(inward_key, outward_key, link_type)` — Establishes semantic dependency links (`Blocks`, `Relates`, `Duplicate`).

---

## 🧠 Production Agent Skills (Atlassian Open Standard)

This repository bundles ready-to-run Agent Skills (`SKILL.md`) following the official [Agent Skills](https://agent-plugins.org/) standard and Atlassian Rovo best practices:

* 🛡️ **[`skills/jira-triage-guard/SKILL.md`](skills/jira-triage-guard/SKILL.md)**: Production triage workflow enforcing *Extract ➔ Search ➔ Analyze ➔ Act*. Intercepts issue creation, searches recent open/resolved tickets, and prevents duplicate backlog pollution.
* 📋 **[`skills/jira-spec-to-backlog/SKILL.md`](skills/jira-spec-to-backlog/SKILL.md)**: Automatically transforms unstructured PRDs and specifications into structured Epics, atomic child tasks with Acceptance Criteria checklists, and dependency issueLinks.

### 🧩 Extensibility Architecture: "Why Expose Atomic Tools Instead of 500+ Endpoints?"

A critical architectural consideration for enterprise AI engineering: *Why expose focused atomic tools instead of blindly wrapping all 500+ Atlassian REST endpoints?*  
This design intentionally follows the **Principle of Least Privilege (PoLP)**, modular extensibility, and the **4-Tier Operational Risk Hierarchy**:

| Enterprise Scenario | Architectural Mechanism | How It Works in Production |
|---|---|---|
| **1. Complex or Niche Queries** | **Universal JQL Expressiveness** | Instead of polluting LLM context with dozens of rigid tools (`find_by_assignee`, `find_overdue`), the single `search_jira_issues` tool accepts full Jira Query Language. The LLM dynamically constructs compound filters (e.g., `issuetype = Bug AND created >= -7d AND assignee is EMPTY`). |
| **2. New Domain Workflows** | **60-Second FastMCP Extension Pattern** | Adding any new API operation (e.g., `assign_issue`, `add_attachment`) requires only 5 lines of Python with `@mcp.tool()`, inheriting automatic Pydantic validation and `JiraTracer` logging. |
| **3. Destructive / Admin Operations** | **Least Privilege & Human Escalation** | High-blast-radius operations (`delete_project`, `modify_billing`) are intentionally excluded from the agent toolset. When requested, the agent gracefully escalates to a human with direct Atlassian deep-links rather than hallucinating or executing destructive mutations. |

---

## 🏛️ Enterprise 4-Tier Operational Risk & Endpoint Taxonomy

Official Atlassian documentation describes 500+ endpoints purely from a technical syntax standpoint, but **remains silent on business risk, agent blast radius, and compliance boundaries**. 

To prevent autonomous AI agents from polluting backlogs, wiping compliance logs, or compromising tenant governance, this architecture categorizes Jira Cloud endpoints into **4 Operational Risk Tiers** (full technical specification in [**`docs/ENTERPRISE_API_TIER_TAXONOMY.md`**](docs/ENTERPRISE_API_TIER_TAXONOMY.md)):

```text
                                  ▲
                                 / \
                                / T4 \      TIER 4: Hard Blacklist (Admin & Security)
                               /------\     Blast Radius: Catastrophic | Access: FORBIDDEN
                              /  T3    \    TIER 3: Human-in-the-Loop (Destructive & Bulk)
                             /----------\   Blast Radius: High | Access: Approval Required
                            /    T2      \  TIER 2: Guarded Mutations (Single Items & Triage)
                           /--------------\ Blast Radius: Bounded | Access: Pre-Flight Shields
                          /      T1        \TIER 1: Read & Discovery (Queries & Metadata)
                         /──────────────────\Blast Radius: Zero | Access: Fully Autonomous
```

| Operational Tier | Representative Endpoints | Blast Radius | Agent Autonomy & Governance |
|---|---|---|---|
| **🟢 Tier 1: Read & Discovery** | `GET /myself`, `GET /project`, `POST /search/jql`, `GET /createmeta`, `GET /transitions`, `GET /field` | **Zero** (Idempotent query) | **100% Autonomous (`Mode.AUTO` / `Mode.ANY`)**. Enforces projection masks (`fields: ...`) and client-side metadata caching. |
| **🟡 Tier 2: Guarded Safe Mutations** | `POST /issue`, `POST /issue/{id}/comment`, `POST /issue/{id}/transitions`, `POST /issueLink` | **Bounded** (Single issue, reversible) | **Autonomous with Pre-Flight Shields**. Mandatory JQL duplicate check (`jira-triage-guard`), required custom fields introspection, and in-issue audit trace comments. |
| **🟠 Tier 3: High-Impact / Destructive** | `DELETE /issue/{id}`, `PUT /issue/{id}` (bulk), `DELETE /attachment`, `POST /version`, `POST /sprint` | **High** (Team velocity & historical logs) | **Prohibited for Autonomous Execution**. Staging proposal pattern (Dry-Run); requires explicit **Human-in-the-Loop (HITL)** approval. |
| **🔴 Tier 4: Tenant Admin & Governance** | `DELETE /project/{key}`, `POST /user`, `PUT /workflow`, `PUT /permissionscheme`, `POST /webhook` | **Catastrophic** (Organization-wide) | **HARD BLACKLIST (Never Exposed as MCP Tools)**. Deterministic refusal with direct escalation link to Atlassian Admin Console. |

👉 *For deep-dive schema contracts, blast radius analysis, and compliance mapping (SOC 2, ISO 27001, GDPR), read the complete [Enterprise API Tier Taxonomy Specification](docs/ENTERPRISE_API_TIER_TAXONOMY.md).*

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
python -m pytest tests/ -v
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

## 📈 Structured Observability & Audit Tracing

Every transaction across the client, CLI controller, and FastMCP server is automatically instrumented with zero-dependency structured JSON tracing via `shields/tracer.py`.

### 1. Real-Time Trace Log Sample (`logs/jira_trace.log`)
Each outbound API call writes an atomic, append-only JSON event:

```json
{
  "timestamp": "2026-10-06T10:04:33Z",
  "trace_id": "trc-c68108e2",
  "operation": "move_status",
  "endpoint": "/rest/api/3/issue/KAN-4/transitions",
  "status_code": 204,
  "latency_ms": 1482.4,
  "resource_key": "KAN-4",
  "success": true,
  "error": null
}
```

### 2. In-Issue Two-Way Audit Trail (Jira Cloud UI)
When issues transition across columns or mutate, an automated audit trail comment is attached directly to the Jira work item:

> `🤖 [AI Audit] Transitioned to 'Done' via IDE Controller. Trace ID: trc-c68108e2`

### 3. Key Observability Benefits:
* **Correlation:** The `trace_id` links customer Slack conversations, agent tool calls, and Atlassian audit records.
* **SLA Monitoring:** Exact millisecond latency (`latency_ms`) detects upstream Atlassian performance degradation.
* **SIEM / Datadog Ready:** Structured JSON Lines format easily streams to Cloud Logging, Grafana Loki, or Datadog.

---

## 🔒 Security & Zero-Leak Guarantees

* **Credential Isolation:** Strict `.gitignore` rules prevent `.env` or `.env.*` files from ever entering source control.
* **Header Scrubbing:** Basic Auth hashes are synthesized in-memory and never dumped to console or logging sinks.
* **Auditability:** Machine-readable probe reports (`discovery/jira_api_discovery_report.json`) record latency and response structures without leaking API tokens.

---

## 📄 License
MIT License. Created by [Mikhail Azhyshchev](https://github.com/Azhy34).
