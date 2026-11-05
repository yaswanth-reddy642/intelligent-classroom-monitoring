"""MongoDB connection manager using Motor async driver."""

import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


async def connect_db(uri: str, database_name: str) -> AsyncIOMotorDatabase:
    """Connect to MongoDB and create indexes."""
    global _client, _db
    _client = AsyncIOMotorClient(uri)
    _db = _client[database_name]

    await _db.alerts.create_index("timestamp")
    await _db.alerts.create_index("status")
    await _db.alerts.create_index("student_display_id")
    await _db.students.create_index("roll_number", unique=True, sparse=True)
    await _db.students.create_index("student_id", unique=True)
    await _db.events.create_index("timestamp")

    logger.info(f"MongoDB connected: {database_name}")
    return _db


async def close_db():
    """Close MongoDB connection."""
    global _client
    if _client:
        _client.close()
        logger.info("MongoDB connection closed.")


def get_db() -> AsyncIOMotorDatabase:
    """Get the current database instance."""
    if _db is None:
        raise RuntimeError("Database not connected. Call connect_db() first.")
    return _db
