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

if __name__ == "__main__":
    mcp.run()
