"""
Unit tests for backend/services/job_runner.py

Tests cover:
  - _persist_ingredients: upsert logic with real in-memory SQLite
  - run_job: orchestration contract (mocked scraper + classifier)
"""
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend.models import Ingredient, Job, Product, ProductIngredient
from backend.services.job_runner import _persist_ingredients, run_job


# ---------------------------------------------------------------------------
# In-memory SQLite fixture — StaticPool shares one DB across connections
# ---------------------------------------------------------------------------

@pytest.fixture()
def engine_and_session():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    yield eng, Session
    Base.metadata.drop_all(eng)


@pytest.fixture()
def db(engine_and_session):
    _, Session = engine_and_session
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def Session(engine_and_session):
    _, S = engine_and_session
    return S


def _make_job(db, job_id: str | None = None) -> Job:
    job = Job(
        id=job_id or str(uuid4()),
        status="queued",
        url_count=1,
        processed=0,
        in_scope=0,
        excluded=0,
        errors=0,
        created_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    return job


def _make_product(db, job_id: str) -> Product:
    p = Product(
        id=str(uuid4()),
        job_id=job_id,
        url="https://example.com",
        name="Test Product",
        ingredients_raw="Water, PPD",
        in_scope=True,
    )
    db.add(p)
    db.flush()
    return p


# ---------------------------------------------------------------------------
# _persist_ingredients
# ---------------------------------------------------------------------------

class TestPersistIngredients:
    def _classify_result(self, components=None, dye_actives=None, internal_names=None):
        return {
            "in_scope": True,
            "scope_reason": "dye product",
            "components": components or {"OXIDATIVE DYE SYSTEM": ["p-Phenylenediamine", "Resorcinol"]},
            "dye_actives": dye_actives or ["p-Phenylenediamine"],
            "internal_names": internal_names or {"p-Phenylenediamine": "PPD"},
        }

    def test_creates_new_ingredients(self, db):
        job = _make_job(db)
        product = _make_product(db, job.id)
        _persist_ingredients(db, product.id, self._classify_result())
        db.commit()

        ings = db.query(Ingredient).all()
        assert len(ings) == 2
        names = {i.name for i in ings}
        assert "p-Phenylenediamine" in names
        assert "Resorcinol" in names

    def test_sets_dye_active_flag(self, db):
        job = _make_job(db)
        product = _make_product(db, job.id)
        _persist_ingredients(db, product.id, self._classify_result())
        db.commit()

        ppd = db.query(Ingredient).filter(Ingredient.name == "p-Phenylenediamine").first()
        res = db.query(Ingredient).filter(Ingredient.name == "Resorcinol").first()
        assert ppd.is_dye_active is True
        assert res.is_dye_active is False

    def test_sets_internal_name(self, db):
        job = _make_job(db)
        product = _make_product(db, job.id)
        _persist_ingredients(db, product.id, self._classify_result())
        db.commit()

        ppd = db.query(Ingredient).filter(Ingredient.name == "p-Phenylenediamine").first()
        assert ppd.internal_name == "PPD"

    def test_upserts_existing_ingredient_increments_count(self, db):
        existing = Ingredient(name="p-Phenylenediamine", count=1, is_dye_active=False)
        db.add(existing)
        db.commit()

        job = _make_job(db)
        product = _make_product(db, job.id)
        _persist_ingredients(db, product.id, self._classify_result())
        db.commit()

        ing = db.query(Ingredient).filter(Ingredient.name == "p-Phenylenediamine").first()
        assert ing.count == 2

    def test_upsert_sets_dye_active_on_existing(self, db):
        existing = Ingredient(name="p-Phenylenediamine", count=1, is_dye_active=False)
        db.add(existing)
        db.commit()

        job = _make_job(db)
        product = _make_product(db, job.id)
        _persist_ingredients(db, product.id, self._classify_result())
        db.commit()

        ing = db.query(Ingredient).filter(Ingredient.name == "p-Phenylenediamine").first()
        assert ing.is_dye_active is True

    def test_creates_junction_rows(self, db):
        job = _make_job(db)
        product = _make_product(db, job.id)
        _persist_ingredients(db, product.id, self._classify_result())
        db.commit()

        pis = db.query(ProductIngredient).filter(
            ProductIngredient.product_id == product.id
        ).all()
        assert len(pis) == 2
        components = {pi.component for pi in pis}
        assert "OXIDATIVE DYE SYSTEM" in components

    def test_empty_components_creates_nothing(self, db):
        job = _make_job(db)
        product = _make_product(db, job.id)
        _persist_ingredients(db, product.id, {"components": {}, "dye_actives": [], "internal_names": {}})
        db.commit()

        assert db.query(Ingredient).count() == 0
        assert db.query(ProductIngredient).count() == 0

    def test_duplicate_ingredient_across_components_creates_single_junction(self, db):
        job = _make_job(db)
        product = _make_product(db, job.id)
        classify_result = {
            "components": {
                "COMP A": ["p-Phenylenediamine"],
                "COMP B": ["p-Phenylenediamine"],
            },
            "dye_actives": ["p-Phenylenediamine"],
            "internal_names": {},
        }
        _persist_ingredients(db, product.id, classify_result)
        db.commit()

        ingredients = db.query(Ingredient).all()
        assert len(ingredients) == 1
        junction_rows = db.query(ProductIngredient).filter(
            ProductIngredient.product_id == product.id
        ).all()
        assert len(junction_rows) == 1


# ---------------------------------------------------------------------------
# run_job orchestration — patch SessionLocal to use the test session factory
# ---------------------------------------------------------------------------

class TestRunJob:
    def _run(self, coro):
        return asyncio.run(coro)

    def _good_scrape(self):
        return {"url": "https://ex.com", "name": "Excellence", "ingredients_raw": "PPD, Water"}

    def _in_scope_classify(self):
        return {
            "in_scope": True,
            "scope_reason": "dye",
            "components": {"DYE SYSTEM": ["PPD"]},
            "dye_actives": ["PPD"],
            "internal_names": {},
        }

    def _out_of_scope_classify(self):
        return {
            "in_scope": False,
            "scope_reason": "not a dye product",
            "components": {},
            "dye_actives": [],
            "internal_names": {},
        }

    def test_job_marked_running_then_complete(self, Session):
        # Create job in a dedicated session
        s = Session()
        job = Job(id=str(uuid4()), status="queued", url_count=1,
                  processed=0, in_scope=0, excluded=0, errors=0, created_at=datetime.utcnow())
        s.add(job)
        s.commit()
        job_id = job.id
        s.close()

        with (
            patch("backend.services.job_runner.SessionLocal", Session),
            patch("backend.services.job_runner.scrape", AsyncMock(return_value=self._good_scrape())),
            patch("backend.services.job_runner.classify", AsyncMock(return_value=self._in_scope_classify())),
        ):
            self._run(run_job(job_id, ["https://ex.com"]))

        # Re-query in fresh session
        s2 = Session()
        job = s2.query(Job).filter(Job.id == job_id).first()
        assert job.status == "complete"
        assert job.processed == 1
        assert job.in_scope == 1
        assert job.excluded == 0
        assert job.completed_at is not None
        s2.close()

    def test_out_of_scope_increments_excluded(self, Session):
        s = Session()
        job = Job(id=str(uuid4()), status="queued", url_count=1,
                  processed=0, in_scope=0, excluded=0, errors=0, created_at=datetime.utcnow())
        s.add(job)
        s.commit()
        job_id = job.id
        s.close()

        with (
            patch("backend.services.job_runner.SessionLocal", Session),
            patch("backend.services.job_runner.scrape", AsyncMock(return_value=self._good_scrape())),
            patch("backend.services.job_runner.classify", AsyncMock(return_value=self._out_of_scope_classify())),
        ):
            self._run(run_job(job_id, ["https://ex.com"]))

        s2 = Session()
        job = s2.query(Job).filter(Job.id == job_id).first()
        assert job.excluded == 1
        assert job.in_scope == 0
        assert job.status == "complete"
        s2.close()

    def test_scrape_error_increments_errors_continues(self, Session):
        s = Session()
        job_id = str(uuid4())
        job = Job(id=job_id, status="queued", url_count=2, processed=0,
                  in_scope=0, excluded=0, errors=0, created_at=datetime.utcnow())
        s.add(job)
        s.commit()
        s.close()

        with (
            patch("backend.services.job_runner.SessionLocal", Session),
            patch("backend.services.job_runner.scrape", AsyncMock(side_effect=Exception("timeout"))),
            patch("backend.services.job_runner.classify", AsyncMock(return_value=self._in_scope_classify())),
        ):
            self._run(run_job(job_id, ["https://a.com", "https://b.com"]))

        s2 = Session()
        job = s2.query(Job).filter(Job.id == job_id).first()
        assert job.errors == 2
        assert job.processed == 2
        assert job.status == "failed"
        s2.close()

    def test_all_errors_sets_status_failed(self, Session):
        s = Session()
        job_id = str(uuid4())
        job = Job(id=job_id, status="queued", url_count=1, processed=0,
                  in_scope=0, excluded=0, errors=0, created_at=datetime.utcnow())
        s.add(job)
        s.commit()
        s.close()

        with (
            patch("backend.services.job_runner.SessionLocal", Session),
            patch("backend.services.job_runner.scrape", AsyncMock(side_effect=Exception("err"))),
            patch("backend.services.job_runner.classify", AsyncMock()),
        ):
            self._run(run_job(job_id, ["https://ex.com"]))

        s2 = Session()
        job = s2.query(Job).filter(Job.id == job_id).first()
        assert job.status == "failed"
        s2.close()

    def test_partial_success_sets_status_complete(self, Session):
        s = Session()
        job_id = str(uuid4())
        job = Job(id=job_id, status="queued", url_count=2, processed=0,
                  in_scope=0, excluded=0, errors=0, created_at=datetime.utcnow())
        s.add(job)
        s.commit()
        s.close()

        scrape_results = [self._good_scrape(), Exception("timeout")]

        async def _scrape_side_effect(url):
            r = scrape_results.pop(0)
            if isinstance(r, Exception):
                raise r
            return r

        with (
            patch("backend.services.job_runner.SessionLocal", Session),
            patch("backend.services.job_runner.scrape", side_effect=_scrape_side_effect),
            patch("backend.services.job_runner.classify", AsyncMock(return_value=self._in_scope_classify())),
        ):
            self._run(run_job(job_id, ["https://a.com", "https://b.com"]))

        s2 = Session()
        job = s2.query(Job).filter(Job.id == job_id).first()
        assert job.status == "complete"
        assert job.errors == 1
        assert job.processed == 2
        s2.close()

    def test_missing_job_id_exits_without_error(self, Session):
        with patch("backend.services.job_runner.SessionLocal", Session):
            self._run(run_job(str(uuid4()), ["https://ex.com"]))
