"""Tests for webhook module — CI/CD integration."""

from __future__ import annotations

from brandly_cli.webhook import (
    GenerateJobRequest,
    JobResponse,
    cancel_job,
    create_job,
    get_job,
    list_jobs,
)


class TestGenerateJobRequest:
    """Tests for request validation."""

    def test_valid_request(self) -> None:
        """Valid request creates successfully."""
        req = GenerateJobRequest(
            project_name="Test Project",
            product_idea="Cool widget",
        )
        assert req.project_name == "Test Project"
        assert req.style == "cinematic"  # Default
        assert req.platforms == ["tiktok"]  # Default

    def test_custom_fields(self) -> None:
        """Custom fields are accepted."""
        req = GenerateJobRequest(
            project_name="Custom",
            product_idea="Amazing product",
            style="ugc",
            shots=3,
            budget=200,
            platforms=["instagram"],
        )
        assert req.style == "ugc"
        assert req.shots == 3
        assert req.budget == 200
        assert req.platforms == ["instagram"]


class TestJobLifecycle:
    """Tests for job creation and management."""

    def test_create_job(self) -> None:
        """Creating a job returns response with ID."""
        req = GenerateJobRequest(
            project_name="Test",
            product_idea="Test product",
        )
        response = create_job(req)
        assert isinstance(response, JobResponse)
        assert response.project_id.startswith("job-")
        assert response.status == "pending"

    def test_get_job(self) -> None:
        """Can retrieve job by ID after creation."""
        req = GenerateJobRequest(project_name="Test", product_idea="Item")
        response = create_job(req)
        job = get_job(response.project_id)
        assert job is not None
        assert job["project_name"] == "Test"

    def test_get_nonexistent_job(self) -> None:
        """Returns None for unknown job ID."""
        job = get_job("nonexistent-id")
        assert job is None

    def test_list_jobs(self) -> None:
        """Lists all created jobs."""
        create_job(GenerateJobRequest(project_name="A", product_idea="Product A"))
        create_job(GenerateJobRequest(project_name="B", product_idea="Product B"))
        jobs = list_jobs()
        assert len(jobs) >= 2

    def test_cancel_pending_job(self) -> None:
        """Can cancel a pending job."""
        req = GenerateJobRequest(project_name="Test", product_idea="Item")
        response = create_job(req)
        result = cancel_job(response.project_id)
        assert result.get("message") == "Job cancelled"

        job = get_job(response.project_id)
        assert job["status"] == "cancelled"

    def test_cancel_nonexistent_job(self) -> None:
        """Returns error for nonexistent job."""
        result = cancel_job("does-not-exist")
        assert "error" in result
