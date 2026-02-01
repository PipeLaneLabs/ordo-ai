"""Unit tests for ArtifactStorage (MinIO client)."""

from unittest.mock import MagicMock, patch

import pytest

from src.exceptions import StorageError
from src.storage.artifact_storage import ArtifactStorage


@pytest.fixture
def mock_minio_client():
    """Mock MinIO client."""
    client = MagicMock()
    client.bucket_exists = MagicMock(return_value=True)
    client.make_bucket = MagicMock()
    client.put_object = MagicMock()
    client.get_object = MagicMock()
    client.list_objects = MagicMock()
    client.remove_object = MagicMock()
    client.get_presigned_download_url = MagicMock()
    return client


@pytest.fixture
def storage(mock_minio_client):
    """Create ArtifactStorage instance with mocked MinIO client."""
    with patch("src.storage.artifact_storage.Minio", return_value=mock_minio_client):
        storage = ArtifactStorage()
        storage.client = mock_minio_client
        return storage


class TestArtifactStorageInit:
    """Test ArtifactStorage initialization."""

    def test_init_creates_bucket_if_not_exists(self):
        """Test that __init__ creates bucket if it doesn't exist."""
        mock_client = MagicMock()
        mock_client.bucket_exists = MagicMock(return_value=False)
        mock_client.make_bucket = MagicMock()

        with patch("src.storage.artifact_storage.Minio", return_value=mock_client):
            storage_instance = ArtifactStorage()

            mock_client.make_bucket.assert_called_once()
            assert storage_instance.bucket_name == "agent-artifacts"

    def test_init_skips_bucket_creation_if_exists(self):
        """Test that __init__ skips bucket creation if it already exists."""
        mock_client = MagicMock()
        mock_client.bucket_exists = MagicMock(return_value=True)
        mock_client.make_bucket = MagicMock()

        with patch("src.storage.artifact_storage.Minio", return_value=mock_client):
            storage = ArtifactStorage()

            mock_client.make_bucket.assert_not_called()

    def test_init_raises_storage_error_on_bucket_creation_failure(self):
        """Test that __init__ raises StorageError if bucket creation fails."""
        from minio.error import S3Error

        mock_client = MagicMock()
        mock_client.bucket_exists = MagicMock(return_value=False)
        mock_client.make_bucket = MagicMock(
            side_effect=S3Error(
                response=MagicMock(),
                code="BucketAlreadyExists",
                message="Bucket creation failed",
                resource="/agent-artifacts",
                request_id="test-request-id",
                host_id="test-host-id",
            )
        )

        with (
            patch("src.storage.artifact_storage.Minio", return_value=mock_client),
            pytest.raises(StorageError),
        ):
            ArtifactStorage()


class TestUploadArtifact:
    """Test upload_artifact method."""

    @pytest.mark.anyio
    async def test_upload_artifact_with_bytes(self, storage):
        """Test uploading artifact with bytes content."""
        content = b"test content"
        workflow_id = "wf-001"
        artifact_path = "code/main.py"

        result = await storage.upload_artifact(
            workflow_id=workflow_id,
            artifact_path=artifact_path,
            content=content,
            content_type="text/plain",
        )

        assert result == f"{workflow_id}/{artifact_path}"
        storage.client.put_object.assert_called_once()

    @pytest.mark.anyio
    async def test_upload_artifact_with_string(self, storage):
        """Test uploading artifact with string content."""
        content = "test content"
        workflow_id = "wf-001"
        artifact_path = "reports/VALIDATION_REPORT.md"

        result = await storage.upload_artifact(
            workflow_id=workflow_id,
            artifact_path=artifact_path,
            content=content,
            content_type="text/markdown",
        )

        assert result == f"{workflow_id}/{artifact_path}"
        storage.client.put_object.assert_called_once()

    @pytest.mark.anyio
    async def test_upload_artifact_with_large_content(self, storage):
        """Test uploading large artifact."""
        content = b"x" * (10 * 1024 * 1024)  # 10MB
        workflow_id = "wf-001"
        artifact_path = "logs/execution.log"

        result = await storage.upload_artifact(
            workflow_id=workflow_id,
            artifact_path=artifact_path,
            content=content,
        )

        assert result == f"{workflow_id}/{artifact_path}"
        storage.client.put_object.assert_called_once()


