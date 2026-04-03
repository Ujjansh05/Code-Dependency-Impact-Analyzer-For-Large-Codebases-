from pathlib import Path
import shutil
import uuid

import pytest
from click.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def sample_code_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "sample_code"


@pytest.fixture
def tmp_path() -> Path:
    root = Path(__file__).resolve().parents[1] / ".pytest_tmp"
    root.mkdir(parents=True, exist_ok=True)
    case_dir = root / f"case_{uuid.uuid4().hex}"
    case_dir.mkdir(parents=True, exist_ok=True)
    try:
        yield case_dir
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)
