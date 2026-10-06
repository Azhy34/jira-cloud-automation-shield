# 🏛️ Enterprise Jira API Operational Risk & Endpoint Taxonomy (4-Tier Architecture)

> **Architectural Standard:** Enterprise Agentic AI Integration  
> **Target Framework:** Atlassian Jira Cloud REST API v3 & Model Context Protocol (FastMCP)  
> **Reference Model:** Bounded Blast Radius & Principle of Least Privilege (PoLP)  

---

## 🎯 Executive Summary & The Problem

The official Atlassian Jira Cloud REST API v3 specification documents **500+ endpoints** across dozens of domains (Issues, Projects, Workflows, Sprints, Permissions, Webhooks, Users, etc.).

However, official API documentation is **purely syntactic**: it describes HTTP methods, payload schemas, and status codes, but remains **completely silent on business risk, agent blast radius, concurrency hazards, compliance audit boundaries, and operational guardrails**.

When autonomous Large Language Models (LLMs) or AI Agents are granted unconstrained tool access to raw API endpoints, catastrophic operational failures occur:
1. **Backlog Pollution:** An autonomous agent creates thousands of duplicate issues without JQL pre-filtering.
2. **Data & Compliance Loss:** An agent calls `DELETE /rest/api/3/issue/{id}` or `DELETE /rest/api/3/version/{id}`, destroying billable logs, sprint metrics, and SOX/ISO-27001 audit histories.
3. **Context Window Exhaustion:** Unfiltered 30KB Jira JSON responses overwhelm LLM context windows, spiking token costs and increasing hallucination rates.
4. **Tenant-Level Destruction:** Accidental calls to administrative endpoints (`DELETE /rest/api/3/project/{key}`, `PUT /rest/api/3/workflow`) compromise enterprise tenants.

To solve this, this repository establishes a **4-Tier Operational Risk Hierarchy and Application Taxonomy**, mapping Atlassian's 500+ endpoints into deterministic execution boundaries.

---

## 📊 The 4-Tier Operational Risk Pyramid

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

---

## 🛡️ The Two-Layer Pydantic Shield Architecture: From 500+ Raw Endpoints to 4 Safe Tiers

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

---

## 🧱 Comprehensive Tier Breakdown

### 🟢 Tier 1: Read & Discovery (Zero Blast Radius — Autonomous Agent Execution)

* **Definition:** Purely idempotent query and metadata introspection operations. Modifies zero state in Jira Cloud.
* **Blast Radius:** **Zero**. Cannot alter tickets, sprint timelines, or user assignments.
* **Representative Endpoints:**
  * `GET /rest/api/3/myself` — Identity & token permission handshake.
  * `GET /rest/api/3/project` & `GET /rest/api/3/project/{key}` — Project catalog discovery.
  * `GET /rest/api/3/search/jql` & `POST /rest/api/3/search/jql` — Targeted JQL querying.
  * `GET /rest/api/3/issue/{issueIdOrKey}` — Individual issue payload retrieval.
  * `GET /rest/api/3/issue/createmeta/{projectIdOrKey}/issuetypes` and `…/issuetypes/{issueTypeId}` — Custom field & issue type schema discovery (the legacy `GET /issue/createmeta` is deprecated).
  * `GET /rest/api/3/issue/{issueIdOrKey}/transitions` — Workflow state discovery.
  * `GET /rest/api/3/field`, `GET /rest/api/3/priority`, `GET /rest/api/3/issuetype` — Enterprise taxonomies.
* **Agent Governance & Architectural Controls:**
  * **Tool Choice Mode:** `FunctionCallingConfig.Mode.AUTO` or `Mode.ANY`.
  * **Field Projection Masks:** Explicit projection (`fields: summary,status,issuetype,parent,description,resolution`) cuts a search payload from 11–25 KB to ~2.4 KB per issue (78–91% smaller, measured), preserving LLM token efficiency.
  * **Client-Side Caching:** `createmeta` is cached for 10 minutes. Caching `field` and `priority` is a planned extension.
  * **Pagination Bounds:** `max_results` is capped at 50 by the Layer 1 guard; the client follows `nextPageToken` up to that bound.

---

### 🟡 Tier 2: Guarded Safe Mutations & Triage (Bounded Blast Radius — Agent Automation with Pre-Flight Shields)

* **Definition:** Single-item creation, progression, and annotation operations that add value without destroying historical context or overwriting unrelated work.
* **Blast Radius:** **Low / Bounded**. Localized strictly to an individual work item; non-destructive and reversible.
* **Representative Endpoints:**
  * `POST /rest/api/3/issue` — Single work item creation (Task, Story, Bug, Subtask).
  * `POST /rest/api/3/issue/{issueIdOrKey}/comment` — Audit notes, triage summaries, and root cause updates.
  * `POST /rest/api/3/issue/{issueIdOrKey}/transitions` — Forward workflow transitions (*To Do* ➔ *In Progress* ➔ *Done*).
  * `POST /rest/api/3/issueLink` — Semantic dependency mapping (*Blocks*, *Relates*, *Duplicate*).
  * `PUT /rest/api/3/issue/{issueIdOrKey}/assignee` — Individual ownership assignment.
