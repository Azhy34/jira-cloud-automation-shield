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

def test_jira_duplicate_check_result():
    from shields.jira_shield import JiraDuplicateCheckResult, JiraDuplicateMatch
    match = JiraDuplicateMatch(
        key="KAN-4",
        summary="API Probing & Breaking Changes Detection",
        status="Done",
        similarity_score=0.92,
        url="https://example.atlassian.net/browse/KAN-4"
    )
    result = JiraDuplicateCheckResult(
        is_duplicate=True,
        query="API Probing Breaking Changes",
        matches=[match],
        recommendation="LINK_DUPLICATE"
    )
    assert result.is_duplicate is True
    assert len(result.matches) == 1
    assert result.matches[0].similarity_score == 0.92

def test_jira_createmeta_response():
    from shields.jira_shield import JiraCreateMetaResponse, JiraCreateMetaField
    field = JiraCreateMetaField(
        field_id="customfield_10021",
        name="Severity",
        required=True,
        schema_type="string",
        allowed_values=["Critical", "Major", "Minor"]
    )
    meta = JiraCreateMetaResponse(
        project_key="KAN",
        issue_type="Bug",
        required_fields=[field]
    )
    assert meta.project_key == "KAN"
    assert len(meta.required_fields) == 1
    assert meta.required_fields[0].required is True

def test_jira_issue_link_response():
    from shields.jira_shield import JiraIssueLinkResponse
    link = JiraIssueLinkResponse(
        success=True,
        inward_key="KAN-2",
        outward_key="KAN-3",
        link_type="Blocks"
    )
    assert link.success is True
    assert link.link_type == "Blocks"

