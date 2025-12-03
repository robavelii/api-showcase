#!/usr/bin/env python3
"""
Seed script to populate the database with test data.

This script creates sample data for all APIs:
- Users with different roles
- Orders with various statuses
- Files and conversion jobs
- Notifications
- Webhook bins and events

Usage:
    python scripts/seed_data.py

Or with Docker:
    docker compose exec auth-api python scripts/seed_data.py
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Import models
from apps.auth.models.user import User
from apps.file_processor.models.conversion_job import ConversionJob, ConversionStatus
from apps.file_processor.models.file import File, FileStatus
from apps.notifications.models.notification import Notification, NotificationType
from apps.orders.models.order import Order, OrderItem, OrderStatus
from apps.orders.models.webhook_event import WebhookEvent, WebhookStatus
from apps.webhook_tester.models.bin import WebhookBin
from apps.webhook_tester.models.event import BinEvent

# Import password hashing
from shared.auth.password import hash_password

# Database URL from environment or default
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://openapi:openapi_secret@localhost:5432/openapi_showcase"
)


async def clear_existing_data(session: AsyncSession):
    """Clear existing seed data to allow re-running the script."""
    print("Clearing existing data...")
    from sqlalchemy import text

    # Delete in order to respect foreign key constraints
    tables = [
        "bin_events",
        "webhook_bins",
        "notifications",
        "conversion_jobs",
        "files",
        "webhook_events",
        "order_items",
        "orders",
        "refresh_tokens",
        "users",
    ]

    for table in tables:
        try:
            await session.execute(text(f"DELETE FROM {table}"))
        except Exception:
            pass  # Table might not exist

    await session.commit()
    print("  Cleared existing data")


async def create_users(session: AsyncSession) -> list[User]:
    """Create sample users."""
    print("Creating users...")

    users_data = [
        {
            "email": "admin@example.com",
            "password": "Admin123!",
            "full_name": "Admin User",
            "is_superuser": True,
        },
        {
            "email": "john.doe@example.com",
            "password": "Password123!",
            "full_name": "John Doe",
            "is_superuser": False,
        },
        {
            "email": "jane.smith@example.com",
            "password": "Password123!",
            "full_name": "Jane Smith",
            "is_superuser": False,
        },
        {
            "email": "bob.wilson@example.com",
            "password": "Password123!",
            "full_name": "Bob Wilson",
            "is_superuser": False,
        },
        {
            "email": "alice.johnson@example.com",
            "password": "Password123!",
            "full_name": "Alice Johnson",
            "is_superuser": False,
        },
    ]

    users = []
    for data in users_data:
        user = User(
            id=uuid4(),
            email=data["email"],
            password_hash=hash_password(data["password"]),
            full_name=data["full_name"],
            is_superuser=data["is_superuser"],
            is_active=True,
            created_at=datetime.utcnow(),
        )
        session.add(user)
        users.append(user)

    await session.commit()
    print(f"  Created {len(users)} users")
    return users


async def create_orders(session: AsyncSession, users: list[User]) -> list[Order]:
    """Create sample orders."""
    print("Creating orders...")

    orders = []
    statuses = list(OrderStatus)

    for i, user in enumerate(users[1:], 1):  # Skip admin
        for j in range(3):  # 3 orders per user
            # Use the enum value (string) for database compatibility
            status = statuses[(i + j) % len(statuses)]
            order = Order(
                id=uuid4(),
                user_id=user.id,
                status=status.value,
                total_amount=Decimal(f"{(i * 100 + j * 50):.2f}"),
                currency="USD",
                shipping_address={
                    "street": f"{100 + i * 10 + j} Main Street",
                    "city": "New York",
                    "state": "NY",
                    "zip": f"1000{i}",
                    "country": "USA",
                },
                billing_address={
                    "street": f"{100 + i * 10 + j} Main Street",
                    "city": "New York",
                    "state": "NY",
                    "zip": f"1000{i}",
                    "country": "USA",
                },
                created_at=datetime.utcnow() - timedelta(days=j * 7),
            )
            session.add(order)
            orders.append(order)

            # Add order items
            for k in range(2):
                item = OrderItem(
                    id=uuid4(),
                    order_id=order.id,
                    product_id=f"PROD-{i:03d}-{k:02d}",
                    product_name=f"Product {i}-{k}",
                    quantity=k + 1,
                    unit_price=Decimal(f"{25.00 + k * 10:.2f}"),
                    total_price=Decimal(f"{(25.00 + k * 10) * (k + 1):.2f}"),
                )
                session.add(item)

    await session.commit()
    print(f"  Created {len(orders)} orders with items")
    return orders


async def create_webhook_events(session: AsyncSession) -> list[WebhookEvent]:
    """Create sample webhook events."""
    print("Creating webhook events...")

    events_data = [
        {
            "source": "stripe",
            "event_type": "payment_intent.succeeded",
            "payload": {"id": "pi_123", "amount": 5000, "currency": "usd"},
            "status": WebhookStatus.COMPLETED,
        },
        {
            "source": "stripe",
            "event_type": "payment_intent.failed",
            "payload": {
                "id": "pi_456",
                "amount": 3000,
                "currency": "usd",
                "error": "card_declined",
            },
            "status": WebhookStatus.COMPLETED,
        },
        {
            "source": "stripe",
            "event_type": "customer.subscription.created",
            "payload": {"id": "sub_789", "customer": "cus_123", "plan": "pro"},
            "status": WebhookStatus.PENDING,
        },
        {
            "source": "github",
            "event_type": "push",
            "payload": {"ref": "refs/heads/main", "commits": [{"id": "abc123"}]},
            "status": WebhookStatus.COMPLETED,
        },
        {
            "source": "github",
            "event_type": "pull_request.opened",
            "payload": {"number": 42, "title": "Feature: Add new API"},
            "status": WebhookStatus.PROCESSING,
        },
    ]

    events = []
    for i, data in enumerate(events_data):
        event = WebhookEvent(
            id=uuid4(),
            source=data["source"],
            event_type=data["event_type"],
            payload=data["payload"],
            status=data["status"],
            created_at=datetime.utcnow() - timedelta(hours=i),
        )
        session.add(event)
        events.append(event)

    await session.commit()
    print(f"  Created {len(events)} webhook events")
    return events


async def create_files(session: AsyncSession, users: list[User]) -> list[File]:
    """Create sample files and conversion jobs."""
    print("Creating files and conversion jobs...")

    files_data = [
        {"filename": "document.pdf", "content_type": "application/pdf", "size": 1024000},
        {"filename": "image.png", "content_type": "image/png", "size": 512000},
        {
            "filename": "report.docx",
            "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "size": 256000,
        },
        {"filename": "data.csv", "content_type": "text/csv", "size": 128000},
        {
            "filename": "presentation.pptx",
            "content_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "size": 2048000,
        },
    ]

    files = []
    for i, (user, data) in enumerate(zip(users[1:], files_data, strict=False)):
        file = File(
            id=uuid4(),
            user_id=user.id,
            filename=data["filename"],
            content_type=data["content_type"],
            size_bytes=data["size"],
            storage_path=f"/uploads/{user.id}/{data['filename']}",
            status=FileStatus.UPLOADED,
            created_at=datetime.utcnow() - timedelta(days=i),
        )
        session.add(file)
        files.append(file)

        # Create conversion job for some files
        if i < 3:
            job = ConversionJob(
                id=uuid4(),
                file_id=file.id,
                target_format="pdf" if i != 0 else "png",
                status=ConversionStatus.COMPLETED if i == 0 else ConversionStatus.PENDING,
                progress=100 if i == 0 else 0,
                output_path=f"/converted/{file.id}/output.{'pdf' if i != 0 else 'png'}"
                if i == 0
                else None,
                created_at=datetime.utcnow() - timedelta(days=i),
            )
            session.add(job)

    await session.commit()
    print(f"  Created {len(files)} files with conversion jobs")
    return files


async def create_notifications(session: AsyncSession, users: list[User]) -> list[Notification]:
    """Create sample notifications."""
    print("Creating notifications...")

    notifications_data = [
        {
            "title": "Welcome!",
            "message": "Welcome to OpenAPI Showcase. Get started by exploring the APIs.",
            "type": NotificationType.INFO,
        },
        {
            "title": "Order Confirmed",
            "message": "Your order #12345 has been confirmed and is being processed.",
            "type": NotificationType.SUCCESS,
        },
        {
            "title": "Payment Failed",
            "message": "Your payment for order #12346 failed. Please update your payment method.",
            "type": NotificationType.ERROR,
        },
        {
            "title": "New Feature",
            "message": "Check out our new file conversion feature!",
            "type": NotificationType.INFO,
        },
        {
            "title": "Security Alert",
            "message": "A new device logged into your account.",
            "type": NotificationType.WARNING,
        },
        {
            "title": "System Maintenance",
            "message": "Scheduled maintenance on Sunday 2AM-4AM UTC.",
            "type": NotificationType.SYSTEM,
        },
    ]

    notifications = []
    for user in users[1:]:  # Skip admin
        for i, data in enumerate(notifications_data[:3]):  # 3 notifications per user
            notification = Notification(
                id=uuid4(),
                user_id=user.id,
                title=data["title"],
                message=data["message"],
                type=data["type"],
                is_read=i == 0,  # First notification is read
                extra_data={"source": "seed_script"},
                created_at=datetime.utcnow() - timedelta(hours=i * 2),
            )
            session.add(notification)
            notifications.append(notification)

    await session.commit()
    print(f"  Created {len(notifications)} notifications")
    return notifications


async def create_webhook_bins(session: AsyncSession, users: list[User]) -> list[WebhookBin]:
    """Create sample webhook bins and events."""
    print("Creating webhook bins and events...")

    bins = []
    for user in users[1:3]:  # Create bins for first 2 regular users
        bin = WebhookBin(
            id=uuid4(),
            user_id=user.id,
            name=f"{user.full_name}'s Test Bin",
            is_active=True,
            created_at=datetime.utcnow(),
        )
        session.add(bin)
        bins.append(bin)

        # Create some events for each bin
        for j in range(5):
            event = BinEvent(
                id=uuid4(),
                bin_id=bin.id,
                method="POST" if j % 2 == 0 else "GET",
                path=f"/webhook/test/{j}",
                headers={"Content-Type": "application/json", "X-Request-ID": str(uuid4())},
                body='{"event": "test", "data": {"key": "value"}}' if j % 2 == 0 else "",
                content_type="application/json",
                source_ip=f"192.168.1.{100 + j}",
                query_params={"token": f"test_{j}"} if j % 2 == 1 else {},
                received_at=datetime.utcnow() - timedelta(minutes=j * 10),
            )
            session.add(event)

    await session.commit()
    print(f"  Created {len(bins)} webhook bins with events")
    return bins


async def seed_database():
    """Main function to seed the database."""
    print("\n" + "=" * 60)
    print("OpenAPI Showcase - Database Seed Script")
    print("=" * 60 + "\n")

    # Create async engine
    engine = create_async_engine(DATABASE_URL, echo=False)

    # Create async session
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            # Clear existing data first
            await clear_existing_data(session)

            # Create all seed data
            users = await create_users(session)
            await create_orders(session, users)
            await create_webhook_events(session)
            await create_files(session, users)
            await create_notifications(session, users)
            await create_webhook_bins(session, users)

            print("\n" + "=" * 60)
            print("Database seeding completed successfully!")
            print("=" * 60)
            print("\nTest Credentials:")
            print("-" * 40)
            print("Admin User:")
            print("  Email: admin@example.com")
            print("  Password: Admin123!")
            print("\nRegular Users:")
            print("  Email: john.doe@example.com")
            print("  Password: Password123!")
            print("  Email: jane.smith@example.com")
            print("  Password: Password123!")
            print("-" * 40 + "\n")

        except Exception as e:
            print(f"\nError seeding database: {e}")
            await session.rollback()
            raise

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_database())
