"""MongoDB repository classes for CRUD operations."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from backend.app.database.mongodb import get_db

logger = logging.getLogger(__name__)


class AlertRepository:
    """CRUD operations for alerts collection."""

    @staticmethod
    async def insert(alert_data: dict) -> str:
        db = get_db()
        result = await db.alerts.insert_one(alert_data)
        return str(result.inserted_id)

    @staticmethod
    async def find_all(
        status: Optional[str] = None,
        limit: int = 100,
        skip: int = 0,
    ) -> List[dict]:
        db = get_db()
        query = {}
        if status:
            query["status"] = status
        cursor = db.alerts.find(query).sort("timestamp", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    @staticmethod
    async def find_by_id(alert_id: str) -> Optional[dict]:
        db = get_db()
        return await db.alerts.find_one({"alert_id": alert_id})

    @staticmethod
    async def update_status(alert_id: str, status: str) -> bool:
        db = get_db()
        result = await db.alerts.update_one(
            {"alert_id": alert_id}, {"$set": {"status": status}}
        )
        return result.modified_count > 0

    @staticmethod
    async def count(status: Optional[str] = None) -> int:
        db = get_db()
        query = {"status": status} if status else {}
        return await db.alerts.count_documents(query)

    @staticmethod
    async def today_count() -> int:
        db = get_db()
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return await db.alerts.count_documents(
            {"timestamp": {"$gte": today.timestamp()}}
        )


class EventRepository:
    """CRUD operations for events collection."""

    @staticmethod
    async def insert(event_data: dict) -> str:
        db = get_db()
        result = await db.events.insert_one(event_data)
        return str(result.inserted_id)

    @staticmethod
    async def find_all(limit: int = 100, skip: int = 0) -> List[dict]:
        db = get_db()
        cursor = db.events.find().sort("timestamp", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)


class StudentRepository:
    """CRUD operations for enrolled students collection."""

    @staticmethod
    async def insert(student_data: dict) -> str:
        db = get_db()
        result = await db.students.insert_one(student_data)
        return str(result.inserted_id)

    @staticmethod
    async def find_all() -> List[dict]:
        db = get_db()
        cursor = db.students.find({}, {"face_embedding": 0, "sface_embedding": 0}).sort("enrolled_at", -1)
        return await cursor.to_list(length=500)

    @staticmethod
    async def find_by_id(student_id: str) -> Optional[dict]:
        db = get_db()
        return await db.students.find_one({"student_id": student_id}, {"face_embedding": 0, "sface_embedding": 0})

    @staticmethod
    async def find_by_roll_number(roll_number: str) -> Optional[dict]:
        db = get_db()
        return await db.students.find_one({"roll_number": roll_number}, {"face_embedding": 0, "sface_embedding": 0})

    @staticmethod
    async def update(student_id: str, data: dict) -> bool:
        db = get_db()
        result = await db.students.update_one(
            {"student_id": student_id}, {"$set": data}
        )
        return result.modified_count > 0

    @staticmethod
    async def delete(student_id: str) -> bool:
        db = get_db()
        result = await db.students.delete_one({"student_id": student_id})
        return result.deleted_count > 0

    @staticmethod
    async def count() -> int:
        db = get_db()
        return await db.students.count_documents({})
