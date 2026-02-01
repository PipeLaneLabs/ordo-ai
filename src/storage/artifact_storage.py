"""
Artifact Storage (MinIO)

S3-compatible artifact storage for code files, reports, and logs.
Implements async operations for uploading, downloading, and listing artifacts.
"""

from __future__ import annotations

import asyncio
import io
from datetime import timedelta

import structlog
from minio import Minio
from minio.error import S3Error

from src.config import settings
from src.exceptions import StorageError


logger = structlog.get_logger(__name__)


class ArtifactStorage:
    """
    MinIO client for artifact storage.

    Provides async interface for storing and retrieving workflow artifacts
    including generated code, reports, and logs.
    """

    def __init__(self) -> None:
        """Initialize MinIO client with configuration from settings."""
        self.client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self.bucket_name = settings.minio_bucket
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        """
        Ensure the configured bucket exists.

        Creates the bucket if it doesn't exist.

        Raises:
            StorageError: If bucket creation fails
        """
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(
                    "minio.bucket.created",
                    bucket=self.bucket_name,
                    endpoint=settings.minio_endpoint,
                )
        except S3Error as e:
            logger.error(
                "minio.bucket.creation_failed",
                bucket=self.bucket_name,
                error=str(e),
            )
            raise StorageError(f"Failed to create bucket: {e}") from e

    async def upload_artifact(
        self,
        workflow_id: str,
        artifact_path: str,
        content: bytes | str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Upload an artifact to MinIO.

        Args:
            workflow_id: Workflow identifier for organizing artifacts
            artifact_path: Relative path within workflow (e.g., 'code/main.py')
            content: File content as bytes or string
            content_type: MIME type of the content

        Returns:
            Full object path in MinIO (workflow_id/artifact_path)

        Raises:
            StorageError: If upload fails

        Example:
            >>> storage = ArtifactStorage()
            >>> path = await storage.upload_artifact(
            ...     "wf-001",
            ...     "reports/VALIDATION_REPORT.md",
            ...     "# Report\\nAll tests passed",
            ...     "text/markdown"
            ... )
        """
        object_name = f"{workflow_id}/{artifact_path}"

        # Convert string to bytes if needed
        content_bytes = content.encode("utf-8") if isinstance(content, str) else content

        content_stream = io.BytesIO(content_bytes)
        content_length = len(content_bytes)

        try:
            # Run blocking MinIO operation in thread pool
            await asyncio.to_thread(
                self.client.put_object,
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=content_stream,
                length=content_length,
                content_type=content_type,
            )

            logger.info(
                "artifact.uploaded",
                workflow_id=workflow_id,
                artifact_path=artifact_path,
                size_bytes=content_length,
                content_type=content_type,
            )

            return object_name

        except S3Error as e:
            logger.error(
                "artifact.upload_failed",
                workflow_id=workflow_id,
                artifact_path=artifact_path,
                error=str(e),
            )
            raise StorageError(f"Failed to upload artifact: {e}") from e

    async def download_artifact(self, workflow_id: str, artifact_path: str) -> bytes:
        """
        Download an artifact from MinIO.

        Args:
            workflow_id: Workflow identifier
            artifact_path: Relative path within workflow

        Returns:
            File content as bytes

        Raises:
            StorageError: If download fails or artifact not found

        Example:
            >>> storage = ArtifactStorage()
            >>> content = await storage.download_artifact(
            ...     "wf-001",
            ...     "code/main.py"
            ... )
        """
        object_name = f"{workflow_id}/{artifact_path}"

        try:
            # Run blocking MinIO operation in thread pool
            response = await asyncio.to_thread(
                self.client.get_object,
                bucket_name=self.bucket_name,
                object_name=object_name,
            )

            content = response.read()
            response.close()
            response.release_conn()

            logger.info(
                "artifact.downloaded",
                workflow_id=workflow_id,
                artifact_path=artifact_path,
                size_bytes=len(content),
            )

            return content

        except S3Error as e:
            logger.error(
                "artifact.download_failed",
                workflow_id=workflow_id,
                artifact_path=artifact_path,
                error=str(e),
            )
            raise StorageError(f"Failed to download artifact: {e}") from e

    async def list_artifacts(self, workflow_id: str) -> list[str]:
        """
        List all artifacts for a workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            List of artifact paths (relative to workflow_id)

        Raises:
            StorageError: If listing fails

        Example:
            >>> storage = ArtifactStorage()
            >>> artifacts = await storage.list_artifacts("wf-001")
            >>> print(artifacts)
            ['code/main.py', 'reports/VALIDATION_REPORT.md']
        """
        prefix = f"{workflow_id}/"

        try:
            # Run blocking MinIO operation in thread pool
            objects = await asyncio.to_thread(
                self.client.list_objects,
                bucket_name=self.bucket_name,
                prefix=prefix,
                recursive=True,
            )

            # Extract relative paths
            artifact_paths = []
            for obj in objects:
                # Remove workflow_id prefix
                relative_path = obj.object_name[len(prefix) :]
                artifact_paths.append(relative_path)

            logger.info(
                "artifacts.listed",
                workflow_id=workflow_id,
                count=len(artifact_paths),
            )

            return artifact_paths

        except S3Error as e:
            logger.error(
                "artifacts.list_failed",
                workflow_id=workflow_id,
                error=str(e),
            )
            raise StorageError(f"Failed to list artifacts: {e}") from e

    async def delete_artifact(self, workflow_id: str, artifact_path: str) -> None:
        """
        Delete an artifact from MinIO.

        Args:
            workflow_id: Workflow identifier
            artifact_path: Relative path within workflow

        Raises:
            StorageError: If deletion fails

        Example:
            >>> storage = ArtifactStorage()
            >>> await storage.delete_artifact("wf-001", "code/main.py")
        """
        object_name = f"{workflow_id}/{artifact_path}"

        try:
            # Run blocking MinIO operation in thread pool
            await asyncio.to_thread(
                self.client.remove_object,
                bucket_name=self.bucket_name,
                object_name=object_name,
            )

            logger.info(
                "artifact.deleted",
                workflow_id=workflow_id,
                artifact_path=artifact_path,
            )

        except S3Error as e:
            logger.error(
                "artifact.deletion_failed",
                workflow_id=workflow_id,
                artifact_path=artifact_path,
                error=str(e),
            )
            raise StorageError(f"Failed to delete artifact: {e}") from e

    async def delete_workflow_artifacts(self, workflow_id: str) -> int:
        """
        Delete all artifacts for a workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Number of artifacts deleted

        Raises:
            StorageError: If deletion fails

        Example:
            >>> storage = ArtifactStorage()
            >>> count = await storage.delete_workflow_artifacts("wf-001")
            >>> print(f"Deleted {count} artifacts")
        """
        prefix = f"{workflow_id}/"

        try:
            # List all objects with prefix
            objects = await asyncio.to_thread(
                self.client.list_objects,
                bucket_name=self.bucket_name,
                prefix=prefix,
                recursive=True,
            )

            # Delete each object
            deleted_count = 0
            for obj in objects:
                await asyncio.to_thread(
                    self.client.remove_object,
                    bucket_name=self.bucket_name,
                    object_name=obj.object_name,
                )
                deleted_count += 1

            logger.info(
                "workflow_artifacts.deleted",
                workflow_id=workflow_id,
                count=deleted_count,
            )

            return deleted_count

        except S3Error as e:
            logger.error(
                "workflow_artifacts.deletion_failed",
                workflow_id=workflow_id,
                error=str(e),
            )
            raise StorageError(f"Failed to delete workflow artifacts: {e}") from e

    async def get_artifact_url(
        self, workflow_id: str, artifact_path: str, expires_hours: int = 24
    ) -> str:
        """
        Generate a presigned URL for artifact download.

        Args:
            workflow_id: Workflow identifier
            artifact_path: Relative path within workflow
            expires_hours: URL expiration time in hours (default: 24)

        Returns:
            Presigned URL for direct download

        Raises:
            StorageError: If URL generation fails

        Example:
            >>> storage = ArtifactStorage()
            >>> url = await storage.get_artifact_url(
            ...     "wf-001",
            ...     "reports/VALIDATION_REPORT.md",
            ...     expires_hours=1
            ... )
        """
        object_name = f"{workflow_id}/{artifact_path}"
        expires = timedelta(hours=expires_hours)

        try:
            # Run blocking MinIO operation in thread pool
            url = await asyncio.to_thread(
                self.client.presigned_get_object,
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=expires,
            )

            logger.info(
                "artifact.url_generated",
                workflow_id=workflow_id,
                artifact_path=artifact_path,
                expires_hours=expires_hours,
            )

            return url

        except S3Error as e:
            logger.error(
                "artifact.url_generation_failed",
                workflow_id=workflow_id,
                artifact_path=artifact_path,
                error=str(e),
            )
            raise StorageError(f"Failed to generate artifact URL: {e}") from e


# Global artifact storage instance (lazy-loaded to avoid connection
# errors during testing)
# artifact_storage = ArtifactStorage()
