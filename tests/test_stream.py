"""
Tests for backend/routers/stream.py (SSE endpoint) and queue management
in backend/services/job_runner.py.
"""
import asyncio
import json
from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.models import Job

_FAKE_MAPPING = "PPD: p-Phenylenediamine\n"
with patch("pathlib.Path.read_text", return_value=_FAKE_MAPPING):
    from backend.main import app

TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=TEST_ENGINE)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.create_all(TEST_ENGINE)
    # sse-starlette's AppStatus binds its asyncio.Event to the first event loop
    # that calls wait() — reset it before each test so it rebinds cleanly.
    try:
        from sse_starlette.sse import AppStatus
        AppStatus.should_exit = False
        AppStatus.should_exit_event = asyncio.Event()
    except (ImportError, AttributeError):
        pass
    yield
    Base.metadata.drop_all(TEST_ENGINE)


@pytest.fixture()
def client():
    _prev = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    with patch("fastapi.staticfiles.StaticFiles.__init__", return_value=None):
        yield TestClient(app, raise_server_exceptions=True)
    if _prev is not None:
        app.dependency_overrides[get_db] = _prev
    else:
        app.dependency_overrides.pop(get_db, None)


def _seed_job(
    status="running",
    url_count=2,
    in_scope=0,
    excluded=0,
) -> str:
    db = TestingSessionLocal()
    job_id = str(uuid4())
    now = datetime.utcnow()
    job = Job(
        id=job_id,
        status=status,
        url_count=url_count,
        processed=url_count if status in ("complete", "failed") else 0,
        in_scope=in_scope,
        excluded=excluded,
        errors=0,
        created_at=now,
        started_at=now if status != "queued" else None,
        completed_at=now if status in ("complete", "failed") else None,
    )
    db.add(job)
    db.commit()
    db.close()
    return job_id


# ---------------------------------------------------------------------------
# Queue management unit tests
# ---------------------------------------------------------------------------

class TestQueueManagement:
    def setup_method(self):
        from backend.services import job_runner
        job_runner._job_queues.clear()

    def teardown_method(self):
        from backend.services import job_runner
        job_runner._job_queues.clear()

    def test_register_queue_creates_and_tracks_queue(self):
        from backend.services.job_runner import register_queue, _job_queues
        job_id = "q-test-1"
        q = register_queue(job_id)
        assert q in _job_queues[job_id]
        assert len(_job_queues[job_id]) == 1

    def test_register_multiple_queues_for_same_job(self):
        from backend.services.job_runner import register_queue, _job_queues
        job_id = "q-test-2"
        q1 = register_queue(job_id)
        q2 = register_queue(job_id)
        assert len(_job_queues[job_id]) == 2
        assert q1 in _job_queues[job_id]
        assert q2 in _job_queues[job_id]

    def test_unregister_queue_removes_it(self):
        from backend.services.job_runner import register_queue, unregister_queue, _job_queues
        job_id = "q-test-3"
        q = register_queue(job_id)
        unregister_queue(job_id, q)
        assert q not in _job_queues[job_id]

    def test_unregister_nonexistent_queue_is_safe(self):
        from backend.services.job_runner import unregister_queue, register_queue, _job_queues
        job_id = "q-test-4"
        q = register_queue(job_id)
        unregister_queue(job_id, q)
        unregister_queue(job_id, q)  # second call should not raise

    def test_publish_delivers_event_to_all_queues(self):
        from backend.services.job_runner import register_queue, _publish
        job_id = "q-test-5"
        q1 = register_queue(job_id)
        q2 = register_queue(job_id)
        event = {"type": "product_done", "name": "Test"}
        asyncio.run(_publish(job_id, event))
        assert not q1.empty()
        assert not q2.empty()
        assert asyncio.run(q1.get()) == event
        assert asyncio.run(q2.get()) == event

    def test_publish_to_unknown_job_is_safe(self):
        from backend.services.job_runner import _publish
        asyncio.run(_publish("no-such-job", {"type": "ping"}))  # no exception


# ---------------------------------------------------------------------------
# SSE stream endpoint tests
# ---------------------------------------------------------------------------

class TestStreamEndpoint:
    def test_404_for_unknown_job(self, client):
        resp = client.get(f"/api/jobs/{uuid4()}/stream")
        assert resp.status_code == 404

    def test_already_complete_sends_job_complete_immediately(self, client):
        job_id = _seed_job(status="complete", in_scope=2, excluded=1)
        with client.stream("GET", f"/api/jobs/{job_id}/stream") as resp:
            assert resp.status_code == 200
            body = resp.read().decode()

        assert "job_complete" in body
        # Verify SSE data line contains valid JSON with expected fields
        data_lines = [ln for ln in body.splitlines() if ln.startswith("data:")]
        assert data_lines, "No data lines in SSE response"
        payload = json.loads(data_lines[0].removeprefix("data:").strip())
        assert payload["type"] == "job_complete"
        assert "stats" in payload
        assert payload["stats"]["in_scope"] == 2
        assert payload["stats"]["excluded"] == 1

    def test_already_failed_sends_job_complete_immediately(self, client):
        job_id = _seed_job(status="failed")
        with client.stream("GET", f"/api/jobs/{job_id}/stream") as resp:
            assert resp.status_code == 200
            body = resp.read().decode()

        assert "job_complete" in body

    def test_live_stream_delivers_product_done_then_job_complete(self, client):
        job_id = _seed_job(status="running", url_count=1)

        q: asyncio.Queue = asyncio.Queue()
        product_event = {
            "type": "product_done",
            "name": "Excellence",
            "in_scope": True,
            "progress": {"done": 1, "total": 1},
        }
        complete_event = {
            "type": "job_complete",
            "stats": {"in_scope": 1, "excluded": 0, "duration_sec": 2.3},
        }
        q.put_nowait(product_event)
        q.put_nowait(complete_event)

        with (
            patch("backend.routers.stream.register_queue", return_value=q),
            patch("backend.routers.stream.unregister_queue"),
        ):
            with client.stream("GET", f"/api/jobs/{job_id}/stream") as resp:
                assert resp.status_code == 200
                body = resp.read().decode()

        assert "product_done" in body
        assert "job_complete" in body

    def test_live_stream_delivers_error_event(self, client):
        job_id = _seed_job(status="running")

        q: asyncio.Queue = asyncio.Queue()
        q.put_nowait({"type": "error", "url": "https://bad.com", "message": "timeout"})
        q.put_nowait({"type": "job_complete", "stats": {"in_scope": 0, "excluded": 0, "duration_sec": 0.5}})

        with (
            patch("backend.routers.stream.register_queue", return_value=q),
            patch("backend.routers.stream.unregister_queue"),
        ):
            with client.stream("GET", f"/api/jobs/{job_id}/stream") as resp:
                body = resp.read().decode()

        assert "error" in body
        assert "timeout" in body

    def test_live_stream_calls_unregister_on_completion(self, client):
        job_id = _seed_job(status="running")

        q: asyncio.Queue = asyncio.Queue()
        q.put_nowait({"type": "job_complete", "stats": {"in_scope": 0, "excluded": 0, "duration_sec": 0.1}})

        with (
            patch("backend.routers.stream.register_queue", return_value=q) as mock_reg,
            patch("backend.routers.stream.unregister_queue") as mock_unreg,
        ):
            with client.stream("GET", f"/api/jobs/{job_id}/stream") as resp:
                resp.read()

        mock_reg.assert_called_once_with(job_id)
        mock_unreg.assert_called_once_with(job_id, q)
