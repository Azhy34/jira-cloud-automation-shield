"""
Tier Router: maps every Jira operation to an operational risk tier
(see docs/ENTERPRISE_API_TIER_TAXONOMY.md) and returns a deterministic decision
before anything reaches the network. Unknown operations are denied by default.
"""

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel

ADMIN_CONSOLE_URL = "https://admin.atlassian.com"


class Tier(str, Enum):
    T1_READ = "T1_READ"
    T2_GUARDED = "T2_GUARDED_MUTATION"
    T3_HITL = "T3_HUMAN_APPROVAL"
    T4_FORBIDDEN = "T4_FORBIDDEN"


class Action(str, Enum):
    ALLOW = "ALLOW"
    ALLOW_WITH_PREFLIGHT = "ALLOW_WITH_PREFLIGHT"
    STAGE_FOR_APPROVAL = "STAGE_FOR_APPROVAL"
    REJECT = "REJECT"


OPERATION_TIERS: Dict[str, Tier] = {
    # Exposed as MCP tools
    "search_jira_issues": Tier.T1_READ,
    "check_duplicate_issues": Tier.T1_READ,
    "get_required_fields_meta": Tier.T1_READ,
    "request_restricted_operation": Tier.T1_READ,
    "create_jira_issue": Tier.T2_GUARDED,
    "move_jira_issue_status": Tier.T2_GUARDED,
    "link_jira_issues": Tier.T2_GUARDED,
    # Never exposed as tools — registered so that requests for them get a deterministic answer
    "delete_issue": Tier.T3_HITL,
    "bulk_update_issues": Tier.T3_HITL,
    "delete_attachment": Tier.T3_HITL,
    "create_version": Tier.T3_HITL,
    "delete_project": Tier.T4_FORBIDDEN,
    "create_user": Tier.T4_FORBIDDEN,
    "update_workflow": Tier.T4_FORBIDDEN,
    "update_permission_scheme": Tier.T4_FORBIDDEN,
    "create_webhook": Tier.T4_FORBIDDEN,
}

TIER_ACTIONS: Dict[Tier, Action] = {
    Tier.T1_READ: Action.ALLOW,
    Tier.T2_GUARDED: Action.ALLOW_WITH_PREFLIGHT,
    Tier.T3_HITL: Action.STAGE_FOR_APPROVAL,
    Tier.T4_FORBIDDEN: Action.REJECT,
}

TIER_REASONS: Dict[Tier, str] = {
    Tier.T1_READ: "Read-only, zero blast radius: runs autonomously.",
    Tier.T2_GUARDED: "Single-item mutation: runs only after pre-flight checks (input guard, duplicate triage).",
    Tier.T3_HITL: "High blast radius: not executed by the agent. A staged proposal is returned for human approval.",
    Tier.T4_FORBIDDEN: f"Tenant administration is forbidden for agents. Escalate to an admin: {ADMIN_CONSOLE_URL}",
}


class RouteDecision(BaseModel):
    operation: str
    tier: Tier
    action: Action
    reason: str
    proposal: Optional[Dict[str, Any]] = None


def route(operation: str, arguments: Optional[Dict[str, Any]] = None) -> RouteDecision:
    known = operation in OPERATION_TIERS
    tier = OPERATION_TIERS.get(operation, Tier.T4_FORBIDDEN)
    reason = TIER_REASONS[tier] if known else f"Unknown operation '{operation}' is denied by default. {TIER_REASONS[tier]}"
    proposal = None
    if tier is Tier.T3_HITL:
        proposal = {
            "status": "PENDING_HUMAN_APPROVAL",
            "operation": operation,
            "arguments": arguments or {},
            "next_step": "A human reviews this proposal and runs the operation in Jira.",
        }
    return RouteDecision(operation=operation, tier=tier, action=TIER_ACTIONS[tier], reason=reason, proposal=proposal)
