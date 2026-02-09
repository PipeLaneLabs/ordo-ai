"""Extended tests for QualityEngineerAgent aligned to current implementation."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.tier_3.quality_engineer import QualityEngineerAgent
from src.config import Settings
from src.llm.base_client import LLMResponse
from src.orchestration.budget_guard import BudgetGuard


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
        budget_guard=MagicMock(spec=BudgetGuard),
        settings=MagicMock(spec=Settings),
        token_budget=12000,
    )


@pytest.mark.asyncio
async def test_parse_output_no_tests_approved(quality_engineer) -> None:
    response = LLMResponse(
        content="No tests generated",
        model="test",
        tokens_used=1,
        cost_usd=0.0,
        latency_ms=1,
        provider="test",
    )

    with (
        patch.object(quality_engineer, "_write_file", new=AsyncMock()) as write_file,
        patch.object(
            quality_engineer,
            "_run_pytest",
            new=AsyncMock(
                return_value={
                    "return_code": 0,
                    "stdout": "TOTAL 10 0 100%",
                    "stderr": "",
                }
            ),
        ),
    ):
        result = await quality_engineer._parse_output(response, {})

    assert result["files_created"] == []
    assert result["status"] == "APPROVED"
    write_file.assert_called()


@pytest.mark.asyncio
async def test_parse_output_low_coverage_rejected(quality_engineer) -> None:
    response = LLMResponse(
        content="```python:tests/unit/test_a.py\ndef test_a():\n    assert True\n```",
        model="test",
        tokens_used=1,
        cost_usd=0.0,
        latency_ms=1,
        provider="test",
    )

    with (
        patch.object(quality_engineer, "_write_file", new=AsyncMock()),
        patch.object(
            quality_engineer,
            "_run_pytest",
            new=AsyncMock(
                return_value={
                    "return_code": 0,
                    "stdout": "TOTAL 10 5 50%",
                    "stderr": "",
                }
            ),
        ),
    ):
        result = await quality_engineer._parse_output(response, {})

    assert result["status"] == "REJECTED"


def test_extract_coverage_no_last_run(quality_engineer) -> None:
    quality_engineer._last_pytest_run_at = None
    coverage = quality_engineer._extract_coverage({"stdout": "No totals"})

    assert coverage == 0.0


@pytest.mark.asyncio
async def test_read_src_files_truncates(quality_engineer, monkeypatch) -> None:
    files = [f"file_{i}.py" for i in range(60)]
    fake_walk = [("src", [], files)]

    monkeypatch.setattr(os, "walk", lambda _root: fake_walk)

    async_file = _AsyncFile("print('hi')")
    with patch.object(quality_engineer, "_open_file_async", return_value=async_file):
        content = await quality_engineer._read_src_files()

    assert "truncated" in content
