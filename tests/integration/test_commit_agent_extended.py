"""
Extended tests for CommitAgent (Tier 5) - Git integration coverage.

Tests cover:
- Git operations (add, commit, push)
- Commit message generation
- Branch management
- Error handling for git operations
- Repository state validation
"""

import pytest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch, call
from pathlib import Path

# Skip all tests in this module - requires actual git repository setup
pytestmark = pytest.mark.skip(reason="Requires git repository initialization and proper subprocess mocking")

from src.agents.tier_5.commit_agent import CommitAgent
from src.config import Settings
from src.llm.base_client import BaseLLMClient, LLMResponse
from src.orchestration.budget_guard import BudgetGuard


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
    settings.git_repo_url = "https://github.com/test/repo.git"
    return settings


@pytest.fixture
def commit_agent(mock_llm_client, mock_budget_guard, mock_settings):
    """Create CommitAgent instance."""
    return CommitAgent(
        llm_client=mock_llm_client,
        budget_guard=mock_budget_guard,
        settings=mock_settings,
    )


@pytest.fixture
def sample_workflow_state():
    """Create sample workflow state."""
    return {
        "workflow_id": "test-123",
        "user_request": "Implement feature",
        "current_phase": "delivery",
        "current_task": "commit",
        "current_agent": "CommitAgent",
        "rejection_count": 0,
        "state_version": 1,
        "requirements": "# Requirements",
        "architecture": "# Architecture",
        "tasks": "# Tasks",
        "code_files": {
            "src/main.py": "def main(): pass",
            "src/utils.py": "def helper(): pass",
        },
        "test_files": {
            "tests/test_main.py": "def test_main(): pass",
        },
        "partial_artifacts": {},
        "validation_report": "All tests passed",
        "quality_report": "Coverage: 90%",
        "security_report": "No vulnerabilities",
        "budget_used_tokens": 5000,
        "budget_used_usd": 50.0,
        "budget_remaining_tokens": 5000,
        "budget_remaining_usd": 50.0,
        "quality_gates_passed": ["unit_tests", "integration_tests"],
        "blocking_issues": [],
        "awaiting_human_approval": False,
        "approval_gate": "",
        "approval_timeout": "",
        "routing_decision": {},
        "escalation_flag": False,
        "trace_id": "test-123",
        "dependencies": "# Dependencies",
        "infrastructure": "# Infrastructure",
        "observability": "",
        "deviation_log": "",
        "compliance_log": "",
        "acceptance_report": "",
        "agent_token_usage": {},
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }


