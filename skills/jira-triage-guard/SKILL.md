---
name: jira-triage-guard
description: "Intelligently triage bug reports, user feedback, and work items by detecting existing duplicates in Jira Cloud before creating new tickets. Enforces the Extract-Search-Analyze-Act workflow to prevent backlog pollution and regression oversights."
---

# Jira Triage & Duplicate Guard Skill

## Overview
This skill guides autonomous AI agents to prevent duplicate Jira ticket creation by proactively running JQL searches across recent open and resolved issues before mutating the backlog.

## Core Operational Workflow

```text
[ Incoming Request / Error Report ]
               │
               ▼
   1. Extract Core Signatures (Tokens, Symptoms, Module)
               │
               ▼
   2. Execute Duplicate Pre-Check (`check_duplicate_issues`)
               │
      ┌────────┴────────┐
      ▼                 ▼
[ Match Found (>75%) ]  [ No Duplicate (<40%) ]
      │                 │
      ▼                 ▼
Recommend Linking       Introspect Required Fields (`get_required_fields_meta`)
or Adding Comment       and Create New Ticket (`create_jira_issue`)
```

### Step 1: Extract Diagnostic Tokens
- Strip generic filler words ("the", "error", "failed", "bug", "issue").
- Retain exact module names, endpoints, error codes (e.g. `410 Gone`, `NullPointerException`, `OAuth2`).

### Step 2: Query Pre-Creation Triage Tool
Call FastMCP tool `check_duplicate_issues`:
```json
{
  "summary": "API Probing Breaking Changes Detection /search/jql",
  "project_key": "KAN"
}
```

### Step 3: Evaluate Match Confidence
- **High Confidence (>= 0.75):** 
  Do NOT create a duplicate ticket. Add an audit comment to the existing issue or link the request.
- **Moderate Confidence (0.40 - 0.74):** 
  Flag possible related tickets or historical fixes. Link issues via `link_jira_issues(link_type="Relates")`.
- **Low Confidence (< 0.40):** 
  Proceed with new issue creation.

### Step 4: Verification & Safe Creation
Before calling `create_jira_issue`:
1. Query `get_required_fields_meta(project_key, issue_type)` to verify all required enterprise fields.
2. Supply required custom fields to prevent `400 Bad Request` schema errors.
