"""
Model Context Protocol (MCP) Server for Jira Cloud Automation Shield.
Exposes tools for LLM Agents (Google ADK, Claude, Cursor) to manage Jira issues safely.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure root directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

load_dotenv(".env")
load_dotenv(".env.jira")
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env.jira")

from mcp.server.fastmcp import FastMCP
from client.jira_client import JiraCloudClient

# Initialize FastMCP Server
mcp = FastMCP("jira-automation-shield")

def get_client() -> JiraCloudClient:
    return JiraCloudClient.from_env()

@mcp.tool()
def search_jira_issues(jql: str, max_results: int = 20) -> list:
    """
    Search Jira issues using Jira Query Language (JQL) via the modern /search/jql API.
    
    Args:
        jql: JQL query string (e.g., 'project = KAN AND status != Done')
        max_results: Maximum number of issues to return
    """
    client = get_client()
    resp = client.search_issues_jql(jql, max_results=max_results)
    results = []
    for issue in resp.issues:
        results.append({
            "key": issue.key,
            "summary": issue.fields.summary,
            "status": issue.fields.status.name,
            "type": issue.fields.issuetype.name,
            "parent": issue.fields.parent.key if issue.fields.parent else None
        })
    return results

@mcp.tool()
def create_jira_issue(
    summary: str,
    description: str,
    project_key: str = "KAN",
    issue_type: str = "Task",
    parent_key: str = None
) -> dict:
    """
    Create a new issue or subtask in Jira with Atlassian Document Format (ADF) description.
    
    Args:
        summary: Title of the issue
        description: Description of the work item
        project_key: Key of the project (e.g. 'KAN')
        issue_type: Type of issue ('Task', 'Epic', 'Bug')
        parent_key: Optional parent Epic key to attach to (e.g. 'KAN-1')
    """
    client = get_client()
    resp = client.create_issue(
        project_key=project_key,
        summary=summary,
        description_text=description,
        issue_type=issue_type,
        parent_key=parent_key
    )
    return {"key": resp.key, "id": resp.id}

@mcp.tool()
def move_jira_issue_status(issue_key: str, target_status: str) -> str:
    """
    Transition a Jira issue to a different Kanban board column.
    
    Args:
        issue_key: The issue key (e.g. 'KAN-4')
        target_status: Target status ('To Do', 'In Progress', 'Done')
    """
    client = get_client()
    client.move_status(issue_key, target_status)
    return f"Issue {issue_key} successfully transitioned to {target_status}"

@mcp.tool()
def check_duplicate_issues(summary: str, project_key: str = "KAN") -> dict:
    """
    Pre-creation triage tool: Checks for existing duplicate or similar Jira issues 
    before creating a new work item (prevents duplicate tickets).
    
    Args:
        summary: The prospective issue title to check
        project_key: Project key (e.g. 'KAN')
    """
    client = get_client()
    result = client.find_similar_issues(summary, project_key)
    return result.model_dump()

@mcp.tool()
def get_required_fields_meta(project_key: str = "KAN", issue_type: str = "Task") -> dict:
    """
    Introspects Jira issue creation metadata (createmeta) to identify required enterprise fields 
    and prevent 400 Bad Request schema violation errors.
    
    Args:
        project_key: Project key (e.g. 'KAN')
        issue_type: Target issue type ('Task', 'Epic', 'Bug')
    """
    client = get_client()
    result = client.get_createmeta_fields(project_key, issue_type)
    return result.model_dump()

@mcp.tool()
def link_jira_issues(inward_key: str, outward_key: str, link_type: str = "Blocks") -> str:
    """
    Creates a semantic dependency link between two Jira issues (e.g., Blocks, Relates, Duplicate).
    
    Args:
        inward_key: Inward issue key (e.g. 'KAN-2')
        outward_key: Outward issue key (e.g. 'KAN-3')
        link_type: Link relationship type ('Blocks', 'Relates', 'Duplicate')
    """
    client = get_client()
    res = client.link_issues(inward_key, outward_key, link_type)
    return f"Linked {inward_key} to {outward_key} via '{link_type}' (success: {res.success})"

if __name__ == "__main__":
    mcp.run()
