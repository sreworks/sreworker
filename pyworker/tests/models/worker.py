"""Tests for Worker Pydantic models."""

import json
import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models.worker import CreateWorkerRequest, WorkerResponse, WORKER_NAME_PATTERN


class TestCreateWorkerRequest:
    """SUT: CreateWorkerRequest"""

    def test_valid_name_alpha(self):
        """Pure alphabetic name should be valid."""
        req = CreateWorkerRequest(name="worker")
        assert req.name == "worker"

    def test_valid_name_with_hyphen_underscore_digit(self):
        """Name with hyphens, underscores and digits should be valid."""
        req = CreateWorkerRequest(name="my-worker_1")
        assert req.name == "my-worker_1"

    def test_invalid_name_starts_with_digit(self):
        """Name starting with digit should be rejected."""
        with pytest.raises(ValidationError):
            CreateWorkerRequest(name="1worker")

    def test_invalid_name_space(self):
        """Name with space should be rejected."""
        with pytest.raises(ValidationError):
            CreateWorkerRequest(name="my worker")

    def test_invalid_name_special_char(self):
        """Name with special char should be rejected."""
        with pytest.raises(ValidationError):
            CreateWorkerRequest(name="worker@")

    def test_invalid_name_empty(self):
        """Empty name should be rejected."""
        with pytest.raises(ValidationError):
            CreateWorkerRequest(name="")

    def test_name_max_length(self):
        """64 chars should be valid, 65 chars should be invalid."""
        valid_name = "a" * 64
        req = CreateWorkerRequest(name=valid_name)
        assert req.name == valid_name

        with pytest.raises(ValidationError):
            CreateWorkerRequest(name="a" * 65)


class TestWorkerResponse:
    """SUT: WorkerResponse"""

    def test_datetime_encoding(self):
        """WorkerResponse should encode datetime in JSON."""
        resp = WorkerResponse(
            name="w1", type="claudecode",
            env_vars={}, command_params=[],
            created_at=datetime(2025, 6, 15, 10, 0, 0)
        )
        data = json.loads(resp.model_dump_json())
        assert "2025" in data["created_at"]
