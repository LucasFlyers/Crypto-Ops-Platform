"""
tests/test_api/test_tickets.py
───────────────────────────────
Tests for ticket ingestion API.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_ticket_success(client: AsyncClient):
    """POST /tickets returns 202 with ticket_id."""
    with patch(
        "app.services.ticket_service.TicketService.dispatch_classification",
        new_callable=AsyncMock,
    ):
        response = await client.post(
            "/api/v1/tickets",
            json={
                "user_id": "user_001",
                "wallet_address": "0x82fa4b3e2a9dc99d21aa0000f8c7e8b192837465",
                "transaction_id": "TX_001",
                "message": "My withdrawal has been pending for 8 hours",
            },
        )

    assert response.status_code == 202
    data = response.json()
    assert "ticket_id" in data
    assert data["status"] == "pending"
    # Validate it's a valid UUID
    uuid.UUID(data["ticket_id"])


@pytest.mark.asyncio
async def test_create_ticket_idempotency(client: AsyncClient):
    """Submitting same transaction_id twice returns the existing ticket."""
    payload = {
        "user_id": "user_002",
        "wallet_address": "0x82fa4b3e2a9dc99d21aa0000f8c7e8b192837465",
        "transaction_id": "TX_DUPLICATE",
        "message": "My withdrawal has been pending for 8 hours",
    }

    with patch(
        "app.services.ticket_service.TicketService.dispatch_classification",
        new_callable=AsyncMock,
    ):
        r1 = await client.post("/api/v1/tickets", json=payload)
        r2 = await client.post("/api/v1/tickets", json=payload)

    assert r1.status_code == 202
    assert r2.status_code == 202

    d1 = r1.json()
    d2 = r2.json()

    # Both should return the same ticket_id
    assert d1["ticket_id"] == d2["ticket_id"]
    assert d2["status"] == "already_exists"


@pytest.mark.asyncio
async def test_create_ticket_invalid_message(client: AsyncClient):
    """Message too short should fail validation."""
    response = await client.post(
        "/api/v1/tickets",
        json={
            "user_id": "user_003",
            "message": "short",  # Less than 10 chars
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_ticket_invalid_wallet(client: AsyncClient):
    """Malformed ETH wallet address should fail validation."""
    response = await client.post(
        "/api/v1/tickets",
        json={
            "user_id": "user_004",
            "wallet_address": "0xinvalidaddress",  # 0x but wrong length
            "message": "My withdrawal has been pending for 8 hours",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_ticket_not_found(client: AsyncClient):
    """GET /tickets/{unknown_id} returns 404."""
    fake_id = uuid.uuid4()
    response = await client.get(f"/api/v1/tickets/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_tickets(client: AsyncClient):
    """GET /tickets returns paginated list."""
    with patch(
        "app.services.ticket_service.TicketService.dispatch_classification",
        new_callable=AsyncMock,
    ):
        await client.post(
            "/api/v1/tickets",
            json={
                "user_id": "user_list_001",
                "message": "Test ticket for listing purposes here",
            },
        )

    response = await client.get("/api/v1/tickets?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert "tickets" in data
    assert "total" in data
    assert isinstance(data["tickets"], list)


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """GET /health returns 200."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
