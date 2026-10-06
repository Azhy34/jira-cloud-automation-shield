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
│    • 7 tools · Tier Router · Layer 1 input guard · ServiceResult       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│           Two-Layer Pydantic Error Shield (`shields/jira_shield.py`)   │
│    • Strict Contract Validation        • Normalized statusCategory     │
│    • Error envelope (ServiceResult)    • Fail-closed duplicate triage  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│              Resilient Jira Client (`client/jira_client.py`)           │
│    • Modern `/rest/api/3/search/jql` Protocol (Zero 410 Errors)        │
│    • Atlassian Document Format (ADF) Payload Engine                    │
│    • Credentials never logged · GET retries on 429/5xx                 │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTPS only
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
* 🛡️ **Seamless Migration:** The client immediately migrated to **`GET /rest/api/3/search/jql`** with explicit field projection masks (`fields: summary,status,issuetype,parent,description,resolution`) and `nextPageToken` pagination, ensuring zero production downtime.
* 🔁 **Second deprecated endpoint (Step 11):** the same discovery discipline, applied to Atlassian's OpenAPI spec, showed that `GET /rest/api/3/issue/createmeta` is marked `deprecated`. Required-field introspection now uses `/issue/createmeta/{project}/issuetypes` and `/issuetypes/{issueTypeId}`.
* 🐞 **Triage miss caught by a live smoke test (Step 11):** Jira text search needs every word to match, and it indexes `[INT-103]` as one token — so an exact duplicate of `KAN-4` was not found. Triage now drops ticket prefixes and digit tokens, searches all terms first and any term as a fallback, then ranks by similarity.

### SLA & Latency Benchmark Results
| Endpoint | Method | Latency | Status | Purpose |
|---|---|---|---|---|
| `/rest/api/3/myself` | `GET` | **455 ms** | `200 OK` | Identity handshake & permissions |
| `/rest/api/3/project` | `GET` | **347 ms** | `200 OK` | Workspace project enumeration |
| `/rest/api/3/project/{key}` | `GET` | **387 ms** | `200 OK` | Issue type metadata retrieval |
| `/rest/api/3/search/jql` | `GET` | **467 ms** | `200 OK` | JQL query execution with field masks |
| `/rest/api/3/issue` | `POST` | **1289 ms** | `201 Created` | ADF mutation testing (Issue creation) |

---

## 📐 Enterprise Architecture Principles & Design Methodology

This integration gateway is built on four core enterprise design principles — resilience, bounded agent autonomy and auditability:

1. **Principle of Least Privilege (PoLP):** Rather than exposing all 500+ raw Atlassian REST endpoints to LLM context, the gateway provides 7 atomic tools, each routed through a 4-tier risk router (`shields/tier_router.py`). Unknown operations are denied by default.
2. **Pre-Flight Shields:** Every tool call passes the Layer 1 Pydantic argument guard (`shields/tool_inputs.py`) before any network call. `create_jira_issue` runs duplicate triage itself and is fail-closed; an HTTP 400 returns the project's required fields as a hint.
3. **Context Compression:** Field projection masks cut a search payload from 11–25 KB to ~2.4 KB per issue (78–91% smaller, measured on this Jira site).
4. **Structured Auditability & Traceability:** Zero-dependency correlation tracing writes exactly one `trace_id` entry per HTTP call to append-only JSON Lines; status transitions add an audit comment to the Jira work item.

---

## 🤖 Model Context Protocol (FastMCP) for AI Agents

Run the bundled FastMCP server to grant autonomous AI agents tool access to your Jira board:

```bash
python mcp_server/jira_mcp.py
```

Every tool runs the same pipeline: **Tier Router → Layer 1 input guard → pre-flight checks (Tier 2) → client → `ServiceResult`**. Tools never raise to the agent: a failure comes back as `{"ok": false, "error": …, "hint": …, "tier": …, "trace_id": …}`.

