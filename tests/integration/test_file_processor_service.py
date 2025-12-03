"""Integration tests for the File Processor service.

Tests file upload and conversion functionality.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from apps.file_processor.models.conversion_job import ConversionStatus
from apps.file_processor.models.file import File, FileStatus
from apps.file_processor.services.conversion_service import ConversionService
from apps.file_processor.services.upload_service import UploadService
from shared.exceptions.errors import NotFoundError, ValidationError


class TestConversionServiceQueueing:
    """Tests for conversion job queuing."""

    @pytest.fixture
    def service(self):
        """Create a fresh ConversionService instance."""
        return ConversionService()

    @pytest.fixture
    def registered_file(self, service):
        """Create and register a file for testing."""
        file = File(
            id=uuid4(),
            user_id=uuid4(),
            filename="test.pdf",
            content_type="application/pdf",
            size_bytes=1024,
            storage_path="/tmp/test.pdf",
            status=FileStatus.UPLOADED,
            created_at=datetime.now(UTC),
        )
        service.register_file(file)
        return file

    def test_queue_conversion_success(self, service, registered_file):
        """Test successful conversion job queuing."""
        result = service.queue_conversion(registered_file.id, "png")

        assert result.id is not None
        assert result.file_id == registered_file.id
        assert result.target_format == "png"
        assert result.status == ConversionStatus.PENDING
        assert result.progress == 0

    def test_queue_conversion_invalid_format_raises_error(self, service, registered_file):
        """Test that invalid target format raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            service.queue_conversion(registered_file.id, "invalid_format")

        assert "not supported" in str(exc_info.value.detail)

    def test_queue_conversion_nonexistent_file_raises_error(self, service):
        """Test that non-existent file raises NotFoundError."""
        with pytest.raises(NotFoundError) as exc_info:
            service.queue_conversion(uuid4(), "pdf")

        assert "not found" in str(exc_info.value.detail)


class TestConversionServiceStatus:
    """Tests for conversion status retrieval."""

    @pytest.fixture
    def service(self):
        """Create a fresh ConversionService instance."""
        return ConversionService()

    @pytest.fixture
    def file_with_job(self, service):
        """Create a file with a conversion job."""
        file = File(
            id=uuid4(),
            user_id=uuid4(),
            filename="test.pdf",
            content_type="application/pdf",
            size_bytes=1024,
            storage_path="/tmp/test.pdf",
            status=FileStatus.UPLOADED,
            created_at=datetime.now(UTC),
        )
        service.register_file(file)
        service.queue_conversion(file.id, "png")
        return file

    def test_get_status_success(self, service, file_with_job):
        """Test getting conversion status."""
        result = service.get_status(file_with_job.id)

        assert result.file_id == file_with_job.id
        assert result.status == ConversionStatus.PENDING
        assert result.progress == 0

    def test_get_status_no_job_raises_error(self, service):
        """Test that getting status for file without job raises NotFoundError."""
        file = File(
            id=uuid4(),
            user_id=uuid4(),
            filename="test.pdf",
            content_type="application/pdf",
            size_bytes=1024,
            storage_path="/tmp/test.pdf",
            status=FileStatus.UPLOADED,
            created_at=datetime.now(UTC),
        )
        service.register_file(file)

        with pytest.raises(NotFoundError) as exc_info:
            service.get_status(file.id)

        assert "No conversion job found" in str(exc_info.value.detail)


class TestConversionServiceJobManagement:
    """Tests for conversion job management."""

    @pytest.fixture
    def service(self):
        """Create a fresh ConversionService instance."""
        return ConversionService()

    @pytest.fixture
    def job(self, service):
        """Create a conversion job."""
        file = File(
            id=uuid4(),
            user_id=uuid4(),
            filename="test.pdf",
            content_type="application/pdf",
            size_bytes=1024,
            storage_path="/tmp/test.pdf",
            status=FileStatus.UPLOADED,
            created_at=datetime.now(UTC),
        )
        service.register_file(file)
        result = service.queue_conversion(file.id, "png")
        return result

    def test_get_job_success(self, service, job):
        """Test getting a job by ID."""
        result = service.get_job(job.id)

        assert result.id == job.id
        assert result.status == ConversionStatus.PENDING

    def test_get_job_nonexistent_raises_error(self, service):
        """Test that getting non-existent job raises NotFoundError."""
        with pytest.raises(NotFoundError) as exc_info:
            service.get_job(uuid4())

        assert "not found" in str(exc_info.value.detail)

    def test_update_job_status_to_processing(self, service, job):
        """Test updating job status to processing."""
        result = service.update_job_status(job.id, ConversionStatus.PROCESSING, progress=10)

        assert result.status == ConversionStatus.PROCESSING
        assert result.progress == 10
        assert result.started_at is not None

    def test_update_job_status_to_completed(self, service, job):
        """Test updating job status to completed."""
        result = service.update_job_status(
            job.id,
            ConversionStatus.COMPLETED,
            progress=100,
            output_path="/tmp/output.docx",
        )

        assert result.status == ConversionStatus.COMPLETED
        assert result.progress == 100
        assert result.output_path == "/tmp/output.docx"
        assert result.completed_at is not None

    def test_update_job_status_to_failed(self, service, job):
        """Test updating job status to failed."""
        result = service.update_job_status(
            job.id,
            ConversionStatus.FAILED,
            error_message="Conversion failed: unsupported format",
        )

        assert result.status == ConversionStatus.FAILED
        assert result.error_message == "Conversion failed: unsupported format"
        assert result.completed_at is not None


