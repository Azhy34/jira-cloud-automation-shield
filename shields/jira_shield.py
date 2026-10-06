"""
Two-Layer Resilient Pydantic Error Shield for Jira Cloud REST API v3.
Provides zero-leak data modeling, contract validation, and fallback mechanisms.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class JiraStatus(BaseModel):
    name: str = Field(..., description="Status name, e.g. To Do, In Progress, Done")
    id: Optional[str] = None

class JiraIssueType(BaseModel):
    name: str = Field(..., description="Issue type name, e.g. Epic, Task, Story, Bug")
    subtask: bool = False

class JiraParentRef(BaseModel):
    key: str = Field(..., description="Parent issue key, e.g. KAN-1")
    id: Optional[str] = None

class JiraIssueFields(BaseModel):
    summary: str
    status: JiraStatus
    issuetype: JiraIssueType
    parent: Optional[JiraParentRef] = None
    description: Optional[Dict[str, Any]] = None

class JiraIssue(BaseModel):
    id: str
    key: str
    fields: JiraIssueFields

class JiraSearchResponse(BaseModel):
    total: Optional[int] = None
    maxResults: Optional[int] = None
    issues: List[JiraIssue] = Field(default_factory=list)

class JiraMutationResponse(BaseModel):
    id: str
    key: str
    self_url: Optional[str] = Field(None, alias="self")

class JiraErrorResponse(BaseModel):
    errorMessages: List[str] = Field(default_factory=list)
    errors: Dict[str, str] = Field(default_factory=dict)
    status_code: int = 400
