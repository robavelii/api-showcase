"""Property-based tests for File Processor API.

**Feature: openapi-showcase**
"""

import io
import tempfile
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import UploadFile
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from apps.file_processor.config import get_file_processor_settings
from apps.file_processor.models.conversion_job import ConversionStatus
from apps.file_processor.models.file import File, FileStatus
from apps.file_processor.schemas.conversion import (
    ConversionJobResponse,
    ConversionStatusResponse,
)
from apps.file_processor.schemas.file import FileMetadata, SignedUrlResponse
from apps.file_processor.services.upload_service import UploadService

# Strategies for generating test data
uuid_strategy = st.uuids()
filename_strategy = st.text(
    min_size=1,
    max_size=50,
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-",
).map(lambda s: f"{s}.pdf")

# Content types that are allowed by default
allowed_content_types = [
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "text/plain",
    "text/csv",
    "application/json",
]
content_type_strategy = st.sampled_from(allowed_content_types)

# File content strategy (small files for testing)
file_content_strategy = st.binary(min_size=1, max_size=1024)

# Target format strategy
target_format_strategy = st.sampled_from(["pdf", "png", "jpg", "webp", "txt"])


class TestFileUploadProperties:
    """
    **Feature: openapi-showcase, Property 14: File upload acceptance**
    """

    @settings(max_examples=100)
    @given(
        filename=filename_strategy,
        content_type=content_type_strategy,
        content=file_content_strategy,
    )
    @pytest.mark.asyncio
    async def test_valid_file_upload_returns_metadata_with_unique_id(
        self, filename: str, content_type: str, content: bytes
    ):
        """
        **Feature: openapi-showcase, Property 14: File upload acceptance**

        For any valid file (within size limits, allowed content type),
        POST /uploads SHALL accept the file and return metadata including
        a unique file ID.
        """
        # Create a temporary directory for storage
        with tempfile.TemporaryDirectory() as tmpdir:
            service = UploadService()
            service.settings.storage_path = tmpdir

            # Create mock UploadFile with headers to set content_type
            file_obj = io.BytesIO(content)
            upload_file = UploadFile(
                filename=filename,
                file=file_obj,
                headers={"content-type": content_type},
            )

            user_id = uuid4()

            # Upload the file
            result = await service.create_upload(upload_file, user_id)

            # Verify result is FileMetadata with required fields
            assert isinstance(result, FileMetadata)
            assert result.id is not None
            assert result.user_id == user_id
            assert result.filename == filename
            assert result.content_type == content_type
            assert result.size_bytes == len(content)
            assert result.status == FileStatus.UPLOADED
            assert result.created_at is not None

    @settings(max_examples=50, deadline=None)  # Multiple uploads can be slow
    @given(
        content=file_content_strategy,
    )
    @pytest.mark.asyncio
    async def test_multiple_uploads_produce_unique_ids(self, content: bytes):
        """
        **Feature: openapi-showcase, Property 14: File upload acceptance**

        For any number of file uploads, each SHALL receive a unique file ID.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            service = UploadService()
            service.settings.storage_path = tmpdir

            file_ids = set()
            num_uploads = 10

            for i in range(num_uploads):
                file_obj = io.BytesIO(content)
                upload_file = UploadFile(
                    filename=f"file_{i}.pdf",
                    file=file_obj,
                    headers={"content-type": "application/pdf"},
                )

                result = await service.create_upload(upload_file, uuid4())

                # Verify ID is unique
                assert result.id not in file_ids
                file_ids.add(result.id)

            # Verify all IDs are unique
            assert len(file_ids) == num_uploads

    @settings(max_examples=50)
    @given(
        filename=filename_strategy,
        content_type=content_type_strategy,
    )
    def test_signed_url_generation_returns_valid_response(self, filename: str, content_type: str):
        """
        **Feature: openapi-showcase, Property 14: File upload acceptance**

        For any valid filename and content type, generate_signed_url SHALL
        return a SignedUrlResponse with file_id, upload_url, and expires_at.
        """
        service = UploadService()
        user_id = uuid4()

        result = service.generate_signed_url(filename, content_type, user_id)

        # Verify result structure
        assert isinstance(result, SignedUrlResponse)
        assert result.file_id is not None
        assert result.upload_url is not None
        assert "signature=" in result.upload_url
        assert result.expires_at > datetime.now(UTC)

    @settings(max_examples=50)
    @given(
        filename=filename_strategy,
        content_type=content_type_strategy,
    )
    def test_signed_url_expiration_is_in_future(self, filename: str, content_type: str):
        """
        **Feature: openapi-showcase, Property 14: File upload acceptance**

        For any signed URL, the expiration time SHALL be in the future.
        """
        service = UploadService()
        user_id = uuid4()

        result = service.generate_signed_url(filename, content_type, user_id)

        # Verify expiration is in the future
        now = datetime.now(UTC)
        assert result.expires_at > now

        # Verify expiration is within expected range (default 1 hour)
        max_expiry = now + timedelta(hours=2)
        assert result.expires_at < max_expiry

    @settings(max_examples=20)
    @given(
        filename=filename_strategy,
    )
    def test_disallowed_content_type_is_rejected(self, filename: str):
        """
        **Feature: openapi-showcase, Property 14: File upload acceptance**

        For any disallowed content type, the upload SHALL be rejected.
        """
        from shared.exceptions.errors import ValidationError

        service = UploadService()
        user_id = uuid4()

        disallowed_types = [
            "application/x-executable",
            "application/x-msdownload",
            "text/html",
        ]

        for content_type in disallowed_types:
            with pytest.raises(ValidationError) as exc_info:
                service.generate_signed_url(filename, content_type, user_id)

            assert "not allowed" in str(exc_info.value.detail).lower()


class TestConversionQueuingProperties:
    """
    **Feature: openapi-showcase, Property 15: Conversion job queuing**
    """

    @settings(max_examples=100)
    @given(
        target_format=target_format_strategy,
    )
    def test_valid_conversion_request_returns_job_id(self, target_format: str):
        """
        **Feature: openapi-showcase, Property 15: Conversion job queuing**

        For any valid conversion request (existing file_id, supported target_format),
        POST /files/convert SHALL queue a job and return a job ID.
        """
        from apps.file_processor.models.file import FileStatus
        from apps.file_processor.services.conversion_service import ConversionService

        service = ConversionService()

        # Create and register a file
        file = File(
            id=uuid4(),
            user_id=uuid4(),
            filename="test.pdf",
            content_type="application/pdf",
            size_bytes=1024,
            storage_path="/tmp/test.pdf",
            status=FileStatus.UPLOADED,
        )
        service.register_file(file)

        # Queue conversion
        result = service.queue_conversion(file.id, target_format)

        # Verify result has job ID and correct status
        assert result.id is not None
        assert result.file_id == file.id
        assert result.target_format == target_format
        assert result.status == ConversionStatus.PENDING
        assert result.progress == 0

    @settings(max_examples=50)
    @given(
        num_jobs=st.integers(min_value=2, max_value=20),
    )
    def test_multiple_conversion_jobs_have_unique_ids(self, num_jobs: int):
        """
        **Feature: openapi-showcase, Property 15: Conversion job queuing**

        For any number of conversion jobs, each SHALL have a unique job ID.
        """
        from apps.file_processor.models.file import FileStatus
        from apps.file_processor.services.conversion_service import ConversionService

        service = ConversionService()
        job_ids = set()

        for i in range(num_jobs):
            # Create and register a file
            file = File(
                id=uuid4(),
                user_id=uuid4(),
                filename=f"test_{i}.pdf",
                content_type="application/pdf",
                size_bytes=1024,
                storage_path=f"/tmp/test_{i}.pdf",
                status=FileStatus.UPLOADED,
            )
            service.register_file(file)

            # Queue conversion
            result = service.queue_conversion(file.id, "png")

            # Verify ID is unique
            assert result.id not in job_ids
            job_ids.add(result.id)

        assert len(job_ids) == num_jobs

    @settings(max_examples=20)
    @given(
        target_format=st.text(min_size=1, max_size=10, alphabet="abcdefghijklmnopqrstuvwxyz"),
    )
    def test_unsupported_format_is_rejected(self, target_format: str):
        """
        **Feature: openapi-showcase, Property 15: Conversion job queuing**

        For any unsupported target format, the conversion request SHALL be rejected.
        """
        from apps.file_processor.models.file import FileStatus
        from apps.file_processor.services.conversion_service import ConversionService
        from shared.exceptions.errors import ValidationError

        # Skip if format happens to be supported
        settings = get_file_processor_settings()
        assume(target_format not in settings.supported_target_formats)

        service = ConversionService()

        # Create and register a file
        file = File(
            id=uuid4(),
            user_id=uuid4(),
            filename="test.pdf",
            content_type="application/pdf",
            size_bytes=1024,
            storage_path="/tmp/test.pdf",
            status=FileStatus.UPLOADED,
        )
        service.register_file(file)

        # Attempt conversion with unsupported format
        with pytest.raises(ValidationError) as exc_info:
            service.queue_conversion(file.id, target_format)

        assert "not supported" in str(exc_info.value.detail).lower()

    def test_nonexistent_file_is_rejected(self):
        """
        **Feature: openapi-showcase, Property 15: Conversion job queuing**

        For any non-existent file_id, the conversion request SHALL be rejected.
        """
        from apps.file_processor.services.conversion_service import ConversionService
        from shared.exceptions.errors import NotFoundError

        service = ConversionService()

        # Attempt conversion with non-existent file
        with pytest.raises(NotFoundError) as exc_info:
            service.queue_conversion(uuid4(), "png")

        assert "not found" in str(exc_info.value.detail).lower()


class TestConversionStatusProperties:
    """
    **Feature: openapi-showcase, Property 16: Status endpoint consistency**
    """

    @settings(max_examples=100)
    @given(
        target_format=target_format_strategy,
    )
    def test_status_returns_valid_enum_and_progress(self, target_format: str):
        """
        **Feature: openapi-showcase, Property 16: Status endpoint consistency**

        For any file with a conversion job, GET /files/{id}/status SHALL return
        a status value from the valid enum and progress between 0-100.
        """
        from apps.file_processor.models.file import FileStatus
        from apps.file_processor.services.conversion_service import ConversionService

        service = ConversionService()

        # Create and register a file
        file = File(
            id=uuid4(),
            user_id=uuid4(),
            filename="test.pdf",
            content_type="application/pdf",
            size_bytes=1024,
            storage_path="/tmp/test.pdf",
            status=FileStatus.UPLOADED,
        )
        service.register_file(file)

        # Queue conversion
        service.queue_conversion(file.id, target_format)

        # Get status
        status = service.get_status(file.id)

        # Verify status is valid enum
        assert status.status in list(ConversionStatus)

        # Verify progress is in valid range
        assert 0 <= status.progress <= 100

        # Verify file_id matches
        assert status.file_id == file.id

    @settings(max_examples=50)
    @given(
        progress_values=st.lists(
            st.integers(min_value=0, max_value=100),
            min_size=1,
            max_size=5,
        ),
    )
    def test_status_reflects_latest_progress(self, progress_values: list[int]):
        """
        **Feature: openapi-showcase, Property 16: Status endpoint consistency**

        For any sequence of progress updates, the status endpoint SHALL
        return the most recent progress value.
        """
        from apps.file_processor.models.file import FileStatus
        from apps.file_processor.services.conversion_service import ConversionService

        service = ConversionService()

        # Create and register a file
        file = File(
            id=uuid4(),
            user_id=uuid4(),
            filename="test.pdf",
            content_type="application/pdf",
            size_bytes=1024,
            storage_path="/tmp/test.pdf",
            status=FileStatus.UPLOADED,
        )
        service.register_file(file)

        # Queue conversion
        job = service.queue_conversion(file.id, "png")

        # Update progress multiple times
        for progress in progress_values:
            service.update_job_status(
                job.id,
                ConversionStatus.PROCESSING,
                progress=progress,
            )

        # Get status
        status = service.get_status(file.id)

        # Verify progress matches last update
        assert status.progress == progress_values[-1]

    @settings(max_examples=50)
    @given(
        status_value=st.sampled_from(
            [
                ConversionStatus.PENDING,
                ConversionStatus.PROCESSING,
                ConversionStatus.COMPLETED,
                ConversionStatus.FAILED,
            ]
        ),
    )
    def test_status_reflects_current_state(self, status_value: ConversionStatus):
        """
        **Feature: openapi-showcase, Property 16: Status endpoint consistency**

        For any status update, the status endpoint SHALL return the current state.
        """
        from apps.file_processor.models.file import FileStatus
        from apps.file_processor.services.conversion_service import ConversionService

        service = ConversionService()

        # Create and register a file
        file = File(
            id=uuid4(),
            user_id=uuid4(),
            filename="test.pdf",
            content_type="application/pdf",
            size_bytes=1024,
            storage_path="/tmp/test.pdf",
            status=FileStatus.UPLOADED,
        )
        service.register_file(file)

        # Queue conversion
        job = service.queue_conversion(file.id, "png")

        # Update status
        progress = 100 if status_value == ConversionStatus.COMPLETED else 50
        service.update_job_status(job.id, status_value, progress=progress)

        # Get status
        result = service.get_status(file.id)

        # Verify status matches
        assert result.status == status_value

    def test_status_for_nonexistent_job_returns_error(self):
        """
        **Feature: openapi-showcase, Property 16: Status endpoint consistency**

        For any file without a conversion job, the status endpoint SHALL
        return a not found error.
        """
        from apps.file_processor.services.conversion_service import ConversionService
        from shared.exceptions.errors import NotFoundError

        service = ConversionService()

        # Attempt to get status for non-existent file
        with pytest.raises(NotFoundError) as exc_info:
            service.get_status(uuid4())

        # Check that error message indicates no job was found
        assert "no conversion job found" in str(exc_info.value.detail).lower()


class TestRetryBackoffProperties:
    """
    **Feature: openapi-showcase, Property 17: Task retry with exponential backoff**
    """

    @settings(max_examples=100)
    @given(
        retry_count=st.integers(min_value=0, max_value=10),
        base_delay=st.integers(min_value=1, max_value=120),
    )
    def test_backoff_delay_follows_exponential_pattern(self, retry_count: int, base_delay: int):
        """
        **Feature: openapi-showcase, Property 17: Task retry with exponential backoff**

        For any failing Celery task configured with retries, the retry delays
        SHALL follow exponential backoff pattern (delay doubles with each retry).
        """
        from apps.file_processor.services.backoff import calculate_backoff_delay

        delay = calculate_backoff_delay(retry_count, base_delay)

        # Verify exponential backoff: base_delay * 2^retry_count
        expected_delay = base_delay * (2**retry_count)
        assert delay == expected_delay

    @settings(max_examples=50)
    @given(
        base_delay=st.integers(min_value=1, max_value=60),
    )
    def test_backoff_delay_doubles_with_each_retry(self, base_delay: int):
        """
        **Feature: openapi-showcase, Property 17: Task retry with exponential backoff**

        For consecutive retries, the delay SHALL double each time.
        """
        from apps.file_processor.services.backoff import calculate_backoff_delay

        # Calculate delays for first 5 retries
        delays = [calculate_backoff_delay(i, base_delay) for i in range(5)]

        # Verify each delay is double the previous
        for i in range(1, len(delays)):
            assert delays[i] == delays[i - 1] * 2

    @settings(max_examples=50)
    @given(
        base_delay=st.integers(min_value=1, max_value=60),
    )
    def test_first_retry_uses_base_delay(self, base_delay: int):
        """
        **Feature: openapi-showcase, Property 17: Task retry with exponential backoff**

        For the first retry (retry_count=0), the delay SHALL equal the base delay.
        """
        from apps.file_processor.services.backoff import calculate_backoff_delay

        delay = calculate_backoff_delay(0, base_delay)

        assert delay == base_delay

    @settings(max_examples=50)
    @given(
        retry_count=st.integers(min_value=0, max_value=5),
    )
    def test_backoff_delay_is_always_positive(self, retry_count: int):
        """
        **Feature: openapi-showcase, Property 17: Task retry with exponential backoff**

        For any retry count, the delay SHALL always be positive.
        """
        from apps.file_processor.services.backoff import calculate_backoff_delay

        # Use default base delay from settings
        fp_settings = get_file_processor_settings()
        delay = calculate_backoff_delay(retry_count, fp_settings.task_retry_base_delay)

        assert delay > 0

    def test_task_retry_max_is_configured(self):
        """
        **Feature: openapi-showcase, Property 17: Task retry with exponential backoff**

        The task retry max SHALL be configured to 3 in settings.
        """
        fp_settings = get_file_processor_settings()

        # Verify settings has correct max retries
        assert fp_settings.task_retry_max == 3


class TestFileMetadataSerializationProperties:
    """
    **Feature: openapi-showcase, Property 18: File metadata round-trip**
    """

    @settings(max_examples=100)
    @given(
        filename=filename_strategy,
        content_type=content_type_strategy,
        size_bytes=st.integers(min_value=0, max_value=100 * 1024 * 1024),
    )
    def test_file_metadata_round_trip(self, filename: str, content_type: str, size_bytes: int):
        """
        **Feature: openapi-showcase, Property 18: File metadata round-trip**

        For any valid FileMetadata object, serializing to JSON and deserializing
        back SHALL produce an equivalent FileMetadata object.
        """
        import json

        from apps.file_processor.models.file import FileStatus
        from apps.file_processor.schemas.file import FileMetadata

        # Create original metadata
        original = FileMetadata(
            id=uuid4(),
            user_id=uuid4(),
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            storage_path=f"/storage/{filename}",
            status=FileStatus.UPLOADED,
            created_at=datetime.now(UTC),
            updated_at=None,
        )

        # Serialize to JSON
        json_str = original.model_dump_json()

        # Deserialize back
        json_data = json.loads(json_str)
        restored = FileMetadata.model_validate(json_data)

        # Verify equivalence
        assert restored.id == original.id
        assert restored.user_id == original.user_id
        assert restored.filename == original.filename
        assert restored.content_type == original.content_type
        assert restored.size_bytes == original.size_bytes
        assert restored.storage_path == original.storage_path
        assert restored.status == original.status
        assert restored.updated_at == original.updated_at

    @settings(max_examples=50)
    @given(
        status=st.sampled_from(list(FileStatus)),
    )
    def test_file_metadata_status_round_trip(self, status: FileStatus):
        """
        **Feature: openapi-showcase, Property 18: File metadata round-trip**

        For any FileStatus value, serialization and deserialization SHALL
        preserve the status.
        """
        import json

        from apps.file_processor.schemas.file import FileMetadata

        original = FileMetadata(
            id=uuid4(),
            user_id=uuid4(),
            filename="test.pdf",
            content_type="application/pdf",
            size_bytes=1024,
            storage_path="/storage/test.pdf",
            status=status,
            created_at=datetime.now(UTC),
            updated_at=None,
        )

        # Round trip
        json_str = original.model_dump_json()
        json_data = json.loads(json_str)
        restored = FileMetadata.model_validate(json_data)

        assert restored.status == status

    @settings(max_examples=50)
    @given(
        target_format=target_format_strategy,
        progress=st.integers(min_value=0, max_value=100),
    )
    def test_conversion_job_response_round_trip(self, target_format: str, progress: int):
        """
        **Feature: openapi-showcase, Property 18: File metadata round-trip**

        For any ConversionJobResponse, serialization and deserialization
        SHALL produce an equivalent object.
        """
        import json

        original = ConversionJobResponse(
            id=uuid4(),
            file_id=uuid4(),
            target_format=target_format,
            status=ConversionStatus.PROCESSING,
            progress=progress,
            output_path=None,
            error_message=None,
            started_at=datetime.now(UTC),
            completed_at=None,
            created_at=datetime.now(UTC),
            updated_at=None,
        )

        # Round trip
        json_str = original.model_dump_json()
        json_data = json.loads(json_str)
        restored = ConversionJobResponse.model_validate(json_data)

        assert restored.id == original.id
        assert restored.file_id == original.file_id
        assert restored.target_format == original.target_format
        assert restored.status == original.status
        assert restored.progress == original.progress

    @settings(max_examples=50)
    @given(
        status=st.sampled_from(list(ConversionStatus)),
        progress=st.integers(min_value=0, max_value=100),
    )
    def test_conversion_status_response_round_trip(self, status: ConversionStatus, progress: int):
        """
        **Feature: openapi-showcase, Property 18: File metadata round-trip**

        For any ConversionStatusResponse, serialization and deserialization
        SHALL produce an equivalent object.
        """
        import json

        original = ConversionStatusResponse(
            file_id=uuid4(),
            status=status,
            progress=progress,
            output_path="/output/file.png" if status == ConversionStatus.COMPLETED else None,
            error_message="Error occurred" if status == ConversionStatus.FAILED else None,
        )

        # Round trip
        json_str = original.model_dump_json()
        json_data = json.loads(json_str)
        restored = ConversionStatusResponse.model_validate(json_data)

        assert restored.file_id == original.file_id
        assert restored.status == original.status
        assert restored.progress == original.progress
        assert restored.output_path == original.output_path
        assert restored.error_message == original.error_message
