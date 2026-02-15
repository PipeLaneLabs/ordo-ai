import os
import sys
from pathlib import Path

import pytest


project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

os.environ.setdefault("OPENROUTER_API_KEY", "test-openrouter-key-12345")
os.environ.setdefault("GOOGLE_API_KEY", "test-google-key-12345")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-min-32-chars-long-12345")
os.environ.setdefault("POSTGRES_PASSWORD", "test-pass-123")
os.environ.setdefault("MINIO_SECRET_KEY", "test-minio-secret-123")


@pytest.fixture(autouse=True)
def _set_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key-12345")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key-12345")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-min-32-chars-long-12345")
    monkeypatch.setenv("POSTGRES_PASSWORD", "test-pass-123")
    monkeypatch.setenv("MINIO_SECRET_KEY", "test-minio-secret-123")
