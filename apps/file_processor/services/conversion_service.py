"""Conversion service for file processor.

Handles file conversion job queuing and status tracking.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from apps.file_processor.config import get_file_processor_settings
from apps.file_processor.models.conversion_job import ConversionJob, ConversionStatus
from apps.file_processor.models.file import File
from apps.file_processor.schemas.conversion import (
    ConversionJobResponse,
    ConversionStatusResponse,
)
from shared.exceptions.errors import NotFoundError, ValidationError


class ConversionService:
    """Service for handling file conversion operations."""

    def __init__(self):
        """Initialize conversion service."""
        self.settings = get_file_processor_settings()
        # In-memory storage for demo purposes
        # In production, this would use database
        self._jobs: dict[UUID, ConversionJob] = {}
        self._files: dict[UUID, File] = {}

    def _validate_target_format(self, target_format: str) -> None:
        """Validate that target format is supported.

        Args:
            target_format: Target format to validate

        Raises:
            ValidationError: If format is not supported
        """
        if target_format not in self.settings.supported_target_formats:
            raise ValidationError(
                detail=f"Target format '{target_format}' is not supported. "
                f"Supported formats: {', '.join(self.settings.supported_target_formats)}"
            )

    def _get_file(self, file_id: UUID) -> File:
        """Get file by ID.

        Args:
            file_id: File ID to look up

        Returns:
            File object

        Raises:
            NotFoundError: If file not found
        """
        if file_id not in self._files:
            raise NotFoundError(detail=f"File with ID {file_id} not found")
        return self._files[file_id]

    def queue_conversion(self, file_id: UUID, target_format: str) -> ConversionJobResponse:
        """Queue a file conversion job.

        Args:
            file_id: ID of the file to convert
            target_format: Target format for conversion

        Returns:
            ConversionJobResponse with job details

        Raises:
            NotFoundError: If file not found
            ValidationError: If target format not supported
        """
        # Validate target format
        self._validate_target_format(target_format)

        # Get file (validates it exists)
        self._get_file(file_id)

        # Create conversion job
        now = datetime.now(UTC)
        job = ConversionJob(
            id=uuid4(),
            file_id=file_id,
            target_format=target_format,
            status=ConversionStatus.PENDING,
            progress=0,
            created_at=now,
        )

        # Store job
        self._jobs[job.id] = job

        # In production, this would queue a Celery task
        # from apps.file_processor.tasks.conversion_tasks import process_conversion_task
        # process_conversion_task.delay(str(job.id))

        return ConversionJobResponse(
            id=job.id,
            file_id=job.file_id,
            target_format=job.target_format,
            status=job.status,
            progress=job.progress,
            output_path=job.output_path,
            error_message=job.error_message,
            started_at=job.started_at,
            completed_at=job.completed_at,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )

    def get_status(self, file_id: UUID) -> ConversionStatusResponse:
        """Get conversion status for a file.

        Args:
            file_id: ID of the file to check

        Returns:
            ConversionStatusResponse with current status

        Raises:
            NotFoundError: If no conversion job found for file
        """
        # Find the most recent job for this file
        file_jobs = [job for job in self._jobs.values() if job.file_id == file_id]

        if not file_jobs:
            raise NotFoundError(detail=f"No conversion job found for file {file_id}")

        # Get the most recent job
        latest_job = max(file_jobs, key=lambda j: j.created_at)

        return ConversionStatusResponse(
            file_id=file_id,
            status=latest_job.status,
            progress=latest_job.progress,
            output_path=latest_job.output_path,
            error_message=latest_job.error_message,
        )

    def get_job(self, job_id: UUID) -> ConversionJob:
        """Get conversion job by ID.

        Args:
            job_id: Job ID to look up

        Returns:
            ConversionJob object

        Raises:
            NotFoundError: If job not found
        """
        if job_id not in self._jobs:
            raise NotFoundError(detail=f"Conversion job {job_id} not found")
        return self._jobs[job_id]

    def update_job_status(
        self,
        job_id: UUID,
        status: ConversionStatus,
        progress: int = 0,
        output_path: str | None = None,
        error_message: str | None = None,
    ) -> ConversionJob:
        """Update conversion job status.

        Args:
            job_id: Job ID to update
            status: New status
            progress: Progress percentage (0-100)
            output_path: Path to output file (if completed)
            error_message: Error message (if failed)

        Returns:
            Updated ConversionJob

        Raises:
            NotFoundError: If job not found
        """
        job = self.get_job(job_id)
        now = datetime.now(UTC)

        job.status = status
        job.progress = progress
        job.updated_at = now

        if status == ConversionStatus.PROCESSING and job.started_at is None:
            job.started_at = now

        if status in (ConversionStatus.COMPLETED, ConversionStatus.FAILED):
            job.completed_at = now

        if output_path:
            job.output_path = output_path

        if error_message:
            job.error_message = error_message

        return job

    def register_file(self, file: File) -> None:
        """Register a file in the service (for testing/demo).

        Args:
            file: File to register
        """
        self._files[file.id] = file


# Singleton instance
_conversion_service: ConversionService | None = None


def get_conversion_service() -> ConversionService:
    """Get conversion service instance."""
    global _conversion_service
    if _conversion_service is None:
        _conversion_service = ConversionService()
    return _conversion_service
