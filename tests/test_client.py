"""
Client behaviour tests with mocked HTTP (requests-mock): pagination, tracing,
fail-closed triage, createmeta migration, error hints and status transitions.
"""

import pytest
import requests
import requests_mock

from client.jira_client import JiraCloudClient, JiraApiError
from conftest import BASE, issue

SEARCH = f"{BASE}/rest/api/3/search/jql"


def test_https_is_required():
    with pytest.raises(ValueError, match="https"):
        JiraCloudClient("http://example.atlassian.net", "bot@example.com", "t")


def test_search_follows_next_page_token_and_requests_resolution(client):
    with requests_mock.Mocker() as m:
        m.get(SEARCH, [
            {"json": {"issues": [issue("KAN-1", "a"), issue("KAN-2", "b")], "nextPageToken": "p2", "isLast": False}},
            {"json": {"issues": [issue("KAN-3", "c"), issue("KAN-4", "d")], "isLast": True}},
        ])
        resp = client.search_issues_jql("project = KAN", max_results=3)

    assert [i.key for i in resp.issues] == ["KAN-1", "KAN-2", "KAN-3"]
    assert m.request_history[1].qs["nextpagetoken"] == ["p2"]
    assert "resolution" in m.request_history[0].qs["fields"][0]


def test_http_error_writes_exactly_one_trace_with_real_status(client, traces):
    with requests_mock.Mocker() as m:
        m.get(SEARCH, status_code=400, json={"errorMessages": ["Bad JQL"]})
        with pytest.raises(JiraApiError) as exc:
            client.search_issues_jql("project = KAN")

    assert exc.value.status_code == 400
    entries = [e for e in traces() if e["operation"] == "search_issues_jql"]
    assert len(entries) == 1
    assert entries[0]["status_code"] == 400 and entries[0]["error"] == "Bad JQL"


def test_network_error_is_traced_as_status_zero(client, traces):
    with requests_mock.Mocker() as m:
        m.get(SEARCH, exc=requests.ConnectionError)
        with pytest.raises(JiraApiError) as exc:
            client.search_issues_jql("project = KAN")

    assert exc.value.status_code == 0
    entries = [e for e in traces() if e["operation"] == "search_issues_jql"]
    assert len(entries) == 1 and entries[0]["status_code"] == 0


def test_triage_is_fail_closed_when_search_fails(client):
    with requests_mock.Mocker() as m:
        m.get(SEARCH, status_code=503, json={"errorMessages": ["Service unavailable"]})
        result = client.find_similar_issues("Configure Cloud Tasks queue")

    assert result.recommendation == "TRIAGE_UNAVAILABLE"
    assert result.error


def test_triage_detects_duplicate(client):
    with requests_mock.Mocker() as m:
        m.get(SEARCH, json={"issues": [issue("KAN-18", "Configure Cloud Tasks queue")], "isLast": True})
        result = client.find_similar_issues("Configure Cloud Tasks queue")

    assert result.is_duplicate and result.recommendation == "LINK_DUPLICATE"
    assert result.matches[0].key == "KAN-18"


def test_triage_terms_drop_ticket_prefix_and_digit_tokens():
    # Jira indexes "INT-103" as one token: "INT" and "103" would make the all-words search miss
    summary = "[INT-103] Step 3: API Probing & Breaking Changes Detection (/search/jql)"
    assert JiraCloudClient._triage_terms(summary) == ["API", "Probing", "Breaking", "Changes", "Detection"]


def test_triage_falls_back_to_any_term_when_all_terms_miss(client):
    with requests_mock.Mocker() as m:
        m.get(SEARCH, [
            {"json": {"issues": [], "isLast": True}},
            {"json": {"issues": [issue("KAN-4", "API Probing & Breaking Changes Detection")], "isLast": True}},
        ])
        result = client.find_similar_issues("API Probing & Breaking Changes Detection again")

    assert 'summary ~ "api probing breaking changes detection"' in m.request_history[0].qs["jql"][0]
    assert " or " in m.request_history[1].qs["jql"][0]
    assert result.is_duplicate and result.matches[0].key == "KAN-4"


def test_triage_rejects_injected_project_key_before_any_request(client):
    with requests_mock.Mocker() as m:
        with pytest.raises(ValueError):
            client.find_similar_issues("anything", 'KAN" OR project is not EMPTY OR project = "X')
    assert m.call_count == 0


def test_triage_never_puts_raw_summary_into_jql(client):
    with requests_mock.Mocker() as m:
        m.get(SEARCH, json={"issues": [], "isLast": True})
        client.find_similar_issues('"" OR x')
    assert '"" or' not in m.request_history[0].qs["jql"][0]