### Registered Agent Tools:
1. `search_jira_issues(jql, max_results)` — *Tier 1.* Query board state via JQL (max 50 results, paginated).
2. `create_jira_issue(summary, description, project_key, issue_type, parent_key)` — *Tier 2.* Runs duplicate triage first: a likely duplicate (similarity ≥ 0.75) or an unavailable triage blocks creation.
3. `move_jira_issue_status(issue_key, target_status)` — *Tier 2.* Transition by exact status name or category (*To Do*, *In Progress*, *Done*); never picks a review status for *In Progress*. Leaves an audit comment.
4. `check_duplicate_issues(summary, project_key)` — *Tier 1.* Triage on its own; returns `TRIAGE_UNAVAILABLE`, never `CREATE_NEW`, if the search fails.
5. `get_required_fields_meta(project_key, issue_type)` — *Tier 1.* Required fields via the current createmeta endpoints, cached for 10 minutes.
6. `link_jira_issues(inward_key, outward_key, link_type)` — *Tier 2.* `Blocks`, `Relates` or `Duplicate`; for `Blocks`, `inward_key` is the blocker.
7. `request_restricted_operation(operation, arguments)` — *Tier 1.* For anything without a tool (delete, bulk edit, admin): Tier 3 returns a staged proposal for human approval, Tier 4 and unknown operations return a refusal with the admin console link. Nothing is executed.

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
| **2. New Domain Workflows** | **FastMCP Extension Pattern** | A new operation (e.g., `assign_issue`) is a `@mcp.tool()` that registers its tier in `OPERATION_TIERS` and calls `_run()` with a Layer 1 input model — it inherits tier routing, argument validation, the `ServiceResult` envelope and `JiraTracer` logging. |
| **3. Destructive / Admin Operations** | **Least Privilege & Human Escalation** | High-blast-radius operations (`delete_issue`, `delete_project`) are never exposed as tools. When requested, the agent calls `request_restricted_operation`: Tier 3 returns a staged proposal for a human, Tier 4 a refusal with the admin console link. |

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

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             Autonomous AI Agent                                  │
│                      (Google ADK / Claude / Cursor / IDE)                        │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │ 1. Invokes Clean MCP Tool
                                         │    (e.g., create_jira_issue, search_jira_issues)
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│               FastMCP Gateway & Two-Layer Pydantic Error Shield                  │
│                                                                                  │
│   [ TIER ROUTER & BLAST RADIUS FIREWALL ]                                        │
│   ├── 🟢 TIER 1: Read & Discovery   ──▶ Auto-Pass + Field Projection Mask         │
│   ├── 🟡 TIER 2: Guarded Mutations  ──▶ Pre-Flight JQL Duplicate & Meta Checks   │
│   ├── 🟠 TIER 3: Destructive/Bulk   ──▶ INTERCEPT: Generate Staged Proposal (HITL)│
│   └── 🔴 TIER 4: Tenant Admin       ──▶ HARD REJECT: Deterministic Refusal Link  │
│                                                                                  │
│   [ LAYER 1: Inbound Parsed Arguments Guard (Pydantic v2) ]                      │
│   • Pre-network validation: key regex, single-line summary, size limits          │
│   • Immediate self-correction hint returned on schema failure without net call   │
│                                                                                  │
│   [ STEP 9 + 11 HARDENING GUARDS ]                                               │
│   • create_jira_issue runs duplicate triage itself (fail-closed, 90 days)        │
│   • On HTTP 400: required fields via current createmeta (cached 10 min)          │
│                                                                                  │
│   [ ZERO-DEPENDENCY TRACER & AUDIT ENGINE ]                                      │
│   • Emits correlation `trace_id` (trc-xxxx) to append-only JSON log              │
│   • Audit comment on transitions; a failed comment is reported                   │
│                                                                                  │
│   [ LAYER 2: Outbound Response Shield & Compression ]                            │
│   • Field projection: 11-25 KB -> ~2.4 KB per issue (measured)                   │
│   • Tools never raise: every outcome is a ServiceResult (ok, error, hint)        │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │ 2. HTTPS only; GET retried on 429/5xx (Retry-After)
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│              Atlassian Jira Cloud REST API v3 (500+ Raw Endpoints)               │
│         (`POST /rest/api/3/issue`, `GET /rest/api/3/search/jql`, etc.)           │
└──────────────────────────────────────────────────────────────────────────────────┘
```


| Operational Tier | Representative Endpoints | Blast Radius | Agent Autonomy & Governance |
|---|---|---|---|
| **🟢 Tier 1: Read & Discovery** | `GET /myself`, `GET /project`, `GET /search/jql`, `GET /createmeta/{project}/issuetypes`, `GET /transitions`, `GET /field` | **Zero** (Idempotent query) | **100% Autonomous (`Mode.AUTO` / `Mode.ANY`)**. Field projection masks; `createmeta` cached for 10 minutes; `max_results` capped at 50. |
| **🟡 Tier 2: Guarded Safe Mutations** | `POST /issue`, `POST /issue/{id}/comment`, `POST /issue/{id}/transitions`, `POST /issueLink` | **Bounded** (Single issue, reversible) | **Autonomous with Pre-Flight Shields**. Duplicate triage enforced inside `create_jira_issue` (fail-closed); required fields returned on HTTP 400; audit comment on transitions. |
| **🟠 Tier 3: High-Impact / Destructive** | `DELETE /issue/{id}`, `PUT /issue/{id}` (bulk), `DELETE /attachment`, `POST /version`, `POST /sprint` | **High** (Team velocity & historical logs) | **Prohibited for Autonomous Execution**. `request_restricted_operation` returns a staged proposal (`PENDING_HUMAN_APPROVAL`); a human executes it. |
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

### 3. Run Automated Tests (no network, no credentials needed)
```bash
pip install -r requirements-dev.txt
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

