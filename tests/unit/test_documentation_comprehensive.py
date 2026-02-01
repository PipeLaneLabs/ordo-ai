"""
Comprehensive tests for DocumentationAgent (Tier 5).

Tests cover:
- Initialization
- Prompt building with various project contexts
- Output parsing with XML tags
- Output parsing with markdown fallback
- File writing
- Code structure analysis
- Temperature configuration
- Error handling
"""

import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.tier_5.documentation import DocumentationAgent
from src.config import Settings
from src.llm.base_client import BaseLLMClient, LLMResponse
from src.orchestration.budget_guard import BudgetGuard
from src.orchestration.state import WorkflowState


@pytest.fixture
def mock_llm_client():
    """Create mock LLM client."""
    return MagicMock(spec=BaseLLMClient)


@pytest.fixture
def mock_budget_guard():
    """Create mock budget guard."""
    return MagicMock(spec=BudgetGuard)


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock(spec=Settings)
    settings.environment = "test"
    return settings


@pytest.fixture
def documentation_agent(mock_llm_client, mock_budget_guard, mock_settings):
    """Create DocumentationAgent instance."""
    return DocumentationAgent(
        llm_client=mock_llm_client,
        budget_guard=mock_budget_guard,
        settings=mock_settings,
    )


@pytest.fixture
def sample_workflow_state():
    """Create sample workflow state."""
    return {
        "workflow_id": "test-123",
        "user_request": "Generate documentation",
        "current_phase": "delivery",
        "current_task": "documentation",
        "current_agent": "DocumentationAgent",
        "rejection_count": 0,
        "state_version": 1,
        "requirements": "# Requirements\nTest requirements",
        "architecture": "# Architecture\nTest architecture",
        "tasks": "# Tasks\nTest tasks",
        "code_files": {},
        "test_files": {},
        "partial_artifacts": {},
        "validation_report": "",
        "quality_report": "",
        "security_report": "",
        "budget_used_tokens": 0,
        "budget_used_usd": 0.0,
        "budget_remaining_tokens": 10000,
        "budget_remaining_usd": 100.0,
        "quality_gates_passed": [],
        "blocking_issues": [],
        "awaiting_human_approval": False,
        "approval_gate": "",
        "approval_timeout": "",
        "routing_decision": {},
        "escalation_flag": False,
        "trace_id": "test-123",
        "dependencies": "# Dependencies\nTest dependencies",
        "infrastructure": "# Infrastructure\nTest infrastructure",
        "observability": "",
        "deviation_log": "",
        "compliance_log": "",
        "acceptance_report": "",
        "agent_token_usage": {},
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }


class TestDocumentationAgentInit:
    """Tests for DocumentationAgent initialization."""

    def test_init_with_defaults(self, mock_llm_client, mock_budget_guard, mock_settings):
        """Test agent initialization with default parameters."""
        agent = DocumentationAgent(
            llm_client=mock_llm_client,
            budget_guard=mock_budget_guard,
            settings=mock_settings,
        )
        
        assert agent.name == "DocumentationAgent"
        assert agent.llm_client == mock_llm_client
        assert agent.budget_guard == mock_budget_guard
        assert agent.settings == mock_settings
        assert agent.token_budget == 8000

    def test_init_sets_correct_token_budget(self, mock_llm_client, mock_budget_guard, mock_settings):
        """Test that initialization sets correct token budget."""
        agent = DocumentationAgent(
            llm_client=mock_llm_client,
            budget_guard=mock_budget_guard,
            settings=mock_settings,
        )
        
        assert agent.token_budget == 8000


class TestBuildPrompt:
    """Tests for prompt building."""

    @pytest.mark.asyncio
    async def test_build_prompt_with_all_files(self, documentation_agent, sample_workflow_state):
        """Test prompt building when all context files exist."""
        with patch.object(documentation_agent, "_read_if_exists") as mock_read:
            mock_read.side_effect = [
                "# Requirements\nTest requirements",
                "# Architecture\nTest architecture",
                "# Tasks\nTest tasks",
                "# Dependencies\nTest dependencies",
                "# Infrastructure\nTest infrastructure",
            ]
            
            with patch.object(documentation_agent, "_analyze_code_structure") as mock_analyze:
                mock_analyze.return_value = "Project Structure:\n```\nsrc/\n```"
                
                prompt = await documentation_agent._build_prompt(sample_workflow_state)
        
        assert "Documentation Generation Task" in prompt
        assert "README.md" in prompt
        assert "API_REFERENCE.md" in prompt
        assert "TROUBLESHOOTING.md" in prompt
        assert "# Requirements" in prompt
        assert "# Architecture" in prompt

    @pytest.mark.asyncio
    async def test_build_prompt_with_missing_files(self, documentation_agent, sample_workflow_state):
        """Test prompt building when some context files are missing."""
        with patch.object(documentation_agent, "_read_if_exists") as mock_read:
            mock_read.side_effect = [None, None, None, None, None]
            
            with patch.object(documentation_agent, "_analyze_code_structure") as mock_analyze:
                mock_analyze.return_value = "Project Structure:\n```\nsrc/\n```"
                
                prompt = await documentation_agent._build_prompt(sample_workflow_state)
        
        assert "Not available" in prompt
        assert "Documentation Generation Task" in prompt

    @pytest.mark.asyncio
    async def test_build_prompt_includes_output_format(self, documentation_agent, sample_workflow_state):
        """Test that prompt includes output format instructions."""
        with patch.object(documentation_agent, "_read_if_exists") as mock_read:
            mock_read.side_effect = [
                "# Requirements",
                "# Architecture",
                "# Tasks",
                "# Dependencies",
                "# Infrastructure",
            ]
            
            with patch.object(documentation_agent, "_analyze_code_structure") as mock_analyze:
                mock_analyze.return_value = "Project Structure"
                
                prompt = await documentation_agent._build_prompt(sample_workflow_state)
        
        assert '<FILE name="README.md">' in prompt
        assert '<FILE name="docs/API_REFERENCE.md">' in prompt
        assert '<FILE name="docs/TROUBLESHOOTING.md">' in prompt


