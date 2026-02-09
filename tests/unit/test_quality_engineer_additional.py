"""Additional QualityEngineerAgent tests for file reading and coverage JSON."""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from src.agents.tier_3.quality_engineer import QualityEngineerAgent
from src.config import Settings


class _AsyncFile:
    def __init__(self, content: str) -> None:
        self._content = content

    async def read(self) -> str:
        return self._content

    async def __aenter__(self) -> _AsyncFile:
        return self

    async def __aexit__(self, _exc_type, _exc, _tb) -> None:
        return None


@pytest.fixture
def quality_engineer() -> QualityEngineerAgent:
    return QualityEngineerAgent(
        name="QualityEngineerAgent",
        llm_client=MagicMock(),
        budget_guard=MagicMock(),
        settings=MagicMock(spec=Settings),
        token_budget=12000,
    )


@pytest.mark.asyncio
async def test_read_src_files_collects_content(quality_engineer, monkeypatch) -> None:
    fake_walk = [("src", [], ["sample.py"])]

    monkeypatch.setattr(os, "walk", lambda _root: fake_walk)

    async_file = _AsyncFile("print('hi')")
    with patch.object(quality_engineer, "_open_file_async", return_value=async_file):
        content = await quality_engineer._read_src_files()

    assert "sample.py" in content
    assert "print('hi')" in content


@pytest.mark.asyncio
async def test_read_existing_tests_reads_files(
    quality_engineer, tmp_path, monkeypatch
) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    test_file = tests_dir / "test_sample.py"
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)

    async_file = _AsyncFile("def test_ok():\n    assert True\n")
    with patch.object(quality_engineer, "_open_file_async", return_value=async_file):
        content = await quality_engineer._read_existing_tests()

    assert "Existing Test" in content
    assert "test_sample.py" in content


def test_extract_coverage_from_json(quality_engineer, tmp_path, monkeypatch) -> None:
    coverage_data = {"totals": {"percent_covered": 88.5}}
    (tmp_path / "coverage.json").write_text(json.dumps(coverage_data), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    quality_engineer._last_pytest_run_at = 1.0

    coverage = quality_engineer._extract_coverage({"stdout": ""})

    assert coverage == 88.5


def test_extract_coverage_json_error_returns_zero(
    quality_engineer, tmp_path, monkeypatch
) -> None:
    (tmp_path / "coverage.json").write_text("not-json", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    quality_engineer._last_pytest_run_at = 1.0

    coverage = quality_engineer._extract_coverage({"stdout": ""})

    assert coverage == 0.0
