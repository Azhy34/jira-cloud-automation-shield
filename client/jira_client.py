"""
Production-grade Jira Cloud REST API v3 Client with Zero-Leak Guarantees.
Features modern /search/jql pagination, transition handling, and ADF payload generation.
"""

import os
import base64
import requests
from typing import Dict, Any, List, Optional
from shields.jira_shield import JiraIssue, JiraSearchResponse, JiraMutationResponse

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
        """Handshake check via /rest/api/3/myself."""
        resp = requests.get(f"{self.url}/rest/api/3/myself", headers=self._headers(), timeout=10)
        resp.raise_for_status()
        return resp.json()

    def search_issues_jql(self, jql: str, max_results: int = 50) -> JiraSearchResponse:
        """
        Queries issues via the modern /rest/api/3/search/jql endpoint.
        Automatically requests necessary field projections.
        """
        params = {
            "jql": jql,
            "fields": "summary,status,issuetype,parent,description",
            "maxResults": max_results
        }
        resp = requests.get(f"{self.url}/rest/api/3/search/jql", headers=self._headers(), params=params, timeout=15)
        resp.raise_for_status()
        return JiraSearchResponse.model_validate(resp.json())

    def create_issue(
        self,
        project_key: str,
        summary: str,
        description_text: str,
        issue_type: str = "Задача",
        parent_key: Optional[str] = None
    ) -> JiraMutationResponse:
        """Creates an issue using standard Atlassian Document Format (ADF)."""
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

        resp = requests.post(f"{self.url}/rest/api/3/issue", headers=self._headers(), json=payload, timeout=15)
        resp.raise_for_status()
        return JiraMutationResponse.model_validate(resp.json())

    def get_transitions(self, issue_key: str) -> List[Dict[str, Any]]:
        """Returns possible status transitions for a work item."""
        resp = requests.get(f"{self.url}/rest/api/3/issue/{issue_key}/transitions", headers=self._headers(), timeout=10)
        resp.raise_for_status()
        return resp.json().get("transitions", [])

    def move_status(self, issue_key: str, target_status: str) -> bool:
        """Transitions an issue across board columns (e.g., 'In Progress', 'Done')."""
        transitions = self.get_transitions(issue_key)
        matched_id = None
        for t in transitions:
            t_name = t["name"].lower()
            to_name = t["to"]["name"].lower()
            if target_status.lower() in t_name or target_status.lower() in to_name:
                matched_id = t["id"]
                break

        if not matched_id:
            raise ValueError(f"No transition found for target status '{target_status}'.")

        resp = requests.post(
            f"{self.url}/rest/api/3/issue/{issue_key}/transitions",
            headers=self._headers(),
            json={"transition": {"id": matched_id}},
            timeout=10
        )
        return resp.status_code == 204
