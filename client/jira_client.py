"""
Production-grade Jira Cloud REST API v3 client.
HTTPS only, GET retries that honour Retry-After, exactly one structured trace per HTTP call,
enhanced /search/jql pagination, fail-closed duplicate triage and the non-deprecated
createmeta endpoints with a short-lived cache.
"""

import os
import re
import time
import base64
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from shields.jira_shield import (
    JiraSearchResponse, JiraMutationResponse, JiraErrorResponse, JiraComment,
    JiraDuplicateCheckResult, JiraDuplicateMatch,
    JiraCreateMetaResponse, JiraCreateMetaField,
    JiraIssueLinkResponse
)
from shields.tracer import JiraTracer

SEARCH_FIELDS = "summary,status,issuetype,parent,description,resolution"
CREATEMETA_TTL_SECONDS = 600
DUPLICATE_THRESHOLD = 0.75
SIMILAR_THRESHOLD = 0.40
PROJECT_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,9}$")
REVIEW_STATUS_RE = re.compile(r"review|проверк|\bqa\b", re.IGNORECASE)
STOPWORDS = {"the", "and", "for", "with", "from", "step", "task"}
CATEGORY_BY_TARGET = {
    "to do": "new", "todo": "new",
    "in progress": "indeterminate", "progress": "indeterminate",
    "done": "done",
}


class JiraApiError(Exception):
    """A failed Jira call, already traced, with a parsed error body and an optional fix-it hint."""

    def __init__(self, error: JiraErrorResponse, trace_id: Optional[str] = None, hint: Optional[str] = None):
        self.error = error
        self.trace_id = trace_id
        self.hint = hint
        super().__init__(f"Jira API error {error.status_code}: {'; '.join(error.errorMessages) or error.errors}")

    @property
    def status_code(self) -> int:
        return self.error.status_code


def _adf_to_text(node: Any) -> str:
    """Flattens an Atlassian Document Format node into plain text."""
    if not isinstance(node, dict):
        return ""
    text = node.get("text", "") + "".join(_adf_to_text(child) for child in node.get("content", []))
    if node.get("type") in {"paragraph", "heading", "listItem", "codeBlock"}:
        text += "\n"
    return text


def _parse_error(resp: requests.Response) -> JiraErrorResponse:
    try:
        body = resp.json()
        return JiraErrorResponse(
            errorMessages=body.get("errorMessages", []),
            errors=body.get("errors", {}),
            status_code=resp.status_code,
        )
    except ValueError:
        return JiraErrorResponse(errorMessages=[resp.text[:300]], status_code=resp.status_code)


