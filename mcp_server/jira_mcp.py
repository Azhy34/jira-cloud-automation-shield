"""
Model Context Protocol (MCP) Server for Jira Cloud Automation Shield.
Every tool runs the same pipeline:
  Tier Router → Layer 1 input guard → pre-flight checks (Tier 2) → client → ServiceResult.
Tools never raise to the agent: failures come back as ServiceResult(ok=False, error, hint).
"""

import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Type

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")
load_dotenv(ROOT / ".env.jira")
load_dotenv(ROOT.parent / ".env.jira")

from mcp.server.fastmcp import FastMCP
from client.jira_client import JiraCloudClient, JiraApiError
from shields.jira_shield import ServiceResult, JiraErrorResponse
from shields.tier_router import Action, route
from shields.tool_inputs import (
    SearchInput, CreateIssueInput, MoveStatusInput, DuplicateCheckInput,
    CreateMetaInput, LinkInput, RestrictedOperationInput, format_validation_hint
)

mcp = FastMCP("jira-automation-shield")


def get_client() -> JiraCloudClient:
    return JiraCloudClient.from_env()


def _run(operation: str, input_model: Type[BaseModel], raw_args: Dict[str, Any],
         action: Callable[[Any, JiraCloudClient], Any]) -> dict:
    decision = route(operation)
    if decision.action in (Action.STAGE_FOR_APPROVAL, Action.REJECT):
        return ServiceResult(ok=False, tier=decision.tier.value, data=decision.proposal,
                             hint=decision.reason).model_dump(mode="json")
    try:
        args = input_model(**raw_args)
    except ValidationError as exc:
        return ServiceResult(
            ok=False, tier=decision.tier.value,
            error=JiraErrorResponse(errorMessages=["Invalid tool arguments"], status_code=422),
            hint=format_validation_hint(exc),
        ).model_dump(mode="json")

    client: Optional[JiraCloudClient] = None
    try:
        client = get_client()
        outcome = action(args, client)
        result = outcome if isinstance(outcome, ServiceResult) else ServiceResult(ok=True, data=outcome)
    except JiraApiError as exc:
        result = ServiceResult(ok=False, error=exc.error, hint=exc.hint)
    except Exception as exc:  # last-resort boundary: the agent always gets a structured answer
        result = ServiceResult(
            ok=False,
            error=JiraErrorResponse(errorMessages=[f"{type(exc).__name__}: {exc}"], status_code=0),
            hint="Unexpected error — check the arguments or escalate; do not retry blindly.",
        )
    result.tier = decision.tier.value
    result.trace_id = client.last_trace_id if client else None
    return result.model_dump(mode="json")


@mcp.tool()
def search_jira_issues(jql: str, max_results: int = 20) -> dict:
    """
    Search Jira issues using Jira Query Language (JQL) via the enhanced /search/jql API.

    Args:
        jql: JQL query string (e.g., 'project = KAN AND status != Done')
        max_results: Maximum number of issues to return (1-50)
    """
    def action(args: SearchInput, client: JiraCloudClient):
        resp = client.search_issues_jql(args.jql, max_results=args.max_results)
        return [
            {
                "key": i.key,
                "summary": i.fields.summary,
                "status": i.fields.status.name,
                "type": i.fields.issuetype.name,
                "resolution": i.fields.resolution.name if i.fields.resolution else None,
                "parent": i.fields.parent.key if i.fields.parent else None,
            }
            for i in resp.issues
        ]
    return _run("search_jira_issues", SearchInput, {"jql": jql, "max_results": max_results}, action)


@mcp.tool()
def create_jira_issue(
    summary: str,
    description: str,
    project_key: str = "KAN",
    issue_type: str = "Task",
    parent_key: Optional[str] = None
) -> dict:
    """
    Create an issue with an ADF description. A duplicate check always runs first:
    a likely duplicate (similarity >= 0.75) blocks creation, and so does an unavailable triage (fail-closed).

    Args:
        summary: Title of the issue (single line, 3-255 chars)
        description: Description of the work item
        project_key: Key of the project (e.g. 'KAN')
        issue_type: Type of issue ('Task', 'Story', 'Bug', 'Epic')
        parent_key: Optional parent key to attach to (e.g. 'KAN-1')
    """
    def action(args: CreateIssueInput, client: JiraCloudClient):
        triage = client.find_similar_issues(args.summary, args.project_key)
        if triage.recommendation == "TRIAGE_UNAVAILABLE":
            return ServiceResult(
                ok=False, data={"triage": triage.model_dump()},
                hint="Duplicate triage is unavailable, so creation is blocked (fail-closed). Retry later.",
            )
        if triage.is_duplicate:
            top = triage.matches[0]
            return ServiceResult(
                ok=False, data={"triage": triage.model_dump()},
                hint=f"Likely duplicate of {top.key} (similarity {top.similarity_score}). "
                     f"Comment on or link {top.key} instead of creating a new issue.",
            )
        created = client.create_issue(
            project_key=args.project_key, summary=args.summary, description_text=args.description,
            issue_type=args.issue_type, parent_key=args.parent_key,
        )
        return {"key": created.key, "id": created.id, "similar": [m.model_dump() for m in triage.matches]}
    return _run("create_jira_issue", CreateIssueInput, {
        "summary": summary, "description": description, "project_key": project_key,
        "issue_type": issue_type, "parent_key": parent_key,
    }, action)


