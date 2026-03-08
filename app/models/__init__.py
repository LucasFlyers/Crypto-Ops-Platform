"""
app/models/__init__.py
Import all models here so Alembic autogenerate can discover them.
"""
from app.models.ticket import Ticket  # noqa: F401
from app.models.classification import Classification  # noqa: F401
from app.models.fraud import FraudFlag  # noqa: F401
from app.models.routing import Routing  # noqa: F401

__all__ = ["Ticket", "Classification", "FraudFlag", "Routing"]