class JiraCloudClient:
    def __init__(self, url: str, email: str, token: str, timeout: int = 15):
        url = url.rstrip("/")
        if not url.startswith("https://"):
            raise ValueError("JIRA_URL must use https://")
        self.url = url
        self.email = email
        self.timeout = timeout
        self.last_trace_id: Optional[str] = None
        self._auth_header = self._build_auth_header(email, token)
        self._createmeta_cache: Dict[Tuple[str, str], Tuple[float, JiraCreateMetaResponse]] = {}

        self.session = requests.Session()
        self.session.headers.update(self._headers())
        # Retry only idempotent reads: retrying a POST could create a duplicate issue
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=(429, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

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

    def _request(self, method: str, path: str, operation: str,
                 resource_key: Optional[str] = None, **kwargs) -> requests.Response:
        """Sends one request and writes exactly one trace entry, whatever the outcome."""
        trace = JiraTracer.start_trace(operation, path)
        self.last_trace_id = trace["trace_id"]
        try:
            resp = self.session.request(method, f"{self.url}{path}", timeout=self.timeout, **kwargs)
        except requests.RequestException as exc:
            JiraTracer.end_trace(trace, 0, resource_key=resource_key, error=type(exc).__name__)
            raise JiraApiError(
                JiraErrorResponse(errorMessages=[f"{type(exc).__name__}: {exc}"], status_code=0),
                trace_id=trace["trace_id"],
            ) from exc

        error = None if resp.ok else _parse_error(resp)
        JiraTracer.end_trace(
            trace, resp.status_code, resource_key=resource_key,
            error="; ".join(error.errorMessages) or str(error.errors) if error else None,
        )
        if error:
            raise JiraApiError(error, trace_id=trace["trace_id"])
        return resp

    def verify_credentials(self) -> Dict[str, Any]:
        """Handshake check via /rest/api/3/myself."""
        return self._request("GET", "/rest/api/3/myself", "verify_credentials").json()

    def search_issues_jql(self, jql: str, max_results: int = 50, fields: str = SEARCH_FIELDS,
                          page_size: int = 100) -> JiraSearchResponse:
        """
        Queries issues via the enhanced /rest/api/3/search/jql endpoint,
        following nextPageToken until max_results issues are collected.
        """
        issues = []
        token: Optional[str] = None
        is_last = True
        while len(issues) < max_results:
            params: Dict[str, Any] = {"jql": jql, "fields": fields,
                                      "maxResults": min(page_size, max_results - len(issues))}
            if token:
                params["nextPageToken"] = token
            page = JiraSearchResponse.model_validate(
                self._request("GET", "/rest/api/3/search/jql", "search_issues_jql", params=params).json()
            )
            issues.extend(page.issues)
            token = page.nextPageToken
            is_last = bool(page.isLast) or not token
            if is_last or not page.issues:
                break
        return JiraSearchResponse(issues=issues[:max_results], isLast=is_last, nextPageToken=None if is_last else token)

    def get_issue_comments(self, issue_key: str, max_results: int = 50) -> List[JiraComment]:
        """Returns issue comments as plain text — bug fixes usually live there."""
        data = self._request(
            "GET", f"/rest/api/3/issue/{issue_key}/comment", "get_issue_comments",
            resource_key=issue_key, params={"maxResults": max_results, "orderBy": "created"},
        ).json()
        return [
            JiraComment(
                id=c["id"],
                author=(c.get("author") or {}).get("displayName"),
                created=c.get("created"),
                text=_adf_to_text(c.get("body")).strip(),
            )
            for c in data.get("comments", [])
        ]

    def create_issue(
        self,
        project_key: str,
        summary: str,
        description_text: str,
        issue_type: str = "Task",
        parent_key: Optional[str] = None
    ) -> JiraMutationResponse:
        """Creates an issue with an ADF description. On 400 the error carries the project's required fields."""
        payload: Dict[str, Any] = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": description_text or " "}]}]
                },
                "issuetype": {"name": issue_type}
            }
        }
        if parent_key:
            payload["fields"]["parent"] = {"key": parent_key}

        try:
            resp = self._request("POST", "/rest/api/3/issue", "create_issue", json=payload)
        except JiraApiError as exc:
            if exc.status_code == 400:
                exc.hint = self._required_fields_hint(project_key, issue_type)
            raise
        return JiraMutationResponse.model_validate(resp.json())

    def _required_fields_hint(self, project_key: str, issue_type: str) -> str:
        try:
            meta = self.get_createmeta_fields(project_key, issue_type)
        except (JiraApiError, ValueError) as exc:
            return f"Jira rejected the payload; required fields could not be loaded ({exc})."
        names = [f"{f.name} ({f.field_id})" for f in meta.required_fields]
        return "Jira rejected the payload. Required fields for this issue type: " + (", ".join(names) or "none reported")

    def get_transitions(self, issue_key: str) -> List[Dict[str, Any]]:
        """Returns possible status transitions for a work item."""
        return self._request(
            "GET", f"/rest/api/3/issue/{issue_key}/transitions", "get_transitions", resource_key=issue_key
        ).json().get("transitions", [])

    def move_status(self, issue_key: str, target_status: str, add_comment: bool = True) -> Dict[str, Any]:
        """
        Transitions an issue. Matching order: exact transition or status name, then status category.
        For "In Progress" a review-like status (e.g. "In Review", "На проверке") is never picked.
        """
        transitions = self.get_transitions(issue_key)
        chosen = self._pick_transition(transitions, target_status)
        if not chosen:
            available = ", ".join(t.get("to", {}).get("name", "?") for t in transitions)
            raise ValueError(f"No transition to '{target_status}' for {issue_key}. Available: {available}")

        self._request(
            "POST", f"/rest/api/3/issue/{issue_key}/transitions", "move_status",
            resource_key=issue_key, json={"transition": {"id": chosen["id"]}},
        )
        trace_id = self.last_trace_id
        audit_saved = None
        if add_comment:
            audit_saved = self.add_audit_comment(
                issue_key, f"🤖 [AI Audit] Transitioned to '{chosen['to']['name']}' via Jira Shield. Trace ID: {trace_id}"
            )
        return {"issue_key": issue_key, "to": chosen["to"]["name"], "trace_id": trace_id, "audit_comment_saved": audit_saved}

    @staticmethod
    def _pick_transition(transitions: List[Dict[str, Any]], target_status: str) -> Optional[Dict[str, Any]]:
        target = target_status.strip().lower()
        for t in transitions:
            if target in (t.get("name", "").lower(), t.get("to", {}).get("name", "").lower()):
                return t
        category = CATEGORY_BY_TARGET.get(target)
        if not category:
            return None
        candidates = [t for t in transitions if (t.get("to", {}).get("statusCategory") or {}).get("key") == category]
        if category == "indeterminate":
            candidates = [t for t in candidates if not REVIEW_STATUS_RE.search(t["to"].get("name", ""))] or candidates
        return candidates[0] if candidates else None

    def add_audit_comment(self, issue_key: str, comment_text: str) -> bool:
        """Appends an audit trail comment. Returns False (and the failure is traced) instead of hiding it."""
        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": comment_text}]}]
            }
        }
        try:
            self._request("POST", f"/rest/api/3/issue/{issue_key}/comment", "add_audit_comment",
                          resource_key=issue_key, json=payload)
            return True
        except JiraApiError:
            return False

    def find_similar_issues(
        self,
        summary: str,
        project_key: str = "KAN",
        lookback_days: int = 90
    ) -> JiraDuplicateCheckResult:
        """
        Atlassian triage pattern: search before create. Fail-closed — if the search itself fails,
        the result is TRIAGE_UNAVAILABLE, never CREATE_NEW.
        """
        if not PROJECT_KEY_RE.match(project_key):
            raise ValueError(f"Invalid project key: {project_key!r}")

        terms = self._triage_terms(summary)
        search_term = " ".join(terms)
        base = f'project = "{project_key}" AND created >= -{lookback_days}d'
        # Jira text search needs every word to match: try all terms first, then any term as a wider net.
        # Ranking by summary similarity below keeps the wide net precise.
        queries = [f'{base} AND summary ~ "{search_term}"',
                   f'{base} AND (' + " OR ".join(f'summary ~ "{t}"' for t in terms) + ")"] if terms else [base]

        try:
            candidates = []
            for jql in queries:
                candidates = self.search_issues_jql(jql, max_results=20).issues
                if candidates:
                    break
        except JiraApiError as exc:
            return JiraDuplicateCheckResult(
                is_duplicate=False, query=search_term, recommendation="TRIAGE_UNAVAILABLE", error=str(exc)
            )

        target = summary.strip().lower()
        matches: List[JiraDuplicateMatch] = []
        for issue in candidates:
            candidate = issue.fields.summary.strip()
            score = SequenceMatcher(None, target, candidate.lower()).ratio()
            if target in candidate.lower() or candidate.lower() in target:
                score = max(score, 0.85)
            if score >= SIMILAR_THRESHOLD:
                matches.append(JiraDuplicateMatch(
                    key=issue.key, summary=candidate, status=issue.fields.status.name,
                    similarity_score=round(score, 2), url=f"{self.url}/browse/{issue.key}",
                ))

        matches.sort(key=lambda m: m.similarity_score, reverse=True)
        is_duplicate = any(m.similarity_score >= DUPLICATE_THRESHOLD for m in matches)
        recommendation = "LINK_DUPLICATE" if is_duplicate else ("INVESTIGATE_SIMILAR" if matches else "CREATE_NEW")
        return JiraDuplicateCheckResult(
            is_duplicate=is_duplicate, query=search_term, matches=matches, recommendation=recommendation
        )

    @staticmethod
    def _triage_terms(summary: str) -> List[str]:
        """
        Distinctive search words. Ticket prefixes like "[INT-103]" and tokens with digits are dropped:
        Jira indexes "INT-103" as one token, so "INT" and "103" would make an all-words search miss.
        Only word characters reach JQL, so quotes or operators in a summary cannot alter the query.
        """
        text = re.sub(r"\[[^\]]*\]", " ", summary)
        words = [w for w in re.findall(r"\b\w{3,}\b", text)
                 if w.lower() not in STOPWORDS and not any(ch.isdigit() for ch in w)]
        return list(dict.fromkeys(words))[:5]

    def get_createmeta_fields(self, project_key: str = "KAN", issue_type: str = "Task") -> JiraCreateMetaResponse:
        """
        Required fields for an issue type via the current createmeta endpoints
        (the legacy GET /rest/api/3/issue/createmeta is deprecated). Cached for 10 minutes.
        """
        cache_key = (project_key, issue_type.lower())
        cached = self._createmeta_cache.get(cache_key)
        if cached and time.monotonic() - cached[0] < CREATEMETA_TTL_SECONDS:
            return cached[1]

        types = self._request(
            "GET", f"/rest/api/3/issue/createmeta/{project_key}/issuetypes", "get_createmeta_issuetypes",
            resource_key=project_key,
        ).json()
        issue_types = types.get("issueTypes") or types.get("values") or []
        match = next((it for it in issue_types if it.get("name", "").lower() == issue_type.lower()), None)
        if not match:
            names = ", ".join(it.get("name", "?") for it in issue_types)
            raise ValueError(f"Issue type '{issue_type}' not found in {project_key}. Available: {names}")

        meta = self._request(
            "GET", f"/rest/api/3/issue/createmeta/{project_key}/issuetypes/{match['id']}",
            "get_createmeta_fields", resource_key=project_key, params={"maxResults": 200},
        ).json()
        fields = meta.get("fields") or meta.get("results") or meta.get("values") or []
        required = [
            JiraCreateMetaField(
                field_id=f.get("fieldId") or f.get("key", "?"),
                name=f.get("name", "?"),
                required=True,
                schema_type=(f.get("schema") or {}).get("type"),
                allowed_values=[
                    str(v.get("value") or v.get("name")) for v in f.get("allowedValues", []) if isinstance(v, dict)
                ] or None,
            )
            for f in fields if f.get("required")
        ]
        result = JiraCreateMetaResponse(project_key=project_key, issue_type=match.get("name", issue_type),
                                        required_fields=required)
        self._createmeta_cache[cache_key] = (time.monotonic(), result)
        return result

    def link_issues(self, inward_key: str, outward_key: str, link_type: str = "Blocks") -> JiraIssueLinkResponse:
        """
        Creates an issueLink. Verified on Jira Cloud: for "Blocks", inward_key is shown as
        "blocks" outward_key (inward = the blocker).
        """
        self._request(
            "POST", "/rest/api/3/issueLink", "link_issues", resource_key=f"{inward_key}->{outward_key}",
            json={"type": {"name": link_type}, "inwardIssue": {"key": inward_key}, "outwardIssue": {"key": outward_key}},
        )
        return JiraIssueLinkResponse(success=True, inward_key=inward_key, outward_key=outward_key, link_type=link_type)