def _mock_createmeta(m, required_name="Severity"):
    m.get(f"{BASE}/rest/api/3/issue/createmeta/KAN/issuetypes",
          json={"issueTypes": [{"id": "10005", "name": "Task"}, {"id": "10008", "name": "Bug"}]})
    m.get(f"{BASE}/rest/api/3/issue/createmeta/KAN/issuetypes/10008", json={"fields": [
        {"fieldId": "summary", "name": "Summary", "required": True, "schema": {"type": "string"}},
        {"fieldId": "customfield_10021", "name": required_name, "required": True,
         "schema": {"type": "option"}, "allowedValues": [{"value": "Critical"}, {"value": "Minor"}]},
        {"fieldId": "labels", "name": "Labels", "required": False},
    ]})


def test_createmeta_uses_current_endpoints_and_caches(client):
    with requests_mock.Mocker() as m:
        _mock_createmeta(m)
        first = client.get_createmeta_fields("KAN", "Bug")
        calls = m.call_count
        second = client.get_createmeta_fields("KAN", "bug")

    assert [f.field_id for f in first.required_fields] == ["summary", "customfield_10021"]
    assert first.required_fields[1].allowed_values == ["Critical", "Minor"]
    assert second == first and m.call_count == calls  # served from cache
    assert all("projectKeys" not in r.url for r in m.request_history)  # legacy endpoint never called


def test_create_issue_400_hint_lists_required_fields(client):
    with requests_mock.Mocker() as m:
        m.post(f"{BASE}/rest/api/3/issue", status_code=400, json={"errors": {"customfield_10021": "required"}})
        _mock_createmeta(m)
        with pytest.raises(JiraApiError) as exc:
            client.create_issue("KAN", "Login fails", "steps", issue_type="Bug")

    assert "Severity (customfield_10021)" in exc.value.hint


def test_audit_comment_failure_is_reported_not_hidden(client, traces):
    with requests_mock.Mocker() as m:
        m.post(f"{BASE}/rest/api/3/issue/KAN-4/comment", status_code=403, json={"errorMessages": ["No permission"]})
        saved = client.add_audit_comment("KAN-4", "audit")

    assert saved is False
    assert [e["status_code"] for e in traces() if e["operation"] == "add_audit_comment"] == [403]


TRANSITIONS = [
    {"id": "11", "name": "К выполнению", "to": {"name": "К выполнению", "statusCategory": {"key": "new"}}},
    {"id": "31", "name": "На проверке", "to": {"name": "На проверке", "statusCategory": {"key": "indeterminate"}}},
    {"id": "21", "name": "В работе", "to": {"name": "В работе", "statusCategory": {"key": "indeterminate"}}},
    {"id": "41", "name": "Готово", "to": {"name": "Готово", "statusCategory": {"key": "done"}}},
]


@pytest.mark.parametrize("target, expected", [
    ("In Progress", "В работе"),   # review-like status is skipped even though it comes first
    ("Done", "Готово"),
    ("To Do", "К выполнению"),
    ("на проверке", "На проверке"),  # exact name wins
])
def test_pick_transition(target, expected):
    assert JiraCloudClient._pick_transition(TRANSITIONS, target)["to"]["name"] == expected


def test_move_status_transitions_and_reports_audit_result(client):
    with requests_mock.Mocker() as m:
        m.get(f"{BASE}/rest/api/3/issue/KAN-4/transitions", json={"transitions": TRANSITIONS})
        m.post(f"{BASE}/rest/api/3/issue/KAN-4/transitions", status_code=204)
        m.post(f"{BASE}/rest/api/3/issue/KAN-4/comment", status_code=201, json={"id": "1"})
        result = client.move_status("KAN-4", "In Progress")

    assert result["to"] == "В работе" and result["audit_comment_saved"] is True
    assert m.request_history[1].json() == {"transition": {"id": "21"}}


def test_get_issue_comments_returns_plain_text(client):
    body = {"type": "doc", "version": 1, "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "Root cause: auth daemon timeout."}]},
        {"type": "paragraph", "content": [{"type": "text", "text": "Fixed in 2.3.1."}]},
    ]}
    with requests_mock.Mocker() as m:
        m.get(f"{BASE}/rest/api/3/issue/KAN-4/comment",
              json={"comments": [{"id": "9", "author": {"displayName": "Ana"}, "created": "2026-10-06", "body": body}]})
        comments = client.get_issue_comments("KAN-4")

    assert comments[0].author == "Ana"
    assert comments[0].text == "Root cause: auth daemon timeout.\nFixed in 2.3.1."