> `🤖 [AI Audit] Transitioned to 'Готово' via Jira Shield. Trace ID: trc-c68108e2`

If the comment cannot be saved (e.g. no permission), the failure is traced and `move_status` returns `audit_comment_saved: false` instead of hiding it.

### 3. Key Observability Benefits:
* **Correlation:** The `trace_id` links customer Slack conversations, agent tool calls, and Atlassian audit records.
* **SLA Monitoring:** Exact millisecond latency (`latency_ms`) detects upstream Atlassian performance degradation.
* **SIEM / Datadog Ready:** Structured JSON Lines format easily streams to Cloud Logging, Grafana Loki, or Datadog.

---

## 🔒 Security & Zero-Leak Guarantees

* **Credential Isolation:** Strict `.gitignore` rules prevent `.env` or `.env.*` files from ever entering source control. The full git history contains no API token and no personal email.
* **Credentials Never Logged:** The Basic auth header is built in memory; traces record only operation, endpoint, status, latency and issue key.
* **HTTPS Only:** The client refuses a non-`https://` Jira URL.
* **Safe Retries:** Only GET requests are retried (429/502/503/504, honouring `Retry-After`); a POST is never retried, so a timeout cannot create a duplicate issue.
* **Auditability:** Machine-readable probe reports (`discovery/jira_api_discovery_report.json`) record latency and response structures without leaking API tokens.

---

## ✅ Verification

**40 automated tests** (pytest + `requests-mock`, no network) run in CI on every push and pull request:

| Suite | Tests | Covers |
|---|---|---|
| `tests/test_jira_shield.py` | 7 | Pydantic response contracts |
| `tests/test_client.py` | 19 | HTTPS-only, pagination, one trace per call (HTTP and network errors), fail-closed triage, triage term extraction and fallback, project-key injection, createmeta migration and cache, required-field hint on 400, audit-comment failure, status matching on Russian workflow names, comments as plain text |
| `tests/test_mcp_tools.py` | 14 | 7 registered tools, Tier Router T1–T4 and deny-by-default, Layer 1 rejects bad input with no network call, duplicate and fail-closed creation never POST, staged proposal and refusal, tools never raise |

**Live read-only smoke test** against Jira Cloud (2026-10-06, nothing created):
* 12 issues fetched in 3 pages of 5 via `nextPageToken`; `resolution` populated.
* `createmeta` served by the current endpoints (Task and Epic required fields).
* `create_jira_issue` with the exact summary of `KAN-4` → blocked as a duplicate (similarity 1.0).
* `project_key="kan; DROP"` → rejected by Layer 1 with no network call.
* `delete_issue` → staged proposal; `delete_project` → refusal with the admin console link.

---

## 📄 License
MIT License. Created by [Mikhail Azhyshchev](https://github.com/Azhy34).