class TestParseOutput:
    """Tests for output parsing."""

    @pytest.mark.asyncio
    async def test_parse_output_with_xml_tags(self, documentation_agent, sample_workflow_state):
        """Test parsing output with XML-like tags."""
        response_content = """
        <FILE name="README.md">
        # Project README
        This is a test README.
        </FILE>
        
        <FILE name="docs/API_REFERENCE.md">
        # API Reference
        This is a test API reference.
        </FILE>
        
        <FILE name="docs/TROUBLESHOOTING.md">
        # Troubleshooting
        This is a test troubleshooting guide.
        </FILE>
        """
        
        response = LLMResponse(
            content=response_content,
            tokens_used=1000,
            model="test-model",
            latency_ms=100,
            provider="test",
        )
        
        with patch.object(documentation_agent, "_write_file") as mock_write:
            mock_write.return_value = AsyncMock()
            
            result = await documentation_agent._parse_output(response, sample_workflow_state)
        
        assert "documentation_files" in result
        assert len(result["documentation_files"]) == 3
        assert "README.md" in result["documentation_files"]
        assert "docs/API_REFERENCE.md" in result["documentation_files"]
        assert "docs/TROUBLESHOOTING.md" in result["documentation_files"]
        assert result["documentation_generated"] is True
        assert result["documentation_token_count"] == 1000

    @pytest.mark.asyncio
    async def test_parse_output_with_markdown_fallback(self, documentation_agent, sample_workflow_state):
        """Test parsing output with markdown fallback."""
        response_content = """# Project README

This is a test README with markdown content.

## Features
- Feature 1
- Feature 2

## Installation
Run `pip install project`
"""
        
        response = LLMResponse(
            content=response_content,
            tokens_used=500,
            model="test-model",
            latency_ms=100,
            provider="test",
        )
        
        with patch.object(documentation_agent, "_write_file") as mock_write:
            mock_write.return_value = AsyncMock()
            
            result = await documentation_agent._parse_output(response, sample_workflow_state)
        
        assert "documentation_files" in result
        assert "README.md" in result["documentation_files"]
        assert result["documentation_generated"] is True

    @pytest.mark.asyncio
    async def test_parse_output_with_empty_content(self, documentation_agent, sample_workflow_state):
        """Test parsing output with empty content raises error."""
        response = LLMResponse(
            content="",
            tokens_used=0,
            model="test-model",
            latency_ms=100,
            provider="test",
        )
        
        with pytest.raises(ValueError) as exc_info:
            await documentation_agent._parse_output(response, sample_workflow_state)
        
        assert "No valid documentation files" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_parse_output_with_invalid_content(self, documentation_agent, sample_workflow_state):
        """Test parsing output with invalid content raises error."""
        response = LLMResponse(
            content="This is just plain text with no structure",
            tokens_used=100,
            model="test-model",
            latency_ms=100,
            provider="test",
        )
        
        with pytest.raises(ValueError) as exc_info:
            await documentation_agent._parse_output(response, sample_workflow_state)
        
        assert "No valid documentation files" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_parse_output_case_insensitive_tags(self, documentation_agent, sample_workflow_state):
        """Test parsing output with case-insensitive XML tags."""
        response_content = """
        <file name="README.md">
        # Project README
        </file>
        
        <FILE name="docs/API_REFERENCE.md">
        # API Reference
        </FILE>
        """
        
        response = LLMResponse(
            content=response_content,
            tokens_used=800,
            model="test-model",
            latency_ms=100,
            provider="test",
        )
        
        with patch.object(documentation_agent, "_write_file") as mock_write:
            mock_write.return_value = AsyncMock()
            
            result = await documentation_agent._parse_output(response, sample_workflow_state)
        
        assert len(result["documentation_files"]) >= 1

    @pytest.mark.asyncio
    async def test_parse_output_skips_empty_files(self, documentation_agent, sample_workflow_state):
        """Test that parsing skips empty file content."""
        response_content = """
        <FILE name="README.md">
        # Project README
        </FILE>
        
        <FILE name="docs/EMPTY.md">
        
        </FILE>
        """
        
        response = LLMResponse(
            content=response_content,
            tokens_used=600,
            model="test-model",
            latency_ms=100,
            provider="test",
        )
        
        with patch.object(documentation_agent, "_write_file") as mock_write:
            mock_write.return_value = AsyncMock()
            
            result = await documentation_agent._parse_output(response, sample_workflow_state)
        
        # Only README.md should be written (EMPTY.md is skipped)
        assert "README.md" in result["documentation_files"]
        assert "docs/EMPTY.md" not in result["documentation_files"]


