"""
Automated unit tests for Jira Two-Layer Pydantic Error Shield.
Validates robust contract parsing and resilient error boundaries.
"""

import pytest
from shields.jira_shield import (
    JiraIssue,
    JiraSearchResponse,
    JiraStatus,
    JiraStatusCategory,
    JiraIssueType,
    JiraMutationResponse,
    JiraErrorResponse
)

def test_jira_issue_validation():
    payload = {
        "id": "10001",
        "key": "KAN-1",
        "fields": {
            "summary": "Implement Jira MCP Gateway",
            "status": {
                "name": "To Do",
                "id": "1",
                "statusCategory": {"key": "new", "name": "To Do"}
            },
            "issuetype": {"name": "Epic", "subtask": False},
            "parent": None,
            "description": None
        }
    }
    issue = JiraIssue.model_validate(payload)
    assert issue.key == "KAN-1"
    assert issue.fields.status.statusCategory.key == "new"
    assert issue.fields.issuetype.subtask is False

def test_jira_search_response_empty():
    payload = {"total": 0, "maxResults": 50, "issues": []}
    res = JiraSearchResponse.model_validate(payload)
    assert len(res.issues) == 0

def test_jira_mutation_response():
    payload = {"id": "10050", "key": "KAN-50", "self": "https://jira.example.com/rest/api/3/issue/10050"}
    res = JiraMutationResponse.model_validate(payload)
    assert res.key == "KAN-50"
    assert res.id == "10050"

def test_jira_error_response():
    payload = {
        "errorMessages": ["The requested API has been removed. Migrate to /rest/api/3/search/jql"],
        "errors": {"field": "Invalid parameter"}
    }
    err = JiraErrorResponse.model_validate(payload)
    assert len(err.errorMessages) == 1
    assert "field" in err.errors
