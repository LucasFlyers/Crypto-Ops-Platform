"""
tests/conftest.py
──────────────────
Shared test fixtures and configuration.
Uses an in-memory SQLite equivalent or test PostgreSQL database.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.db.session import Base, get_db
from app.models import Ticket, Classification, FraudFlag, Routing


# ── Test Database ─────────────────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a fresh in-memory database for each test.
    Rolls back after the test to ensure isolation.
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with TestSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(test_db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    HTTP test client with the test DB injected.
    Overrides the get_db dependency for all routes.
    """
    async def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Test Data Factories ────────────────────────────────────────────────────────

def make_ticket_payload(
    user_id: str = "test_user_001",
    wallet_address: str = "0x82fa4b3e2a9dc99d21aa0000f8c7e8b192837465",
    transaction_id: str | None = None,
    message: str = "My withdrawal has been pending for 8 hours",
) -> dict:
    """Factory for ticket creation payloads."""
    payload = {
        "user_id": user_id,
        "wallet_address": wallet_address,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if transaction_id:
        payload["transaction_id"] = transaction_id
    return payload


@pytest_asyncio.fixture
async def sample_ticket(test_db_session: AsyncSession) -> Ticket:
    """Pre-created ticket fixture."""
    ticket = Ticket(
        user_id="test_user_001",
        wallet_address="0x82fa4b3e2a9dc99d21aa0000f8c7e8b192837465",
        transaction_id=f"TX_{uuid.uuid4().hex[:8]}",
        message="My withdrawal has been pending for 8 hours",
        status="pending",
    )
    test_db_session.add(ticket)
    await test_db_session.commit()
    await test_db_session.refresh(ticket)
    return ticket


@pytest_asyncio.fixture
async def classified_ticket(test_db_session: AsyncSession, sample_ticket: Ticket) -> Ticket:
    """Pre-classified ticket fixture."""
    classification = Classification(
        ticket_id=sample_ticket.id,
        category="withdrawal_issue",
        priority="high",
        fraud_score=0.35,
        ai_reasoning="User reports extended pending withdrawal — likely technical delay",
        ai_model_used="gpt-4o",
    )
    test_db_session.add(classification)
    sample_ticket.status = "classified"
    await test_db_session.commit()
    return sample_ticket
