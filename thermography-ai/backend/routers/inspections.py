"""Inspections API Routes"""

from fastapi import APIRouter, Query
from database import get_db
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/")
async def get_inspections(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    severity: str = Query(None),
    equipment_id: str = Query(None),
    status: str = Query(None),
):
    db = get_db()
    try:
        query = {}
        if severity:
            query["severity"] = severity
        if equipment_id:
            query["equipment_id"] = equipment_id
        if status:
            query["status"] = status

        skip = (page - 1) * limit
        total = await db.inspections.count_documents(query)
        docs = await db.inspections.find(query).sort("timestamp", -1).skip(skip).limit(limit).to_list(limit)

        inspections = []
        for d in docs:
            d.pop("_id", None)
            if isinstance(d.get("timestamp"), datetime):
                d["timestamp"] = d["timestamp"].isoformat()
            inspections.append(d)

        return {
            "inspections": inspections,
            "total": total,
            "page": page,
            "pages": (total + limit - 1) // limit
        }
    except Exception as e:
        logger.error(f"Get inspections error: {e}")
        return {"inspections": [], "total": 0, "page": 1, "pages": 0}


@router.get("/critical")
async def get_critical_inspections():
    db = get_db()
    try:
        docs = await db.inspections.find(
            {"severity": {"$in": ["Critical", "Serious"]}}
        ).sort("timestamp", -1).limit(20).to_list(20)

        result = []
        for d in docs:
            d.pop("_id", None)
            if isinstance(d.get("timestamp"), datetime):
                d["timestamp"] = d["timestamp"].isoformat()
            result.append(d)
        return {"inspections": result, "count": len(result)}
    except Exception as e:
        logger.error(f"Critical inspections error: {e}")
        return {"inspections": [], "count": 0}


@router.get("/history")
async def get_inspection_history(days: int = Query(30, ge=1, le=365)):
    from datetime import timedelta
    db = get_db()
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        docs = await db.inspections.find(
            {"timestamp": {"$gte": cutoff}}
        ).sort("timestamp", -1).to_list(500)

        result = []
        for d in docs:
            d.pop("_id", None)
            if isinstance(d.get("timestamp"), datetime):
                d["timestamp"] = d["timestamp"].isoformat()
            result.append(d)

        # Aggregate by severity
        severity_counts = {}
        for d in result:
            sev = d.get("severity", "Unknown")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        return {
            "inspections": result,
            "total": len(result),
            "period_days": days,
            "severity_breakdown": severity_counts
        }
    except Exception as e:
        logger.error(f"History error: {e}")
        return {"inspections": [], "total": 0, "period_days": days, "severity_breakdown": {}}


@router.get("/{inspection_id}")
async def get_inspection(inspection_id: str):
    db = get_db()
    try:
        doc = await db.inspections.find_one({"inspection_id": inspection_id})
        if not doc:
            return {"error": "Inspection not found"}
        doc.pop("_id", None)
        if isinstance(doc.get("timestamp"), datetime):
            doc["timestamp"] = doc["timestamp"].isoformat()
        return doc
    except Exception as e:
        logger.error(f"Get inspection error: {e}")
        return {"error": str(e)}
