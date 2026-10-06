"""
MCP tool pipeline tests: Tier Router, Layer 1 input guard, mandatory duplicate check,
fail-closed creation and the ServiceResult envelope (tools never raise).
"""

import asyncio

import pytest
import requests_mock

from client.jira_client import JiraCloudClient
from conftest import BASE, issue
from mcp_server import jira_mcp
from shields.tier_router import Action, Tier, route

SEARCH = f"{BASE}/rest/api/3/search/jql"
CREATE = f"{BASE}/rest/api/3/issue"


@pytest.fixture(autouse=True)
def test_client(monkeypatch):
    monkeypatch.setattr(jira_mcp, "get_client", lambda: JiraCloudClient(BASE, "bot@example.com", "test-token"))


def test_seven_tools_are_registered():
    names = {t.name for t in asyncio.run(jira_mcp.mcp.list_tools())}
    assert names == {
        "search_jira_issues", "create_jira_issue", "move_jira_issue_status", "check_duplicate_issues",
        "get_required_fields_meta", "link_jira_issues", "request_restricted_operation",
    }


@pytest.mark.parametrize("operation, tier, action", [
    ("search_jira_issues", Tier.T1_READ, Action.ALLOW),
    ("create_jira_issue", Tier.T2_GUARDED, Action.ALLOW_WITH_PREFLIGHT),
    ("delete_issue", Tier.T3_HITL, Action.STAGE_FOR_APPROVAL),
    ("delete_project", Tier.T4_FORBIDDEN, Action.REJECT),
    ("drop_everything", Tier.T4_FORBIDDEN, Action.REJECT),  # unknown = denied by default
])
def test_tier_router(operation, tier, action):
    decision = route(operation)
    assert (decision.tier, decision.action) == (tier, action)


def test_layer1_rejects_bad_project_key_without_network():
    with requests_mock.Mocker() as m:
        result = jira_mcp.create_jira_issue(summary="Valid summary", description="", project_key="kan; DROP")
    assert result["ok"] is False and result["error"]["status_code"] == 422
    assert "project_key" in result["hint"]
    assert m.call_count == 0


def test_layer1_rejects_multiline_summary_without_network():
    with requests_mock.Mocker() as m:
        result = jira_mcp.create_jira_issue(summary="line one\nline two", description="")
    assert result["ok"] is False and "single line" in result["hint"]
    assert m.call_count == 0


def test_create_blocks_duplicate_and_never_posts():
    with requests_mock.Mocker() as m:
        m.get(SEARCH, json={"issues": [issue("KAN-18", "Configure Cloud Tasks queue")], "isLast": True})
        m.post(CREATE, status_code=201, json={"id": "1", "key": "KAN-99"})
        result = jira_mcp.create_jira_issue(summary="Configure Cloud Tasks queue", description="")

    assert result["ok"] is False and "KAN-18" in result["hint"]
    assert result["data"]["triage"]["recommendation"] == "LINK_DUPLICATE"
    assert not any(r.method == "POST" for r in m.request_history)
    assert result["tier"] == "T2_GUARDED_MUTATION" and result["trace_id"].startswith("trc-")


def test_create_is_blocked_when_triage_is_unavailable():
    with requests_mock.Mocker() as m:
        m.get(SEARCH, status_code=503, json={"errorMessages": ["Service unavailable"]})
        m.post(CREATE, status_code=201, json={"id": "1", "key": "KAN-99"})
        result = jira_mcp.create_jira_issue(summary="Brand new work item", description="")

    assert result["ok"] is False and "fail-closed" in result["hint"]
    assert not any(r.method == "POST" for r in m.request_history)


def test_create_succeeds_when_no_duplicates():
    with requests_mock.Mocker() as m:
        m.get(SEARCH, json={"issues": [], "isLast": True})
        m.post(CREATE, status_code=201, json={"id": "10099", "key": "KAN-99", "self": f"{BASE}/rest/api/3/issue/10099"})
        result = jira_mcp.create_jira_issue(summary="Brand new work item", description="details")

    assert result["ok"] is True and result["data"]["key"] == "KAN-99"


def test_restricted_operation_tier3_returns_staged_proposal():
    result = jira_mcp.request_restricted_operation("delete_issue", {"issue_key": "KAN-4"})
    assert result["ok"] is False and result["tier"] == "T3_HUMAN_APPROVAL"
    assert result["data"]["status"] == "PENDING_HUMAN_APPROVAL"
    assert result["data"]["arguments"] == {"issue_key": "KAN-4"}


def test_restricted_operation_tier4_is_refused_with_escalation_link():
    result = jira_mcp.request_restricted_operation("delete_project", {"project_key": "KAN"})
    assert result["ok"] is False and result["tier"] == "T4_FORBIDDEN"
    assert "admin.atlassian.com" in result["hint"]


def test_tools_never_raise_on_missing_credentials(monkeypatch):
    monkeypatch.setattr(jira_mcp, "get_client", lambda: JiraCloudClient.from_env())
    for var in ("JIRA_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"):
        monkeypatch.delenv(var, raising=False)
    result = jira_mcp.search_jira_issues("project = KAN")
    assert result["ok"] is False and "Missing JIRA_URL" in result["error"]["errorMessages"][0]