* **Agent Governance & Architectural Controls:**
  * **Pre-Flight Duplicate Triage:** `create_jira_issue` runs `find_similar_issues` itself before `POST /issue` — enforced in code, not left to the prompt. A likely duplicate blocks creation, and so does an unavailable triage (fail-closed).
  * **Schema Introspection Shield:** When `POST /issue` returns HTTP 400, the client loads the required fields from `createmeta` and returns them as a fix-it hint.
  * **In-Issue Audit Tracing:** Status transitions add an in-issue audit comment with the `trace_id` (e.g., `trc-c68108e2`); a comment that fails to save is reported, not hidden.
  * **No Duplicate on Retry:** Only GET requests are retried; `POST /issue` is never retried, so a network timeout cannot create a second issue.

---

### 🟠 Tier 3: High-Impact & Destructive Mutations (High Blast Radius — Mandatory Human-in-the-Loop [HITL])

* **Definition:** Operations that permanently delete data, alter sprint commitments, perform unconstrained bulk updates, or impact release milestones.
* **Blast Radius:** **High**. Can destroy compliance records, delete billable logs, or alter sprint velocity for entire engineering departments.
* **Representative Endpoints:**
  * `DELETE /rest/api/3/issue/{issueIdOrKey}` — Permanent issue deletion.
  * `PUT /rest/api/3/issue/{issueIdOrKey}` — Bulk field updates, overwriting historical descriptions or Story Points.
  * `DELETE /rest/api/3/issue/{issueIdOrKey}/attachments/{id}` — Deletion of reproduction evidence or audit artifacts.
  * `POST /rest/api/3/version` & `DELETE /rest/api/3/version/{id}` — Release version creation or deletion.
  * `POST /rest/api/3/issue/bulk` — Mass creation/editing of hundreds of tickets simultaneously.
  * `POST /rest/api/3/board/{boardId}/sprint` & `PUT /rest/api/3/sprint/{id}` — Starting or closing sprint cycles.
* **Agent Governance & Architectural Controls:**
  * **Autonomous Execution Strictly Prohibited:** Agents are **never** permitted to execute Tier 3 endpoints autonomously.
  * **Staging / Proposal Pattern (Dry-Run):** The agent calls `request_restricted_operation`; the Tier Router returns a proposal `{status: PENDING_HUMAN_APPROVAL, operation, arguments}` and executes nothing.
  * **Mandatory Human Approval (HITL):** A human reviews the proposal and runs the operation in Jira. An in-chat approval channel (e.g. a Slack button with a short-lived signed token) is a planned extension.

---

### 🔴 Tier 4: Tenant Administration & Security Governance (Catastrophic Blast Radius — Hard Blacklist)

* **Definition:** Organization-wide governance, user access management, workflow schema modification, audit log lifecycle, and billing.
* **Blast Radius:** **Catastrophic / Organization-Wide**. Vulnerable to tenant takeover, privilege escalation, and business disruption.
* **Representative Endpoints:**
  * `DELETE /rest/api/3/project/{projectIdOrKey}` — Entire project deletion.
  * `POST /rest/api/3/user` & `DELETE /rest/api/3/user` — User lifecycle and invitation management.
  * `PUT /rest/api/3/workflow` & `DELETE /rest/api/3/workflowScheme` — Core workflow logic alterations.
  * `PUT /rest/api/3/permissionscheme` — Security access control modifications.
  * `POST /rest/api/3/webhook` — Arbitrary third-party webhook URL registration (SSRF vulnerability risk).
  * `GET /rest/api/3/auditing/record` — Audit trail tampering or log purging.
  * Billing, licensing, and subscription management endpoints.
* **Agent Governance & Architectural Controls:**
  * **Hard Blacklist (Never Exposed as MCP Tools):** Tier 4 endpoints are completely excluded from the agent gateway.
  * **Deterministic Refusal & Escalation:** When a user prompts the agent to perform a Tier 4 task (e.g., *"Delete the KAN project"*), the agent returns a deterministic response:
    > *"Tenant administration is forbidden for agents. Escalate to an admin: https://admin.atlassian.com"*
  * **Deny by Default:** An operation that is not in the router's registry is treated as Tier 4.

---

## 📋 Operational Decision Matrix

