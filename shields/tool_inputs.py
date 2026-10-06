"""
Layer 1: inbound argument guard for agent tools.
Every MCP tool validates its raw arguments here before any network call,
so a malformed key or an oversized summary never reaches Jira.
"""

from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field, ValidationError, field_validator

PROJECT_KEY_PATTERN = r"^[A-Z][A-Z0-9_]{1,9}$"
ISSUE_KEY_PATTERN = r"^[A-Z][A-Z0-9_]{1,9}-\d+$"


class SearchInput(BaseModel):
    jql: str = Field(..., min_length=1, max_length=2000)
    max_results: int = Field(20, ge=1, le=50)


class CreateIssueInput(BaseModel):
    summary: str = Field(..., min_length=3, max_length=255)
    description: str = Field("", max_length=32000)
    project_key: str = Field("KAN", pattern=PROJECT_KEY_PATTERN)
    issue_type: str = Field("Task", min_length=1, max_length=50)
    parent_key: Optional[str] = Field(None, pattern=ISSUE_KEY_PATTERN)

    @field_validator("summary")
    @classmethod
    def summary_is_single_line(cls, value: str) -> str:
        if "\n" in value or "\r" in value:
            raise ValueError("summary must be a single line")
        return value.strip()


class MoveStatusInput(BaseModel):
    issue_key: str = Field(..., pattern=ISSUE_KEY_PATTERN)
    target_status: str = Field(..., min_length=1, max_length=50)


class DuplicateCheckInput(BaseModel):
    summary: str = Field(..., min_length=3, max_length=255)
    project_key: str = Field("KAN", pattern=PROJECT_KEY_PATTERN)


class CreateMetaInput(BaseModel):
    project_key: str = Field("KAN", pattern=PROJECT_KEY_PATTERN)
    issue_type: str = Field("Task", min_length=1, max_length=50)


class LinkInput(BaseModel):
    inward_key: str = Field(..., pattern=ISSUE_KEY_PATTERN)
    outward_key: str = Field(..., pattern=ISSUE_KEY_PATTERN)
    link_type: Literal["Blocks", "Relates", "Duplicate"] = "Blocks"


class RestrictedOperationInput(BaseModel):
    operation: str = Field(..., pattern=r"^[a-z][a-z_]{2,59}$")
    arguments: Dict[str, Any] = Field(default_factory=dict)


def format_validation_hint(err: ValidationError) -> str:
    """Turns a Pydantic error into a short self-correction hint for the calling agent."""
    problems = [f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in err.errors()]
    return "Fix the arguments and call the tool again — " + "; ".join(problems)