@mcp.tool()
def move_jira_issue_status(issue_key: str, target_status: str) -> dict:
    """
    Transition a Jira issue to a different board column and leave an audit comment.

    Args:
        issue_key: The issue key (e.g. 'KAN-4')
        target_status: Target status ('To Do', 'In Progress', 'Done' or an exact status name)
    """
    def action(args: MoveStatusInput, client: JiraCloudClient):
        return client.move_status(args.issue_key, args.target_status)
    return _run("move_jira_issue_status", MoveStatusInput,
                {"issue_key": issue_key, "target_status": target_status}, action)


@mcp.tool()
def check_duplicate_issues(summary: str, project_key: str = "KAN") -> dict:
    """
    Pre-creation triage: checks for existing duplicate or similar Jira issues.
    Returns TRIAGE_UNAVAILABLE (never CREATE_NEW) if the search itself fails.

    Args:
        summary: The prospective issue title to check
        project_key: Project key (e.g. 'KAN')
    """
    def action(args: DuplicateCheckInput, client: JiraCloudClient):
        triage = client.find_similar_issues(args.summary, args.project_key)
        return ServiceResult(ok=triage.recommendation != "TRIAGE_UNAVAILABLE", data=triage.model_dump(),
                             hint=triage.error)
    return _run("check_duplicate_issues", DuplicateCheckInput,
                {"summary": summary, "project_key": project_key}, action)


@mcp.tool()
def get_required_fields_meta(project_key: str = "KAN", issue_type: str = "Task") -> dict:
    """
    Lists the required fields for creating an issue type (current createmeta endpoints, cached 10 min),
    to prevent 400 Bad Request schema errors.

    Args:
        project_key: Project key (e.g. 'KAN')
        issue_type: Target issue type ('Task', 'Epic', 'Bug')
    """
    def action(args: CreateMetaInput, client: JiraCloudClient):
        return client.get_createmeta_fields(args.project_key, args.issue_type).model_dump()
    return _run("get_required_fields_meta", CreateMetaInput,
                {"project_key": project_key, "issue_type": issue_type}, action)


@mcp.tool()
def link_jira_issues(inward_key: str, outward_key: str, link_type: str = "Blocks") -> dict:
    """
    Creates a dependency link between two Jira issues.
    For 'Blocks', inward_key is the blocker: the result reads "inward_key blocks outward_key".

    Args:
        inward_key: Inward issue key — the blocker for 'Blocks' (e.g. 'KAN-2')
        outward_key: Outward issue key — the blocked issue for 'Blocks' (e.g. 'KAN-3')
        link_type: 'Blocks', 'Relates' or 'Duplicate'
    """
    def action(args: LinkInput, client: JiraCloudClient):
        return client.link_issues(args.inward_key, args.outward_key, args.link_type).model_dump()
    return _run("link_jira_issues", LinkInput,
                {"inward_key": inward_key, "outward_key": outward_key, "link_type": link_type}, action)


@mcp.tool()
def request_restricted_operation(operation: str, arguments: Optional[Dict[str, Any]] = None) -> dict:
    """
    Use when the user asks for something no other tool does (e.g. delete an issue, bulk edit,
    delete a project). Nothing is executed: Tier 3 returns a staged proposal for human approval,
    Tier 4 and unknown operations return a refusal with an escalation link.

    Args:
        operation: snake_case operation name (e.g. 'delete_issue', 'delete_project')
        arguments: The arguments the user asked for, recorded in the proposal
    """
    try:
        args = RestrictedOperationInput(operation=operation, arguments=arguments or {})
    except ValidationError as exc:
        return ServiceResult(ok=False, error=JiraErrorResponse(errorMessages=["Invalid tool arguments"],
                                                               status_code=422),
                             hint=format_validation_hint(exc)).model_dump(mode="json")
    decision = route(args.operation, args.arguments)
    if decision.action in (Action.ALLOW, Action.ALLOW_WITH_PREFLIGHT):
        hint = f"'{args.operation}' has a dedicated tool — call it directly."
    else:
        hint = decision.reason
    return ServiceResult(ok=False, tier=decision.tier.value, data=decision.proposal, hint=hint).model_dump(mode="json")


if __name__ == "__main__":
    mcp.run()