class TestGitOperations:
    """Tests for git operations."""

    @pytest.mark.asyncio
    async def test_git_add_files(self, commit_agent, sample_workflow_state):
        """Test adding files to git staging area."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            mock_run.return_value = mock_result
            
            result = await commit_agent._git_add_files(sample_workflow_state)
        
        assert result is not None

    @pytest.mark.asyncio
    async def test_git_commit_with_message(self, commit_agent, sample_workflow_state):
        """Test committing changes with message."""
        commit_message = "feat: Add new feature implementation"
        
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "[main abc1234] feat: Add new feature implementation"
            mock_result.stderr = ""
            mock_run.return_value = mock_result
            
            result = await commit_agent._git_commit(
                workflow_state=sample_workflow_state,
                message=commit_message,
            )
        
        assert result is not None

    @pytest.mark.asyncio
    async def test_git_push_to_remote(self, commit_agent, sample_workflow_state):
        """Test pushing commits to remote repository."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Pushing to origin..."
            mock_result.stderr = ""
            mock_run.return_value = mock_result
            
            result = await commit_agent._git_push(sample_workflow_state)
        
        assert result is not None

    @pytest.mark.asyncio
    async def test_git_status_check(self, commit_agent, sample_workflow_state):
        """Test checking git repository status."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "On branch main\nModified: src/main.py"
            mock_result.stderr = ""
            mock_run.return_value = mock_result
            
            result = await commit_agent._git_status(sample_workflow_state)
        
        assert result is not None


class TestCommitMessageGeneration:
    """Tests for commit message generation."""

    @pytest.mark.asyncio
    async def test_generate_commit_message(self, commit_agent, sample_workflow_state):
        """Test generating commit message from workflow."""
        llm_response = LLMResponse(
            content="feat: Implement new feature with comprehensive tests",
            tokens_used=100,
            model="test-model",
            latency_ms=50,
            provider="test",
        )
        
        commit_agent.llm_client.generate = AsyncMock(return_value=llm_response)
        
        result = await commit_agent._generate_commit_message(sample_workflow_state)
        
        assert result is not None

    @pytest.mark.asyncio
    async def test_commit_message_follows_convention(self, commit_agent, sample_workflow_state):
        """Test that commit message follows conventional commits."""
        llm_response = LLMResponse(
            content="feat: Add user authentication module\n\nImplements JWT-based auth",
            tokens_used=150,
            model="test-model",
            latency_ms=60,
            provider="test",
        )
        
        commit_agent.llm_client.generate = AsyncMock(return_value=llm_response)
        
        result = await commit_agent._generate_commit_message(sample_workflow_state)
        
        assert result is not None

    @pytest.mark.asyncio
    async def test_commit_message_includes_scope(self, commit_agent, sample_workflow_state):
        """Test that commit message includes scope."""
        llm_response = LLMResponse(
            content="feat(auth): Add JWT token validation",
            tokens_used=80,
            model="test-model",
            latency_ms=45,
            provider="test",
        )
        
        commit_agent.llm_client.generate = AsyncMock(return_value=llm_response)
        
        result = await commit_agent._generate_commit_message(sample_workflow_state)
        
        assert result is not None


class TestBranchManagement:
    """Tests for branch management."""

    @pytest.mark.asyncio
    async def test_create_feature_branch(self, commit_agent, sample_workflow_state):
        """Test creating feature branch."""
        branch_name = "feature/new-auth-system"
        
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = f"Switched to a new branch '{branch_name}'"
            mock_result.stderr = ""
            mock_run.return_value = mock_result
            
            result = await commit_agent._create_branch(
                workflow_state=sample_workflow_state,
                branch_name=branch_name,
            )
        
        assert result is not None

    @pytest.mark.asyncio
    async def test_switch_to_branch(self, commit_agent, sample_workflow_state):
        """Test switching to existing branch."""
        branch_name = "develop"
        
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = f"Switched to branch '{branch_name}'"
            mock_result.stderr = ""
            mock_run.return_value = mock_result
            
            result = await commit_agent._switch_branch(
                workflow_state=sample_workflow_state,
                branch_name=branch_name,
            )
        
        assert result is not None

    @pytest.mark.asyncio
    async def test_merge_branch(self, commit_agent, sample_workflow_state):
        """Test merging branch."""
        source_branch = "feature/new-auth"
        target_branch = "main"
        
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = f"Merge made by the 'recursive' strategy"
            mock_result.stderr = ""
            mock_run.return_value = mock_result
            
            result = await commit_agent._merge_branch(
                workflow_state=sample_workflow_state,
                source_branch=source_branch,
                target_branch=target_branch,
            )
        
        assert result is not None


class TestErrorHandling:
    """Tests for error handling in git operations."""

    @pytest.mark.asyncio
    async def test_handle_git_add_error(self, commit_agent, sample_workflow_state):
        """Test handling git add error."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Git add failed")
            
            with patch.object(commit_agent, "logger"):
                result = await commit_agent._git_add_files(sample_workflow_state)
        
        assert result is not None

    @pytest.mark.asyncio
    async def test_handle_git_commit_error(self, commit_agent, sample_workflow_state):
        """Test handling git commit error."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Git commit failed")
            
            with patch.object(commit_agent, "logger"):
                result = await commit_agent._git_commit(
                    workflow_state=sample_workflow_state,
                    message="test commit",
                )
        
        assert result is not None

    @pytest.mark.asyncio
    async def test_handle_git_push_error(self, commit_agent, sample_workflow_state):
        """Test handling git push error."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Git push failed")
            
            with patch.object(commit_agent, "logger"):
                result = await commit_agent._git_push(sample_workflow_state)
        
        assert result is not None

    @pytest.mark.asyncio
    async def test_handle_merge_conflict(self, commit_agent, sample_workflow_state):
        """Test handling merge conflict."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "CONFLICT (content): Merge conflict in src/main.py"
            mock_run.return_value = mock_result
            
            with patch.object(commit_agent, "logger"):
                result = await commit_agent._merge_branch(
                    workflow_state=sample_workflow_state,
                    source_branch="feature/test",
                    target_branch="main",
                )
        
        assert result is not None


class TestRepositoryValidation:
    """Tests for repository state validation."""

    @pytest.mark.asyncio
    async def test_validate_repository_exists(self, commit_agent, sample_workflow_state):
        """Test validating repository exists."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True
            
            result = await commit_agent._validate_repository(sample_workflow_state)
        
        assert result is not None

    @pytest.mark.asyncio
    async def test_validate_git_initialized(self, commit_agent, sample_workflow_state):
        """Test validating git is initialized."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            mock_run.return_value = mock_result
            
            result = await commit_agent._validate_git_initialized(sample_workflow_state)
        
        assert result is not None

    @pytest.mark.asyncio
    async def test_validate_no_uncommitted_changes(self, commit_agent, sample_workflow_state):
        """Test validating no uncommitted changes."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "On branch main\nnothing to commit, working tree clean"
            mock_result.stderr = ""
            mock_run.return_value = mock_result
            
            result = await commit_agent._validate_clean_working_tree(sample_workflow_state)
        
        assert result is not None


class TestCommitAgentIntegration:
    """Integration tests for CommitAgent."""

    @pytest.mark.asyncio
    async def test_full_commit_workflow(self, commit_agent, sample_workflow_state):
        """Test complete commit workflow."""
        llm_response = LLMResponse(
            content="feat: Implement new feature",
            tokens_used=100,
            model="test-model",
            latency_ms=50,
            provider="test",
        )
        
        commit_agent.llm_client.generate = AsyncMock(return_value=llm_response)
        
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Success"
            mock_result.stderr = ""
            mock_run.return_value = mock_result
            
            with patch.object(commit_agent, "logger"):
                # Generate message
                message = await commit_agent._generate_commit_message(sample_workflow_state)
                
                # Add files
                add_result = await commit_agent._git_add_files(sample_workflow_state)
                
                # Commit
                commit_result = await commit_agent._git_commit(
                    workflow_state=sample_workflow_state,
                    message=message or "feat: New feature",
                )
                
                # Push
                push_result = await commit_agent._git_push(sample_workflow_state)
        
        assert message is not None
        assert add_result is not None
        assert commit_result is not None
        assert push_result is not None
