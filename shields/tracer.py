"""
Zero-Dependency Structured Tracer & Observability Logger for Jira Operations.
Provides unique trace_ids, SLA latency timing, and zero-leak structured JSON output.
"""

import time
import uuid
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Ensure logs directory exists
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
trace_log_file = log_dir / "jira_trace.log"

logger = logging.getLogger("jira_tracer")
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = logging.FileHandler(trace_log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(file_handler)

class JiraTracer:
    @staticmethod
    def start_trace(operation: str, endpoint: str) -> Dict[str, Any]:
        """Initializes a trace context."""
        return {
            "trace_id": f"trc-{uuid.uuid4().hex[:8]}",
            "operation": operation,
            "endpoint": endpoint,
            "start_time": time.time(),
            "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

    @staticmethod
    def end_trace(
        context: Dict[str, Any],
        status_code: int,
        resource_key: Optional[str] = None,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calculates latency, records trace entry to log, and returns summary."""
        latency_ms = round((time.time() - context["start_time"]) * 1000, 2)
        log_entry = {
            "timestamp": context["timestamp_iso"],
            "trace_id": context["trace_id"],
            "operation": context["operation"],
            "endpoint": context["endpoint"],
            "status_code": status_code,
            "latency_ms": latency_ms,
            "resource_key": resource_key,
            "success": 200 <= status_code < 300,
            "error": error
        }
        logger.info(json.dumps(log_entry))
        return log_entry
