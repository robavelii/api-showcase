"""Integration tests for the Webhook service.

Tests webhook signature verification and event processing.
"""

import hashlib
import hmac
import time
from uuid import uuid4

import pytest

from apps.orders.services.webhook_service import WebhookService


class TestWebhookSignatureVerification:
    """Tests for Stripe webhook signature verification."""

    @pytest.fixture
    def service(self):
        """Create a fresh WebhookService instance."""
        return WebhookService()

    def test_verify_valid_signature(self, service):
        """Test verification of valid signature."""
        secret = "whsec_test_secret"
        payload = b'{"type": "payment_intent.succeeded"}'
        timestamp = str(int(time.time()))

        # Compute valid signature
        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
        signature = hmac.new(
            secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        sig_header = f"t={timestamp},v1={signature}"

        result = service.verify_stripe_signature(payload, sig_header, secret)

        assert result is True

    def test_verify_invalid_signature(self, service):
        """Test rejection of invalid signature."""
        secret = "whsec_test_secret"
        payload = b'{"type": "payment_intent.succeeded"}'
        timestamp = str(int(time.time()))

        sig_header = f"t={timestamp},v1=invalid_signature"

        result = service.verify_stripe_signature(payload, sig_header, secret)

        assert result is False

    def test_verify_tampered_payload(self, service):
        """Test rejection of tampered payload."""
        secret = "whsec_test_secret"
        original_payload = b'{"type": "payment_intent.succeeded"}'
        tampered_payload = b'{"type": "payment_intent.failed"}'
        timestamp = str(int(time.time()))

        # Sign original payload
        signed_payload = f"{timestamp}.{original_payload.decode('utf-8')}"
        signature = hmac.new(
            secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        sig_header = f"t={timestamp},v1={signature}"

        # Verify with tampered payload
        result = service.verify_stripe_signature(tampered_payload, sig_header, secret)

        assert result is False

    def test_verify_wrong_secret(self, service):
        """Test rejection when using wrong secret."""
        correct_secret = "whsec_correct"
        wrong_secret = "whsec_wrong"
        payload = b'{"type": "test"}'
        timestamp = str(int(time.time()))

        # Sign with wrong secret
        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
        signature = hmac.new(
            wrong_secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        sig_header = f"t={timestamp},v1={signature}"

        # Verify with correct secret
        result = service.verify_stripe_signature(payload, sig_header, correct_secret)

        assert result is False

    def test_verify_expired_timestamp(self, service):
        """Test rejection of expired timestamp."""
        secret = "whsec_test_secret"
        payload = b'{"type": "test"}'
        # Timestamp from 10 minutes ago
        timestamp = str(int(time.time()) - 600)

        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
        signature = hmac.new(
            secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        sig_header = f"t={timestamp},v1={signature}"

        result = service.verify_stripe_signature(payload, sig_header, secret)

        assert result is False

    def test_verify_malformed_signature_header(self, service):
        """Test rejection of malformed signature header."""
        payload = b'{"type": "test"}'

        malformed_headers = [
            "",
            "invalid",
            "t=123",
            "v1=abc",
            "t=abc,v1=def",  # non-numeric timestamp
        ]

        for sig_header in malformed_headers:
            result = service.verify_stripe_signature(payload, sig_header, "secret")
            assert result is False


class TestWebhookProcessing:
    """Tests for webhook event processing."""

    @pytest.fixture
    def service(self):
        """Create a fresh WebhookService instance."""
        return WebhookService()

    def test_process_webhook_success(self, service):
        """Test successful webhook processing."""
        result = service.process_webhook(
            source="stripe",
            event_type="payment_intent.succeeded",
            payload={"id": "pi_123", "amount": 1000},
        )

        assert result.id is not None
        assert result.source == "stripe"
        assert result.event_type == "payment_intent.succeeded"
        assert result.status == "pending"
        assert result.payload["id"] == "pi_123"

    def test_process_webhook_with_signature(self, service):
        """Test webhook processing with signature."""
        result = service.process_webhook(
            source="stripe",
            event_type="charge.succeeded",
            payload={"id": "ch_123"},
            signature="t=123,v1=abc",
        )

        assert result.id is not None


class TestWebhookRetrieval:
    """Tests for webhook retrieval."""

    @pytest.fixture
    def service_with_webhooks(self):
        """Create a service with pre-populated webhooks."""
        service = WebhookService()

        for i in range(5):
            service.process_webhook(
                source="stripe" if i % 2 == 0 else "paypal",
                event_type=f"event.type.{i}",
                payload={"index": i},
            )

        return service

    def test_get_webhook_by_id(self, service_with_webhooks):
        """Test retrieving a webhook by ID."""
        webhook_id = list(service_with_webhooks._webhooks.keys())[0]

        result = service_with_webhooks.get_webhook(webhook_id)

        assert result is not None
        assert result.id == webhook_id

    def test_get_nonexistent_webhook_returns_none(self, service_with_webhooks):
        """Test retrieving non-existent webhook returns None."""
        result = service_with_webhooks.get_webhook(uuid4())

        assert result is None

    def test_list_webhooks(self, service_with_webhooks):
        """Test listing all webhooks."""
        result = service_with_webhooks.list_webhooks(limit=100)

        assert len(result.items) == 5

    def test_list_webhooks_filter_by_source(self, service_with_webhooks):
        """Test filtering webhooks by source."""
        result = service_with_webhooks.list_webhooks(source="stripe", limit=100)

        assert all(w.source == "stripe" for w in result.items)


class TestWebhookStatusManagement:
    """Tests for webhook status management."""

    @pytest.fixture
    def service(self):
        """Create a fresh WebhookService instance."""
        return WebhookService()

    def test_mark_completed(self, service):
        """Test marking webhook as completed."""
        webhook = service.process_webhook(
            source="stripe",
            event_type="test",
            payload={},
        )

        result = service.mark_completed(webhook.id)

        assert result.status == "completed"
        assert result.processed_at is not None

    def test_mark_failed(self, service):
        """Test marking webhook as failed."""
        webhook = service.process_webhook(
            source="stripe",
            event_type="test",
            payload={},
        )

        result = service.mark_failed(webhook.id, "Processing error")

        assert result.status == "failed"
        assert result.error_message == "Processing error"

    def test_retry_webhook(self, service):
        """Test retrying a failed webhook."""
        webhook = service.process_webhook(
            source="stripe",
            event_type="test",
            payload={},
        )
        service.mark_failed(webhook.id, "Error")

        result = service.retry_webhook(webhook.id)

        assert result.status == "pending"
        assert result.retry_count == 1
        assert result.error_message is None

    def test_retry_increments_count(self, service):
        """Test that retry increments retry count."""
        webhook = service.process_webhook(
            source="stripe",
            event_type="test",
            payload={},
        )

        for _ in range(3):
            service.retry_webhook(webhook.id)

        result = service.get_webhook(webhook.id)
        assert result.retry_count == 3


class TestWebhookPagination:
    """Tests for webhook pagination."""

    @pytest.fixture
    def service_with_many_webhooks(self):
        """Create a service with many webhooks."""
        service = WebhookService()

        for i in range(25):
            service.process_webhook(
                source="stripe",
                event_type=f"event.{i}",
                payload={"index": i},
            )

        return service

    def test_pagination_limits_results(self, service_with_many_webhooks):
        """Test that pagination limits results."""
        result = service_with_many_webhooks.list_webhooks(limit=10)

        assert len(result.items) == 10
        assert result.has_more is True
        assert result.next_cursor is not None

    def test_pagination_cursor_continues(self, service_with_many_webhooks):
        """Test that cursor pagination continues correctly."""
        first_page = service_with_many_webhooks.list_webhooks(limit=10)
        second_page = service_with_many_webhooks.list_webhooks(
            cursor=first_page.next_cursor, limit=10
        )

        first_ids = {w.id for w in first_page.items}
        second_ids = {w.id for w in second_page.items}

        assert len(first_ids & second_ids) == 0  # No overlap
