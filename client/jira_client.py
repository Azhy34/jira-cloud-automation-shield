"""
Production-grade Jira Cloud REST API v3 Client with Zero-Leak Guarantees.
Features modern /search/jql pagination, transition handling, ADF payload generation,
and integrated structured tracing via JiraTracer.
"""

import os
import base64
import requests
from typing import Dict, Any, List, Optional
from shields.jira_shield import JiraIssue, JiraSearchResponse, JiraMutationResponse
from shields.tracer import JiraTracer

class JiraCloudClient:
    def __init__(self, url: str, email: str, token: str):
        self.url = url.rstrip("/")
        self.email = email
        self._auth_header = self._build_auth_header(email, token)

    @classmethod
    def from_env(cls) -> "JiraCloudClient":
        url = os.getenv("JIRA_URL", "").rstrip("/")
        email = os.getenv("JIRA_EMAIL", "").strip()
        token = os.getenv("JIRA_API_TOKEN", "").strip()
        if not url or not email or not token:
            raise ValueError("Missing JIRA_URL, JIRA_EMAIL, or JIRA_API_TOKEN in environment.")
        return cls(url, email, token)

    def _build_auth_header(self, email: str, token: str) -> str:
        b64 = base64.b64encode(f"{email}:{token}".encode()).decode()
        return f"Basic {b64}"

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": self._auth_header,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def verify_credentials(self) -> Dict[str, Any]:
        """Handshake check via /rest/api/3/myself with tracing."""
        trace = JiraTracer.start_trace("verify_credentials", "/rest/api/3/myself")
        try:
            resp = requests.get(f"{self.url}/rest/api/3/myself", headers=self._headers(), timeout=10)
            JiraTracer.end_trace(trace, resp.status_code)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            JiraTracer.end_trace(trace, 500, error=str(e))
            raise

    def search_issues_jql(self, jql: str, max_results: int = 50) -> JiraSearchResponse:
        """
        Queries issues via modern /rest/api/3/search/jql endpoint with tracing.
        Automatically requests necessary field projections.
        """
        trace = JiraTracer.start_trace("search_issues_jql", "/rest/api/3/search/jql")
        params = {
            "jql": jql,
            "fields": "summary,status,issuetype,parent,description",
            "maxResults": max_results
        }
        try:
            resp = requests.get(f"{self.url}/rest/api/3/search/jql", headers=self._headers(), params=params, timeout=15)
            JiraTracer.end_trace(trace, resp.status_code)
            resp.raise_for_status()
            return JiraSearchResponse.model_validate(resp.json())
        except Exception as e:
            JiraTracer.end_trace(trace, 500, error=str(e))
            raise

    def create_issue(
        self,
        project_key: str,
        summary: str,
        description_text: str,
        issue_type: str = "Task",
        parent_key: Optional[str] = None
    ) -> JiraMutationResponse:
        """Creates an issue using standard Atlassian Document Format (ADF) with tracing."""
        trace = JiraTracer.start_trace("create_issue", "/rest/api/3/issue")
        payload: Dict[str, Any] = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description_text}]
                        }
                    ]
                },
                "issuetype": {"name": issue_type}
            }
        }
        if parent_key:
            payload["fields"]["parent"] = {"key": parent_key}

        try:
            resp = requests.post(f"{self.url}/rest/api/3/issue", headers=self._headers(), json=payload, timeout=15)
            created_key = resp.json().get("key") if resp.status_code == 201 else None
            JiraTracer.end_trace(trace, resp.status_code, resource_key=created_key)
            resp.raise_for_status()
            return JiraMutationResponse.model_validate(resp.json())
        except Exception as e:
            JiraTracer.end_trace(trace, 500, error=str(e))
            raise

    def get_transitions(self, issue_key: str) -> List[Dict[str, Any]]:
        """Returns possible status transitions for a work item."""
        resp = requests.get(f"{self.url}/rest/api/3/issue/{issue_key}/transitions", headers=self._headers(), timeout=10)
        resp.raise_for_status()
        return resp.json().get("transitions", [])

    def move_status(self, issue_key: str, target_status: str, add_comment: bool = True) -> bool:
        """Transitions an issue across board columns with tracing and audit trailing."""
        trace = JiraTracer.start_trace("move_status", f"/rest/api/3/issue/{issue_key}/transitions")
        transitions = self.get_transitions(issue_key)
        matched_id = None
        target_lower = target_status.lower()
        for t in transitions:
            t_name = t.get("name", "").lower()
            to_name = t.get("to", {}).get("name", "").lower()
            to_cat = (t.get("to", {}).get("statusCategory", {}).get("key") or "").lower()

            if (target_lower in t_name or target_lower in to_name or 
                (target_lower == "done" and to_cat == "done") or
                (target_lower in ["in progress", "progress"] and to_cat == "indeterminate") or
                (target_lower in ["to do", "todo"] and to_cat in ["new", "undefined"])):
                matched_id = t["id"]
                break

        if not matched_id:
            JiraTracer.end_trace(trace, 400, resource_key=issue_key, error=f"Target status '{target_status}' not reachable")
            raise ValueError(f"No transition found for target status '{target_status}'.")

        try:
            resp = requests.post(
                f"{self.url}/rest/api/3/issue/{issue_key}/transitions",
                headers=self._headers(),
                json={"transition": {"id": matched_id}},
                timeout=10
            )
            JiraTracer.end_trace(trace, resp.status_code, resource_key=issue_key)
            
            # Add audit trail comment to Jira issue
            if resp.status_code == 204 and add_comment:
                self.add_audit_comment(
                    issue_key=issue_key,
                    comment_text=f"🤖 [AI Audit] Transitioned to '{target_status}' via IDE Controller. Trace ID: {trace['trace_id']}"
                )
            return resp.status_code == 204
        except Exception as e:
            JiraTracer.end_trace(trace, 500, resource_key=issue_key, error=str(e))
            raise

    def add_audit_comment(self, issue_key: str, comment_text: str) -> None:
        """Appends an automated audit trail comment to the Jira work item."""
        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": comment_text}]
                    }
                ]
            }
        }
        try:
            requests.post(
                f"{self.url}/rest/api/3/issue/{issue_key}/comment",
                headers=self._headers(),
                json=payload,
                timeout=10
            )
        except Exception:
            pass  # Non-blocking audit comment
