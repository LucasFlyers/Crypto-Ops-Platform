"""
app/schemas/ticket.py
──────────────────────
Pydantic v2 schemas for ticket API layer.
Strict validation — reject bad data at the boundary, not deep in the system.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class TicketCreateRequest(BaseModel):
    """Incoming ticket from external system or support tool."""

    user_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Internal user identifier",
        examples=["48291"],
    )
    wallet_address: Optional[str] = Field(
        default=None,
        max_length=256,
        description="Blockchain wallet address (optional)",
        examples=["0x82fa4b3e2a9dc99d21aa0000f8c7e8b192837465"],
    )
    transaction_id: Optional[str] = Field(
        default=None,
        max_length=256,
        description="Transaction ID if issue relates to a specific tx",
        examples=["TX192838"],
    )
    message: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="User's description of the issue",
        examples=["My withdrawal has been pending for 8 hours"],
    )
    timestamp: Optional[datetime] = Field(
        default=None,
        description="Event timestamp (defaults to server time if not provided)",
    )

    @field_validator("wallet_address")
    @classmethod
    def validate_wallet_address(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        # Basic ETH address validation (0x + 40 hex chars) or other formats
        if v.startswith("0x") and len(v) != 42:
            raise ValueError(
                f"Ethereum wallet address must be 42 characters, got {len(v)}"
            )
        return v.lower() if v.startswith("0x") else v

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("user_id cannot be blank")
        return v.strip()


class TicketResponse(BaseModel):
    """Response payload after successful ticket creation."""

    ticket_id: uuid.UUID
    status: str
    message: str = "Ticket received and queued for processing"

    model_config = {"from_attributes": True}


class TicketDetailResponse(BaseModel):
    """Full ticket details including classification and routing."""

    id: uuid.UUID
    user_id: str
    wallet_address: Optional[str]
    transaction_id: Optional[str]
    message: str
    status: str
    created_at: datetime
    updated_at: datetime
    classification: Optional["ClassificationDetail"] = None
    routing: Optional["RoutingDetail"] = None

    model_config = {"from_attributes": True}


class ClassificationDetail(BaseModel):
    category: str
    priority: str
    fraud_score: float
    ai_reasoning: str
    processed_at: datetime

    model_config = {"from_attributes": True}


class RoutingDetail(BaseModel):
    assigned_team: str
    severity_level: str
    rule_matched: str
    resolved: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# Rebuild models to resolve forward references
TicketDetailResponse.model_rebuild()
