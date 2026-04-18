"""
Shared pytest fixtures and path constants.
"""
import pytest
from pathlib import Path

TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent
FIXTURES_DIR = TESTS_DIR / "fixtures"
OUTPUT_DIR = PROJECT_ROOT / "output"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def output_dir() -> Path:
    return OUTPUT_DIR


@pytest.fixture
def mapping_path() -> Path:
    return FIXTURES_DIR / "mapping.txt"


@pytest.fixture
def existing_csv_path() -> Path:
    return FIXTURES_DIR / "existing_master.csv"