| Dimension | Tier 1 (Read/Discovery) | Tier 2 (Guarded Mutation) | Tier 3 (High-Impact / Destructive) | Tier 4 (Admin / Governance) |
|---|---|---|---|---|
| **Blast Radius** | Zero | Bounded (Single Item) | High (Sprint/Milestone) | Catastrophic (Tenant-Wide) |
| **Agent Autonomy** | 100% Autonomous | Autonomous with Pre-Flight Shields | Prohibited (Approval Required) | 0% (Hard Blacklist) |
| **ADK Tool Choice Mode** | `Mode.AUTO` / `Mode.ANY` | `Mode.AUTO` (Guarded) | Proposal Only (`Mode.NONE` for mutation) | Out of Scope / Refusal |
| **Pydantic Shield** | Field Projection & Fallback | Two-Layer Validation + Duplicate JQL | Dry-Run Proposal Contract | N/A (Excluded) |
| **Audit Trace** | Client Metric (Latency) | In-Issue Comment with `TraceID` | Audit Trail + Human Approver ID | Security Audit Log (Atlassian) |
| **FastMCP Status** | Bundled (`search_jira_issues`, `check_duplicate_issues`, `get_required_fields_meta`) | Bundled (`create_jira_issue`, `move_jira_issue_status`, `link_jira_issues`) | `request_restricted_operation` (proposal only) | **Never Exposed** (refusal via `request_restricted_operation`) |

---

## 💡 Practical Implementation Example

### Pre-Flight Shield Flow for Tier 2 Creation

```text
User Prompt: "Create a bug ticket: Payment gateway timeout on checkout"
                     │
                     ▼
[ TIER 2 TOOL ] ──▶ create_jira_issue(summary="Payment gateway timeout on checkout", issue_type="Bug")
                     │
                     ├─▶ Tier Router: create_jira_issue = T2 → allowed with pre-flight
                     ├─▶ Layer 1: key regex, single-line summary, size limits (no network on failure)
                     ├─▶ Pre-flight triage (inside the tool): summary ~ all terms, then any term
                     │      ├─▶ Duplicate (≥ 0.75)  ──▶ ok=false + "link or comment KAN-xx" & STOP
                     │      └─▶ Triage unavailable  ──▶ ok=false (fail-closed) & STOP
                     ▼ (No duplicate)
[ TIER 2 WRITE ] ──▶ POST /rest/api/3/issue   (on HTTP 400 → hint lists required fields)
                     │
                     ▼
[ OBSERVABILITY ] ──▶ One trace_id per HTTP call in the JSON Lines log; ServiceResult carries the trace_id.
```

---

## ✅ Implementation Status (what is enforced in code)

| Control | Where | Tested in |
|---|---|---|
| Tier Router T1–T4, deny by default | `shields/tier_router.py` | `tests/test_mcp_tools.py::test_tier_router` |
| Layer 1 argument guard, no network on failure | `shields/tool_inputs.py`, `mcp_server/jira_mcp.py::_run` | `test_layer1_rejects_*` |
| Duplicate triage inside `create_jira_issue`, fail-closed | `mcp_server/jira_mcp.py`, `client/jira_client.py::find_similar_issues` | `test_create_blocks_duplicate_*`, `test_create_is_blocked_when_triage_is_unavailable`, `test_triage_*` |
| `ServiceResult` envelope, tools never raise | `shields/jira_shield.py`, `mcp_server/jira_mcp.py::_run` | `test_tools_never_raise_on_missing_credentials` |
| Staged proposal (T3) and refusal (T4) | `request_restricted_operation` | `test_restricted_operation_*` |
| Current createmeta endpoints + 10-min cache, required-field hint on 400 | `client/jira_client.py` | `test_createmeta_*`, `test_create_issue_400_hint_*` |
| One trace per HTTP call, failed audit comment reported | `client/jira_client.py::_request`, `add_audit_comment` | `test_http_error_*`, `test_network_error_*`, `test_audit_comment_*` |
| GET-only retries honouring `Retry-After`, HTTPS only | `client/jira_client.py` | `test_https_is_required` |

**Planned, not implemented:** caching `field` / `priority`, an in-chat approval channel for Tier 3, per-user OAuth tokens (the client uses one API token), migration to MCP SDK 2.x (`MCPServer`; pinned to `mcp<2` for now).

---

## 🏆 Compliance & Certification Relevance

This 4-Tier Operational Risk Hierarchy directly satisfies:
* **Google Cloud Professional Cloud Architect (PCA):** Enterprise Governance, Least Privilege IAM, and Defense-in-Depth boundaries.
* **Google Cloud Professional Cloud Developer (PCD):** Resilient API Design, Error Contracts, and Distributed Tracing.
* **Enterprise Security Standards:** SOC 2 Type II, ISO 27001, and GDPR Article 32 (Security of Processing).
