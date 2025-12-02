"""Webhook routes for file processor.

Provides endpoints for conversion completion webhooks.
"""

from fastapi import APIRouter, Request, status

from apps.file_processor.schemas.conversion import ConversionWebhookPayload

router = APIRouter()


@router.post(
    "/webhooks/convert",
    status_code=status.HTTP_200_OK,
    summary="Conversion webhook",
    description="Receive conversion completion webhook notifications.",
    responses={
        200: {
            "description": "Webhook received",
            "content": {
                "application/json": {
                    "example": {
                        "status": "received",
                        "message": "Webhook processed successfully",
                    }
                }
            },
        },
    },
)
async def conversion_webhook(
    payload: ConversionWebhookPayload,
    request: Request,
) -> dict:
    """Receive conversion completion webhook notifications.
    
    This endpoint receives notifications when file conversions complete
    or fail. In a real application, this would trigger downstream
    processing or notifications.
    """
    # Log the webhook receipt
    # In production, you would process this webhook appropriately
    
    return {
        "status": "received",
        "message": "Webhook processed successfully",
        "job_id": str(payload.job_id),
        "conversion_status": payload.status.value,
    }
