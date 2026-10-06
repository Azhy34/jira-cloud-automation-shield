"""
Two-Layer Resilient Pydantic Error Shield for Jira Cloud REST API v3.
Provides zero-leak data modeling, contract validation, and fallback mechanisms.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class JiraStatusCategory(BaseModel):
    key: Optional[str] = None
    name: Optional[str] = None

class JiraStatus(BaseModel):
    name: str = Field(..., description="Status display name")
    id: Optional[str] = None
    statusCategory: Optional[JiraStatusCategory] = None

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

# Architectural Hardening Models (Atlassian Official Skills Alignment)
class JiraDuplicateMatch(BaseModel):
    key: str
    summary: str
    status: str
    similarity_score: float = Field(..., description="Estimated match confidence 0.0 - 1.0")
    url: Optional[str] = None

class JiraDuplicateCheckResult(BaseModel):
    is_duplicate: bool
    query: str
    matches: List[JiraDuplicateMatch] = Field(default_factory=list)
    recommendation: str = Field(..., description="Actionable advice: CREATE_NEW, LINK_DUPLICATE, or COMMENT_EXISTING")

class JiraCreateMetaField(BaseModel):
    field_id: str
    name: str
    required: bool
    schema_type: Optional[str] = None
    allowed_values: Optional[List[str]] = None

class JiraCreateMetaResponse(BaseModel):
    project_key: str
    issue_type: str
    required_fields: List[JiraCreateMetaField] = Field(default_factory=list)

class JiraIssueLinkResponse(BaseModel):
    success: bool
    inward_key: str
    outward_key: str
    link_type: str

