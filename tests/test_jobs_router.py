"""
Integration tests for backend/routers/jobs.py and routers/results.py

Uses FastAPI TestClient with an in-memory SQLite database injected via
dependency override. The app lifespan is NOT entered (no 'with' on TestClient)
so the production DB path is never touched.
"""
from datetime import datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.models import Ingredient, Job, Product, ProductIngredient

# Patch classifier _load_mapping before importing main (avoids file read at module init)
_FAKE_MAPPING = "PPD: p-Phenylenediamine\n"
with patch("pathlib.Path.read_text", return_value=_FAKE_MAPPING):
    from backend.main import app


# ---------------------------------------------------------------------------
# Test DB — in-memory SQLite
# ---------------------------------------------------------------------------

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


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.create_all(TEST_ENGINE)
    yield
    Base.metadata.drop_all(TEST_ENGINE)


@pytest.fixture()
def client():
    # Do NOT use 'with TestClient(...)' — that starts the lifespan which tries
    # to connect to the Docker-only DB path. Instantiate directly instead.
    with patch("fastapi.staticfiles.StaticFiles.__init__", return_value=None):
        yield TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _seed_job(
    status="queued", url_count=3, processed=0, in_scope=0, excluded=0, errors=0
) -> str:
    db = TestingSessionLocal()
    job_id = str(uuid4())
    job = Job(
        id=job_id,
        status=status,
        url_count=url_count,
        processed=processed,
        in_scope=in_scope,
        excluded=excluded,
        errors=errors,
        created_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.close()
    return job_id


# ---------------------------------------------------------------------------
# POST /api/jobs
# ---------------------------------------------------------------------------

class TestCreateJob:
    def test_returns_job_id(self, client):
        with patch("backend.routers.jobs.run_job", new=AsyncMock()):
            resp = client.post("/api/jobs", json={"urls": ["https://a.com", "https://b.com"]})
        assert resp.status_code == 200
        body = resp.json()
        assert "job_id" in body
        assert len(body["job_id"]) == 36  # UUID

    def test_job_created_in_db(self, client):
        with patch("backend.routers.jobs.run_job", new=AsyncMock()):
            resp = client.post("/api/jobs", json={"urls": ["https://a.com"]})
        job_id = resp.json()["job_id"]

        db = TestingSessionLocal()
        job = db.query(Job).filter(Job.id == job_id).first()
        db.close()
        assert job is not None
        assert job.url_count == 1
        assert job.status == "queued"

    def test_rejects_empty_urls(self, client):
        resp = client.post("/api/jobs", json={"urls": []})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/jobs
# ---------------------------------------------------------------------------

class TestListJobs:
    def test_returns_empty_list_initially(self, client):
        resp = client.get("/api/jobs")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_seeded_job(self, client):
        _seed_job(status="complete", url_count=2, processed=2, in_scope=1, excluded=1)
        resp = client.get("/api/jobs")
        assert resp.status_code == 200
        jobs = resp.json()
        assert len(jobs) == 1
        assert jobs[0]["status"] == "complete"
        assert jobs[0]["url_count"] == 2

    def test_ordered_most_recent_first(self, client):
        db = TestingSessionLocal()
        for i in range(3):
            db.add(
                Job(
                    id=str(uuid4()),
                    status="queued",
                    url_count=1,
                    processed=0,
                    in_scope=0,
                    excluded=0,
                    errors=0,
                    created_at=datetime(2026, 4, 25, i, 0, 0),
                )
            )
        db.commit()
        db.close()

        resp = client.get("/api/jobs")
        jobs = resp.json()
        assert jobs[0]["created_at"] > jobs[1]["created_at"] > jobs[2]["created_at"]


# ---------------------------------------------------------------------------
# GET /api/jobs/{id}
# ---------------------------------------------------------------------------

class TestGetJob:
    def test_returns_job_detail(self, client):
        job_id = _seed_job(status="running", url_count=5, processed=2, in_scope=1)
        resp = client.get(f"/api/jobs/{job_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == job_id
        assert body["status"] == "running"
        assert body["processed"] == 2

    def test_returns_404_for_unknown_id(self, client):
        resp = client.get(f"/api/jobs/{uuid4()}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/jobs/{id}/products
# ---------------------------------------------------------------------------

class TestGetProducts:
    def _seed_product_with_ingredients(self, job_id: str) -> str:
        db = TestingSessionLocal()
        product_id = str(uuid4())
        product = Product(
            id=product_id,
            job_id=job_id,
            url="https://example.com",
            name="Excellence",
            ingredients_raw="PPD, Water",
            in_scope=True,
            scope_reason="dye product",
        )
        db.add(product)
        db.flush()

        ing = Ingredient(
            name="p-Phenylenediamine", internal_name="PPD", count=1, is_dye_active=True
        )
        db.add(ing)
        db.flush()

        pi = ProductIngredient(
            product_id=product_id,
            ingredient_id=ing.id,
            component="OXIDATIVE DYE SYSTEM",
            is_dye_active=True,
        )
        db.add(pi)
        db.commit()
        db.close()
        return product_id

    def test_returns_products_with_ingredients(self, client):
        job_id = _seed_job()
        self._seed_product_with_ingredients(job_id)

        resp = client.get(f"/api/jobs/{job_id}/products")
        assert resp.status_code == 200
        products = resp.json()
        assert len(products) == 1
        assert products[0]["name"] == "Excellence"
        assert len(products[0]["ingredients"]) == 1
        ing = products[0]["ingredients"][0]
        assert ing["name"] == "p-Phenylenediamine"
        assert ing["component"] == "OXIDATIVE DYE SYSTEM"
        assert ing["is_dye_active"] is True

    def test_returns_empty_list_for_job_with_no_products(self, client):
        job_id = _seed_job()
        resp = client.get(f"/api/jobs/{job_id}/products")
        assert resp.status_code == 200
        assert resp.json() == []