class TestGetTemperature:
    """Tests for temperature configuration."""

    def test_get_temperature_returns_correct_value(self, documentation_agent):
        """Test that temperature is set to 0.3 for balanced creativity."""
        temperature = documentation_agent._get_temperature()
        
        assert temperature == 0.3

    def test_get_temperature_is_float(self, documentation_agent):
        """Test that temperature returns a float."""
        temperature = documentation_agent._get_temperature()
        
        assert isinstance(temperature, float)


class TestAnalyzeCodeStructure:
    """Tests for code structure analysis."""

    def test_analyze_code_structure_with_existing_src(self, documentation_agent):
        """Test code structure analysis when src directory exists."""
        with patch("src.agents.tier_5.documentation.Path") as mock_path_class:
            mock_src_path = MagicMock()
            mock_src_path.exists.return_value = True
            
            # Create mock files with proper comparison support
            mock_file1 = MagicMock()
            mock_file1.is_file.return_value = True
            mock_file1.suffix = ".py"
            mock_file1.relative_to.return_value = Path("src/main.py")
            mock_file1.__lt__ = lambda self, other: True  # For sorting
            
            mock_file2 = MagicMock()
            mock_file2.is_file.return_value = True
            mock_file2.suffix = ".py"
            mock_file2.relative_to.return_value = Path("src/config.py")
            mock_file2.__lt__ = lambda self, other: False  # For sorting
            
            mock_src_path.rglob.return_value = [mock_file1, mock_file2]
            mock_path_class.return_value = mock_src_path
            
            result = documentation_agent._analyze_code_structure()
        
        assert "Project Structure:" in result
        assert "```" in result

    def test_analyze_code_structure_without_src(self, documentation_agent):
        """Test code structure analysis when src directory doesn't exist."""
        with patch("src.agents.tier_5.documentation.Path") as mock_path_class:
            mock_src_path = MagicMock()
            mock_src_path.exists.return_value = False
            mock_path_class.return_value = mock_src_path
            
            result = documentation_agent._analyze_code_structure()
        
        assert result == "Code structure not available"

    def test_analyze_code_structure_filters_python_files(self, documentation_agent):
        """Test that code structure analysis only includes Python files."""
        with patch("src.agents.tier_5.documentation.Path") as mock_path_class:
            mock_src_path = MagicMock()
            mock_src_path.exists.return_value = True
            
            # Create mock files with different extensions and proper comparison
            py_file = MagicMock()
            py_file.is_file.return_value = True
            py_file.suffix = ".py"
            py_file.relative_to.return_value = Path("src/main.py")
            py_file.__lt__ = lambda self, other: True  # For sorting
            
            txt_file = MagicMock()
            txt_file.is_file.return_value = True
            txt_file.suffix = ".txt"
            txt_file.relative_to.return_value = Path("src/readme.txt")
            txt_file.__lt__ = lambda self, other: False  # For sorting
            
            mock_src_path.rglob.return_value = [py_file, txt_file]
            mock_path_class.return_value = mock_src_path

            result = documentation_agent._analyze_code_structure()

        assert "main.py" in result  # Check for file presence regardless of path separator
        assert "src/readme.txt" not in result


class TestDocumentationAgentIntegration:
    """Integration tests for DocumentationAgent."""

    @pytest.mark.asyncio
    async def test_full_documentation_generation_flow(self, documentation_agent, sample_workflow_state):
        """Test complete documentation generation flow."""
        # Mock the LLM response
        llm_response = LLMResponse(
            content="""
            <FILE name="README.md">
            # Test Project
            This is a test project.
            </FILE>
            """,
            tokens_used=1000,
            model="test-model",
            latency_ms=100,
            provider="test",
        )
        
        with patch.object(documentation_agent, "_read_if_exists") as mock_read:
            mock_read.side_effect = [
                "# Requirements",
                "# Architecture",
                "# Tasks",
                "# Dependencies",
                "# Infrastructure",
            ]
            
            with patch.object(documentation_agent, "_analyze_code_structure") as mock_analyze:
                mock_analyze.return_value = "Project Structure"
                
                with patch.object(documentation_agent, "_write_file") as mock_write:
                    mock_write.return_value = AsyncMock()
                    
                    # Build prompt
                    prompt = await documentation_agent._build_prompt(sample_workflow_state)
                    assert "Documentation Generation Task" in prompt
                    
                    # Parse output
                    result = await documentation_agent._parse_output(llm_response, sample_workflow_state)
                    assert result["documentation_generated"] is True
                    assert "README.md" in result["documentation_files"]
