import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.models.analysis_job import JobStatus


FAKE_PHOTO = b"\xff\xd8\xff\xe0" + b"\x00" * 100  # minimal JPEG magic bytes


def test_submit_analysis_returns_202(client, admin_headers):
    """POST /analyze creates a pending job and returns job_id."""
    with patch(
        "app.api.v1.endpoints.analyze.process_job",
        new_callable=AsyncMock,
    ):
        response = client.post(
            "/api/v1/analyze",
            files={"photo": ("face.jpg", FAKE_PHOTO, "image/jpeg")},
            headers=admin_headers,
        )

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == JobStatus.pending
    # job_id must be a valid UUID
    uuid.UUID(data["job_id"])


def test_submit_analysis_requires_api_key(client):
    response = client.post(
        "/api/v1/analyze",
        files={"photo": ("face.jpg", FAKE_PHOTO, "image/jpeg")},
    )
    assert response.status_code == 403


def test_submit_analysis_rejects_wrong_content_type(client, admin_headers):
    response = client.post(
        "/api/v1/analyze",
        files={"photo": ("doc.pdf", b"%PDF", "application/pdf")},
        headers=admin_headers,
    )
    assert response.status_code == 415


def test_submit_analysis_rejects_oversized_photo(client, admin_headers):
    big = b"\xff\xd8\xff\xe0" + b"\x00" * (11 * 1024 * 1024)
    with patch(
        "app.api.v1.endpoints.analyze.process_job",
        new_callable=AsyncMock,
    ):
        response = client.post(
            "/api/v1/analyze",
            files={"photo": ("big.jpg", big, "image/jpeg")},
            headers=admin_headers,
        )
    assert response.status_code == 413


def test_get_job_returns_pending(client, admin_headers):
    """After submission, polling the job returns the current status."""
    with patch(
        "app.api.v1.endpoints.analyze.process_job",
        new_callable=AsyncMock,
    ):
        post = client.post(
            "/api/v1/analyze",
            files={"photo": ("face.jpg", FAKE_PHOTO, "image/jpeg")},
            headers=admin_headers,
        )
    job_id = post.json()["job_id"]

    get = client.get(f"/api/v1/analyze/{job_id}", headers=admin_headers)
    assert get.status_code == 200
    data = get.json()
    assert data["job_id"] == job_id
    assert data["status"] == JobStatus.pending
    assert data["result"] is None
    assert data["error_message"] is None


def test_get_job_404_for_unknown(client, admin_headers):
    response = client.get(
        f"/api/v1/analyze/{uuid.uuid4()}", headers=admin_headers
    )
    assert response.status_code == 404


def test_get_job_requires_api_key(client, admin_headers):
    with patch(
        "app.api.v1.endpoints.analyze.process_job",
        new_callable=AsyncMock,
    ):
        post = client.post(
            "/api/v1/analyze",
            files={"photo": ("face.jpg", FAKE_PHOTO, "image/jpeg")},
            headers=admin_headers,
        )
    job_id = post.json()["job_id"]

    response = client.get(f"/api/v1/analyze/{job_id}")
    assert response.status_code == 403