class TestUploadServiceValidation:
    """Tests for upload validation."""

    @pytest.fixture
    def service(self):
        """Create a fresh UploadService instance."""
        return UploadService()

    def test_validate_content_type_allowed(self, service):
        """Test that allowed content types pass validation."""
        # Should not raise
        service._validate_content_type("application/pdf")
        service._validate_content_type("image/png")
        service._validate_content_type("image/jpeg")

    def test_validate_content_type_not_allowed_raises_error(self, service):
        """Test that disallowed content types raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            service._validate_content_type("application/x-executable")

        assert "not allowed" in str(exc_info.value.detail)

    def test_validate_file_size_within_limit(self, service):
        """Test that files within size limit pass validation."""
        # Should not raise
        service._validate_file_size(1024 * 1024)  # 1MB

    def test_validate_file_size_exceeds_limit_raises_error(self, service):
        """Test that files exceeding size limit raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            service._validate_file_size(1024 * 1024 * 1024)  # 1GB

        assert "exceeds maximum" in str(exc_info.value.detail)


class TestUploadServiceSignedUrl:
    """Tests for signed URL generation."""

    @pytest.fixture
    def service(self):
        """Create a fresh UploadService instance."""
        return UploadService()

    def test_generate_signed_url_success(self, service):
        """Test successful signed URL generation."""
        result = service.generate_signed_url(
            filename="test.pdf",
            content_type="application/pdf",
            user_id=uuid4(),
        )

        assert result.file_id is not None
        assert result.upload_url is not None
        assert "storage.example.com" in result.upload_url
        assert result.expires_at is not None

    def test_generate_signed_url_invalid_content_type_raises_error(self, service):
        """Test that invalid content type raises ValidationError."""
        with pytest.raises(ValidationError):
            service.generate_signed_url(
                filename="test.exe",
                content_type="application/x-executable",
                user_id=uuid4(),
            )

    def test_signed_url_contains_file_id(self, service):
        """Test that signed URL contains the file ID."""
        result = service.generate_signed_url(
            filename="test.pdf",
            content_type="application/pdf",
            user_id=uuid4(),
        )

        assert str(result.file_id) in result.upload_url

    def test_signed_url_contains_signature(self, service):
        """Test that signed URL contains a signature."""
        result = service.generate_signed_url(
            filename="test.pdf",
            content_type="application/pdf",
            user_id=uuid4(),
        )

        assert "signature=" in result.upload_url


class TestUploadServiceSignatureValidation:
    """Tests for signed URL validation."""

    @pytest.fixture
    def service(self):
        """Create a fresh UploadService instance."""
        return UploadService()

    def test_validate_valid_signature(self, service):
        """Test validating a valid signature."""
        import time

        file_id = uuid4()
        signature = "a" * 64  # Valid SHA256 hex length
        expires = int(time.time()) + 3600  # 1 hour from now

        result = service.validate_signed_url(file_id, signature, expires)

        assert result is True

    def test_validate_expired_signature(self, service):
        """Test that expired signatures are rejected."""
        import time

        file_id = uuid4()
        signature = "a" * 64
        expires = int(time.time()) - 3600  # 1 hour ago

        result = service.validate_signed_url(file_id, signature, expires)

        assert result is False

    def test_validate_invalid_signature_length(self, service):
        """Test that invalid signature length is rejected."""
        import time

        file_id = uuid4()
        signature = "short"  # Invalid length
        expires = int(time.time()) + 3600

        result = service.validate_signed_url(file_id, signature, expires)

        assert result is False


class TestUploadServiceFileUpload:
    """Tests for file upload handling."""

    @pytest.fixture
    def service(self):
        """Create a fresh UploadService instance."""
        return UploadService()

    @pytest.mark.asyncio
    async def test_create_upload_success(self, service, tmp_path):
        """Test successful file upload."""
        # Mock the storage path
        with patch.object(service.settings, "storage_path", str(tmp_path)):
            mock_file = AsyncMock()
            mock_file.filename = "test.pdf"
            mock_file.content_type = "application/pdf"
            mock_file.read = AsyncMock(return_value=b"test content")

            result = await service.create_upload(mock_file, uuid4())

            assert result.id is not None
            assert result.filename == "test.pdf"
            assert result.content_type == "application/pdf"
            assert result.size_bytes == len(b"test content")
            assert result.status == FileStatus.UPLOADED

    @pytest.mark.asyncio
    async def test_create_upload_invalid_content_type_raises_error(self, service):
        """Test that invalid content type raises ValidationError."""
        mock_file = AsyncMock()
        mock_file.filename = "test.exe"
        mock_file.content_type = "application/x-executable"
        mock_file.read = AsyncMock(return_value=b"test")

        with pytest.raises(ValidationError):
            await service.create_upload(mock_file, uuid4())

    @pytest.mark.asyncio
    async def test_create_upload_file_too_large_raises_error(self, service):
        """Test that oversized file raises ValidationError."""
        mock_file = AsyncMock()
        mock_file.filename = "test.pdf"
        mock_file.content_type = "application/pdf"
        # Create content larger than max size
        mock_file.read = AsyncMock(return_value=b"x" * (service.settings.max_upload_size + 1))

        with pytest.raises(ValidationError) as exc_info:
            await service.create_upload(mock_file, uuid4())

        assert "exceeds maximum" in str(exc_info.value.detail)
