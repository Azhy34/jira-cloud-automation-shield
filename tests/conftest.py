"""Shared test setup: no network, no real credentials, trace log in a temp dir."""

import os
import sys
import tempfile
from pathlib import Path

# Must run before shields.tracer is imported
os.environ["JIRA_TRACE_LOG_DIR"] = tempfile.mkdtemp(prefix="jira_trace_")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json

import pytest

BASE = "https://example.atlassian.net"


@pytest.fixture
def client():
    from client.jira_client import JiraCloudClient
    return JiraCloudClient(BASE, "bot@example.com", "test-token")


@pytest.fixture
def traces():
    """Returns a function that lists the JSON trace entries written to the trace file during the test."""
    from shields.tracer import trace_log_file, logger
    start = trace_log_file.stat().st_size if trace_log_file.exists() else 0

    def _entries():
        for handler in logger.handlers:
            handler.flush()
        with open(trace_log_file, encoding="utf-8") as f:
            f.seek(start)
            return [json.loads(line) for line in f if line.strip()]
    return _entries


def issue(key: str, summary: str, status: str = "To Do", category: str = "new") -> dict:
    return {
        "id": key.split("-")[1],
        "key": key,
        "fields": {
            "summary": summary,
            "status": {"name": status, "statusCategory": {"key": category}},
            "issuetype": {"name": "Task"},
        },
    }
