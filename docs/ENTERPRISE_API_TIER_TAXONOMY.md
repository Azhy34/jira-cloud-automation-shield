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
│   • Pre-network schema validation (summary length, project key regex, ADF format)│
│   • Immediate self-correction hint returned on schema failure without net call   │
│                                                                                  │
│   [ STEP 9 HARDENING GUARDS ]                                                    │
│   • check_duplicate_issues: Pre-creation JQL similarity query (last 90 days)     │
│   • get_createmeta_fields: Introspects required custom fields before POST         │
│                                                                                  │
│   [ ZERO-DEPENDENCY TRACER & AUDIT ENGINE ]                                      │
│   • Emits correlation `trace_id` (trc-xxxx) to append-only JSON log              │
│   • Attaches two-way audit trail comment to Jira Cloud work items                │
│                                                                                  │
│   [ LAYER 2: Outbound Response Shield & Compression ]                            │
│   • Filters 35KB raw Atlassian response down to <1KB normalized Pydantic model   │
│   • Protects agent from HTTP 4xx/5xx network crashes via ServiceResult fallback   │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │ 2. Scoured, Validated TLS 1.3 Requests
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
  * `GET /rest/api/3/issue/createmeta` — Custom field & issue type schema discovery.
  * `GET /rest/api/3/issue/{issueIdOrKey}/transitions` — Workflow state discovery.
  * `GET /rest/api/3/field`, `GET /rest/api/3/priority`, `GET /rest/api/3/issuetype` — Enterprise taxonomies.
* **Agent Governance & Architectural Controls:**
  * **Tool Choice Mode:** `FunctionCallingConfig.Mode.AUTO` or `Mode.ANY`.
  * **Field Projection Masks:** Enforce explicit projection (`fields: ["summary", "status", "priority", "assignee"]`) to compress payloads from 35KB down to <1KB, preserving LLM token efficiency.
  * **Client-Side Caching:** Cache static metadata (`createmeta`, `field`, `priority`) with a 15-minute TTL.
  * **Pagination Bounds:** Hardcap `maxResults <= 50` and enforce `validateQuery=strict` to prevent expensive unbounded scans.

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
  * **Pre-Flight Duplicate Triage:** Agent **must execute** `find_similar_issues` (via `jira-triage-guard`) prior to calling `POST /issue`.
  * **Schema Introspection Shield:** Introspect `createmeta` before creation to ensure required enterprise custom fields are satisfied, avoiding HTTP 400 rejection.
  * **In-Issue Audit Tracing:** Every state mutation injects an in-issue audit comment with a unique `trace_id` (e.g., `trc-c68108e2`).
  * **Idempotency Guarantees:** Client tracks retry loops to avoid creating duplicate issues upon network timeouts.

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
  * **Staging / Proposal Pattern (Dry-Run):** The agent generates a structured proposal (`ActionProposalSchema`) displaying the target issue, affected fields, and deletion reason.
  * **Mandatory Human Approval (HITL):** Execution requires explicit human confirmation via an authenticated webhook, Telegram confirmation button, or CLI prompt with an ephemeral HMAC approval token.

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
    > *"This action requires Organization Administrator privileges and is blocked for autonomous AI agents under enterprise Least Privilege policy. Please perform this operation directly in the Atlassian Admin Console: https://admin.atlassian.com"*

---

## 📋 Operational Decision Matrix

| Dimension | Tier 1 (Read/Discovery) | Tier 2 (Guarded Mutation) | Tier 3 (High-Impact / Destructive) | Tier 4 (Admin / Governance) |
|---|---|---|---|---|
| **Blast Radius** | Zero | Bounded (Single Item) | High (Sprint/Milestone) | Catastrophic (Tenant-Wide) |
| **Agent Autonomy** | 100% Autonomous | Autonomous with Pre-Flight Shields | Prohibited (Approval Required) | 0% (Hard Blacklist) |
| **ADK Tool Choice Mode** | `Mode.AUTO` / `Mode.ANY` | `Mode.AUTO` (Guarded) | Proposal Only (`Mode.NONE` for mutation) | Out of Scope / Refusal |
| **Pydantic Shield** | Field Projection & Fallback | Two-Layer Validation + Duplicate JQL | Dry-Run Proposal Contract | N/A (Excluded) |
| **Audit Trace** | Client Metric (Latency) | In-Issue Comment with `TraceID` | Audit Trail + Human Approver ID | Security Audit Log (Atlassian) |
| **FastMCP Status** | Bundled (`search_jira_issues`, `createmeta`) | Bundled (`create_jira_issue`, `move_status`, `link`) | Staging Proposal Tool Only | **Never Exposed** |

---

## 💡 Practical Implementation Example

### Pre-Flight Shield Flow for Tier 2 Creation

```text
User Prompt: "Create a bug ticket: Payment gateway timeout on checkout"
                     │
                     ▼
[ TIER 1 QUERY ] ──▶ search_jira_issues(jql='text ~ "Payment gateway timeout"')
                     │
                     ├─▶ Duplicate Found? ──▶ Attach comment to existing ticket (Tier 2) & STOP.
                     │
                     ▼ (No Duplicate)
[ TIER 1 QUERY ] ──▶ get_required_fields_meta(project_key='KAN', issue_type='Bug')
                     │
                     ▼
[ TIER 2 WRITE ] ──▶ create_jira_issue(summary, description, project_key='KAN')
                     │
                     ▼
[ OBSERVABILITY ] ──▶ Log TraceID to local log + inject audit comment to Jira ticket.
```

---

## 🏆 Compliance & Certification Relevance

This 4-Tier Operational Risk Hierarchy directly satisfies:
* **Google Cloud Professional Cloud Architect (PCA):** Enterprise Governance, Least Privilege IAM, and Defense-in-Depth boundaries.
* **Google Cloud Professional Cloud Developer (PCD):** Resilient API Design, Error Contracts, and Distributed Tracing.
* **Enterprise Security Standards:** SOC 2 Type II, ISO 27001, and GDPR Article 32 (Security of Processing).
