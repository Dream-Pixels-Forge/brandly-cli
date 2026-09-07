"""Webhook server for CI/CD integration with brandly-cli."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

# Pydantic models for request/response
try:
    from pydantic import BaseModel
except ImportError:  # pragma: no cover
    class BaseModel:  # type: ignore
        pass


class GenerateJobRequest(BaseModel):
    """Request body for generating a new video."""
    project_name: str
    product_idea: str
    style: str = "cinematic"
    shots: int = 5
    budget: int = 500
    platforms: list[str] = ["tiktok"]


class JobResponse(BaseModel):
    """Response for job creation."""
    project_id: str
    status: str
    message: str


# In-memory job storage (for webhook server)
_job_store: dict[str, dict[str, Any]] = {}


def get_job(job_id: str) -> dict[str, Any] | None:
    """Get job by ID."""
    return _job_store.get(job_id)


def create_job(payload: GenerateJobRequest) -> JobResponse:
    """Create a new video generation job."""
    job_id = f"job-{uuid.uuid4().hex[:8]}"
    timestamp = datetime.now(timezone.utc).isoformat()

    job = {
        "project_id": job_id,
        "project_name": payload.project_name,
        "product_idea": payload.product_idea,
        "style": payload.style,
        "shots": payload.shots,
        "budget": payload.budget,
        "platforms": payload.platforms,
        "status": "pending",
        "created_at": timestamp,
        "updated_at": timestamp,
    }

    _job_store[job_id] = job
    return JobResponse(
        project_id=job_id,
        status="pending",
        message=f"Job created: {payload.product_idea[:50]}",
    )


def cancel_job(job_id: str) -> dict[str, Any]:
    """Cancel a pending job."""
    if job_id not in _job_store:
        return {"error": "Job not found"}

    job = _job_store[job_id]
    if job["status"] == "pending":
        job["status"] = "cancelled"
        job["updated_at"] = datetime.now(timezone.utc).isoformat()
        return {"message": "Job cancelled", "job_id": job_id}
    else:
        return {"error": f"Cannot cancel job in status: {job['status']}"}


def list_jobs() -> list[dict[str, Any]]:
    """List all jobs."""
    return list(_job_store.values())
