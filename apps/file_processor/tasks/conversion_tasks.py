"""Celery tasks for file conversion.

Provides background task processing for file conversions with retry logic
and exponential backoff.
"""

import logging
import os
import time
from datetime import datetime, UTC
from uuid import UUID

import httpx
from celery import shared_task

from apps.file_processor.config import get_file_processor_settings
from apps.file_processor.models.conversion_job import ConversionStatus
from apps.file_processor.schemas.conversion import ConversionWebhookPayload
from apps.file_processor.services.backoff import calculate_backoff_delay

logger = logging.getLogger(__name__)
settings = get_file_processor_settings()


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
)
def process_conversion_task(self, job_id: str) -> dict:
    """Process a file conversion job asynchronously.

    This task processes file conversions with automatic retry on failure.
    Uses exponential backoff for retries.

    Args:
        job_id: UUID string of the conversion job

    Returns:
        Processing result dictionary
    """
    from apps.file_processor.services.conversion_service import get_conversion_service
    
    conversion_service = get_conversion_service()
    job_uuid = UUID(job_id)

    try:
        logger.info(f"Processing conversion job {job_id}, attempt {self.request.retries + 1}")

        # Get the job
        job = conversion_service.get_job(job_uuid)
        
        # Update status to processing
        conversion_service.update_job_status(
            job_uuid,
            ConversionStatus.PROCESSING,
            progress=0,
        )

        # Simulate conversion process with progress updates
        result = _perform_conversion(
            job_uuid,
            job.file_id,
            job.target_format,
            conversion_service,
        )

        if result["success"]:
            # Update status to completed
            conversion_service.update_job_status(
                job_uuid,
                ConversionStatus.COMPLETED,
                progress=100,
                output_path=result.get("output_path"),
            )
            
            # Trigger webhook if configured
            _trigger_completion_webhook(job_uuid, job.file_id, result.get("output_path"))
            
            logger.info(f"Conversion job {job_id} completed successfully")
            return {"status": "completed", "job_id": job_id}
        else:
            raise Exception(result.get("error", "Conversion failed"))

    except Exception as exc:
        logger.error(f"Error processing conversion job {job_id}: {exc}")

        # Check if we've exhausted retries
        if self.request.retries >= self.max_retries:
            conversion_service.update_job_status(
                job_uuid,
                ConversionStatus.FAILED,
                progress=0,
                error_message=str(exc),
            )
            
            # Trigger failure webhook
            _trigger_failure_webhook(job_uuid, job.file_id, str(exc))
            
            logger.error(f"Conversion job {job_id} failed after {self.max_retries} retries")
            return {"status": "failed", "job_id": job_id, "error": str(exc)}

        # Calculate backoff delay
        delay = calculate_backoff_delay(
            self.request.retries,
            settings.task_retry_base_delay,
        )
        
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=delay)


def _perform_conversion(
    job_id: UUID,
    file_id: UUID,
    target_format: str,
    conversion_service,
) -> dict:
    """Perform the actual file conversion.

    Args:
        job_id: Conversion job ID
        file_id: Source file ID
        target_format: Target format
        conversion_service: Conversion service instance

    Returns:
        Result dictionary with success flag and output path
    """
    try:
        # Get file info (in production, this would fetch from database)
        # For demo, we simulate the conversion process
        
        # Simulate progress updates
        for progress in [10, 25, 50, 75, 90]:
            conversion_service.update_job_status(
                job_id,
                ConversionStatus.PROCESSING,
                progress=progress,
            )
            # Small delay to simulate processing
            time.sleep(0.01)

        # Generate output path
        output_path = f"{settings.storage_path}/converted/{job_id}.{target_format}"
        
        # In production, actual conversion would happen here
        # For demo, we just create an empty file
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(b"converted content")

        return {
            "success": True,
            "output_path": output_path,
        }

    except Exception as e:
        logger.error(f"Conversion error for job {job_id}: {e}")
        return {
            "success": False,
            "error": str(e),
        }


def _trigger_completion_webhook(
    job_id: UUID,
    file_id: UUID,
    output_path: str | None,
) -> None:
    """Trigger webhook on conversion completion.

    Args:
        job_id: Conversion job ID
        file_id: Source file ID
        output_path: Path to converted file
    """
    webhook_url = settings.conversion_webhook_url
    if not webhook_url:
        return

    try:
        payload = ConversionWebhookPayload(
            job_id=job_id,
            file_id=file_id,
            status=ConversionStatus.COMPLETED,
            output_path=output_path,
            error_message=None,
            completed_at=datetime.now(UTC),
        )

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                webhook_url,
                json=payload.model_dump(mode="json"),
            )
            response.raise_for_status()
            logger.info(f"Completion webhook sent for job {job_id}")

    except Exception as e:
        logger.error(f"Failed to send completion webhook for job {job_id}: {e}")


def _trigger_failure_webhook(
    job_id: UUID,
    file_id: UUID,
    error_message: str,
) -> None:
    """Trigger webhook on conversion failure.

    Args:
        job_id: Conversion job ID
        file_id: Source file ID
        error_message: Error message
    """
    webhook_url = settings.conversion_webhook_url
    if not webhook_url:
        return

    try:
        payload = ConversionWebhookPayload(
            job_id=job_id,
            file_id=file_id,
            status=ConversionStatus.FAILED,
            output_path=None,
            error_message=error_message,
            completed_at=datetime.now(UTC),
        )

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                webhook_url,
                json=payload.model_dump(mode="json"),
            )
            response.raise_for_status()
            logger.info(f"Failure webhook sent for job {job_id}")

    except Exception as e:
        logger.error(f"Failed to send failure webhook for job {job_id}: {e}")


# Expose the backoff calculation for testing
__all__ = ["process_conversion_task", "calculate_backoff_delay"]
