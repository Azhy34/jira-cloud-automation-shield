---
name: jira-spec-to-backlog
description: "Decompose technical specifications, PRDs, and architecture documents into structured Jira backlogs. Creates a master Epic, decomposes atomic tasks with Definition of Done (DoD), and establishes issueLink dependency graphs."
---

# Jira Spec-to-Backlog Skill

## Overview
Automates the translation of unstructured requirements into production-grade Jira Software hierarchy:
`Master Epic` ➔ `Atomic Child Tasks / Stories` ➔ `Dependency Graph (Blocks / Relates)`.

## Core Decomposition Workflow

### 1. Identify Milestone Scope
- Group requirements into a single cohesive functional initiative.
- Formulate a clear Master Epic summary: `[<DOMAIN>-CORE] <Feature Title>`.

### 2. Create the Master Epic First
Create the organizing container in Jira:
```json
{
  "project_key": "KAN",
  "issue_type": "Epic",
  "summary": "[AUTH-CORE] Enterprise OAuth 2.0 Identity Gateway",
  "description": "Master Epic for SSO and token rotation architecture."
}
```

### 3. Decompose Atomic Tasks (3-7 items)
For each implementation slice:
1. Ensure the task is independently testable within 1-2 days.
2. Structure the description with mandatory **Acceptance Criteria (DoD)** checklist.
3. Link the child item to the Epic via `parent_key`.

### 4. Establish Horizontal Dependencies (`Issue Linking`)
Do not leave tasks floating as a flat list:
- Call `link_jira_issues(inward_key="TASK-A", outward_key="TASK-B", link_type="Blocks")` when Task B depends on Task A.
- Use `Relates` for contextual dependencies across domains.

### 5. Review Definition of Done (DoD) Pattern
Every task created must contain:
```text
Deliverables:
• Implementation artifact or API endpoint

Acceptance Criteria (AC):
- [ ] Automated unit tests passing in CI
- [ ] Zero secret leaks in configuration
- [ ] Latency SLA benchmark verified
```
