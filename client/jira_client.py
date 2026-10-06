"""
Production-grade Jira Cloud REST API v3 Client with Zero-Leak Guarantees.
Features modern /search/jql pagination, transition handling, ADF payload generation,
and integrated structured tracing via JiraTracer.
"""

import os
import base64
import requests
from typing import Dict, Any, List, Optional
from shields.jira_shield import (
    JiraIssue, JiraSearchResponse, JiraMutationResponse,
    JiraDuplicateCheckResult, JiraDuplicateMatch,
    JiraCreateMetaResponse, JiraCreateMetaField,
    JiraIssueLinkResponse
)
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

    def find_similar_issues(
        self,
        summary: str,
        project_key: str = "KAN",
        lookback_days: int = 90
    ) -> JiraDuplicateCheckResult:
        """
        Extracts key tokens from prospective summary, searches for similar issues via JQL,
        and computes similarity confidence scores (Atlassian Triage Pattern).
        """
        trace = JiraTracer.start_trace("find_similar_issues", "/rest/api/3/search/jql")
        import re
        from difflib import SequenceMatcher

        # Extract meaningful alphanumeric tokens
        tokens = [w for w in re.findall(r"\b\w{3,}\b", summary) if w.lower() not in {"the", "and", "for", "with", "from", "step", "task"}]
        search_term = " ".join(tokens[:5]) if tokens else summary

        jql = f'project = "{project_key}" AND created >= -{lookback_days}d'
        if search_term:
            jql += f' AND text ~ "{search_term}"'

        matches: List[JiraDuplicateMatch] = []
        try:
            resp = self.search_issues_jql(jql, max_results=10)
            target_norm = summary.strip().lower()
            for issue in resp.issues:
                cand_summary = issue.fields.summary.strip()
                cand_norm = cand_summary.lower()
                sim = SequenceMatcher(None, target_norm, cand_norm).ratio()
                
                # Boost if direct substring
                if target_norm in cand_norm or cand_norm in target_norm:
                    sim = max(sim, 0.85)

                if sim >= 0.40:
                    matches.append(
                        JiraDuplicateMatch(
                            key=issue.key,
                            summary=cand_summary,
                            status=issue.fields.status.name,
                            similarity_score=round(sim, 2),
                            url=f"{self.url}/browse/{issue.key}"
                        )
                    )

            matches.sort(key=lambda m: m.similarity_score, reverse=True)
            is_dup = any(m.similarity_score >= 0.75 for m in matches)
            rec = "LINK_DUPLICATE" if is_dup else ("INVESTIGATE_SIMILAR" if matches else "CREATE_NEW")

            result = JiraDuplicateCheckResult(
                is_duplicate=is_dup,
                query=search_term,
                matches=matches,
                recommendation=rec
            )
            JiraTracer.end_trace(trace, 200, resource_key=f"matches={len(matches)}")
            return result
        except Exception as e:
            JiraTracer.end_trace(trace, 500, error=str(e))
            return JiraDuplicateCheckResult(
                is_duplicate=False,
                query=search_term,
                matches=[],
                recommendation="CREATE_NEW"
            )

    def get_createmeta_fields(
        self,
        project_key: str = "KAN",
        issue_type: str = "Task"
    ) -> JiraCreateMetaResponse:
        """
        Introspects project creation schema to detect required enterprise fields (CreateMeta Pattern).
        """
        trace = JiraTracer.start_trace("get_createmeta_fields", f"/rest/api/3/issue/createmeta")
        try:
            resp = requests.get(
                f"{self.url}/rest/api/3/issue/createmeta",
                headers=self._headers(),
                params={"projectKeys": project_key, "expand": "projects.issuetypes.fields"},
                timeout=10
            )
            JiraTracer.end_trace(trace, resp.status_code)
            resp.raise_for_status()
            data = resp.json()

            projects = data.get("projects", [])
            req_fields: List[JiraCreateMetaField] = []
            target_proj = next((p for p in projects if p.get("key") == project_key), None)
            if target_proj:
                issue_types = target_proj.get("issuetypes", [])
                target_it = next((it for it in issue_types if it.get("name", "").lower() == issue_type.lower()), None)
                if target_it:
                    fields = target_it.get("fields", {})
                    for fid, finfo in fields.items():
                        if finfo.get("required"):
                            allowed = [str(v.get("value") or v.get("name")) for v in finfo.get("allowedValues", []) if isinstance(v, dict)]
                            req_fields.append(
                                JiraCreateMetaField(
                                    field_id=fid,
                                    name=finfo.get("name", fid),
                                    required=True,
                                    schema_type=finfo.get("schema", {}).get("type"),
                                    allowed_values=allowed or None
                                )
                            )

            return JiraCreateMetaResponse(
                project_key=project_key,
                issue_type=issue_type,
                required_fields=req_fields
            )
        except Exception as e:
            JiraTracer.end_trace(trace, 500, error=str(e))
            raise

    def link_issues(
        self,
        inward_key: str,
        outward_key: str,
        link_type: str = "Blocks"
    ) -> JiraIssueLinkResponse:
        """
        Creates semantic issueLink relationship between issues (Atlassian Dependency Pattern).
        """
        trace = JiraTracer.start_trace("link_issues", "/rest/api/3/issueLink")
        payload = {
            "type": {"name": link_type},
            "inwardIssue": {"key": inward_key},
            "outwardIssue": {"key": outward_key}
        }
        try:
            resp = requests.post(
                f"{self.url}/rest/api/3/issueLink",
                headers=self._headers(),
                json=payload,
                timeout=10
            )
            JiraTracer.end_trace(trace, resp.status_code, resource_key=f"{inward_key}->{outward_key}")
            success = resp.status_code in {200, 201}
            return JiraIssueLinkResponse(
                success=success,
                inward_key=inward_key,
                outward_key=outward_key,
                link_type=link_type
            )
        except Exception as e:
            JiraTracer.end_trace(trace, 500, error=str(e))
            raise