class TestDownloadArtifact:
    """Test download_artifact method."""

    @pytest.mark.anyio
    async def test_download_artifact_success(self, storage):
        """Test successful artifact download."""
        content = b"test content"
        mock_response = MagicMock()
        mock_response.read = MagicMock(return_value=content)
        mock_response.close = MagicMock()
        mock_response.release_conn = MagicMock()

        storage.client.get_object = MagicMock(return_value=mock_response)

        result = await storage.download_artifact(
            workflow_id="wf-001",
            artifact_path="code/main.py",
        )

        assert result == content
        mock_response.close.assert_called_once()
        mock_response.release_conn.assert_called_once()


class TestListArtifacts:
    """Test list_artifacts method."""

    @pytest.mark.anyio
    async def test_list_artifacts_success(self, storage):
        """Test successful artifact listing."""
        mock_obj1 = MagicMock()
        mock_obj1.object_name = "wf-001/code/main.py"

        mock_obj2 = MagicMock()
        mock_obj2.object_name = "wf-001/reports/VALIDATION_REPORT.md"

        storage.client.list_objects = MagicMock(return_value=[mock_obj1, mock_obj2])

        result = await storage.list_artifacts(workflow_id="wf-001")

        assert len(result) == 2
        assert "code/main.py" in result
        assert "reports/VALIDATION_REPORT.md" in result

    @pytest.mark.anyio
    async def test_list_artifacts_empty(self, storage):
        """Test listing artifacts when none exist."""
        storage.client.list_objects = MagicMock(return_value=[])

        result = await storage.list_artifacts(workflow_id="wf-001")

        assert result == []


class TestDeleteWorkflowArtifacts:
    """Test delete_workflow_artifacts method."""

    @pytest.mark.anyio
    async def test_delete_workflow_artifacts_success(self, storage):
        """Test successful deletion of workflow artifacts."""
        mock_obj1 = MagicMock()
        mock_obj1.object_name = "wf-001/code/main.py"

        mock_obj2 = MagicMock()
        mock_obj2.object_name = "wf-001/reports/VALIDATION_REPORT.md"

        storage.client.list_objects = MagicMock(return_value=[mock_obj1, mock_obj2])
        storage.client.remove_object = MagicMock()

        result = await storage.delete_workflow_artifacts(workflow_id="wf-001")

        assert result == 2
        assert storage.client.remove_object.call_count == 2

    @pytest.mark.anyio
    async def test_delete_workflow_artifacts_empty(self, storage):
        """Test deletion when no artifacts exist."""
        storage.client.list_objects = MagicMock(return_value=[])
        storage.client.remove_object = MagicMock()

        result = await storage.delete_workflow_artifacts(workflow_id="wf-001")

        assert result == 0
        storage.client.remove_object.assert_not_called()


class TestArtifactStorageEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.anyio
    async def test_upload_artifact_with_special_characters_in_path(self, storage):
        """Test uploading artifact with special characters in path."""
        content = b"test"
        workflow_id = "wf-001"
        artifact_path = "reports/VALIDATION_REPORT_2026-01-26.md"

        result = await storage.upload_artifact(
            workflow_id=workflow_id,
            artifact_path=artifact_path,
            content=content,
        )

        assert result == f"{workflow_id}/{artifact_path}"

    @pytest.mark.anyio
    async def test_upload_artifact_with_empty_content(self, storage):
        """Test uploading artifact with empty content."""
        content = b""
        workflow_id = "wf-001"
        artifact_path = "empty.txt"

        result = await storage.upload_artifact(
            workflow_id=workflow_id,
            artifact_path=artifact_path,
            content=content,
        )

        assert result == f"{workflow_id}/{artifact_path}"

    @pytest.mark.anyio
    async def test_upload_artifact_with_unicode_content(self, storage):
        """Test uploading artifact with unicode content."""
        content = "Hello 世界 🌍"
        workflow_id = "wf-001"
        artifact_path = "unicode.txt"

        result = await storage.upload_artifact(
            workflow_id=workflow_id,
            artifact_path=artifact_path,
            content=content,
        )

        assert result == f"{workflow_id}/{artifact_path}"
