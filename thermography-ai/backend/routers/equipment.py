"""Equipment API Routes"""

from fastapi import APIRouter
from database import get_db, EQUIPMENT_LIST
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/")
async def get_equipment():
    db = get_db()
    try:
        docs = await db.equipment.find({}).to_list(100)
        result = []
        for d in docs:
            d.pop("_id", None)
            result.append(d)
        if not result:
            result = EQUIPMENT_LIST
        return {"equipment": result, "total": len(result)}
    except Exception as e:
        logger.error(f"Get equipment error: {e}")
        return {"equipment": EQUIPMENT_LIST, "total": len(EQUIPMENT_LIST)}


@router.get("/{equipment_id}")
async def get_equipment_detail(equipment_id: str):
    db = get_db()
    try:
        doc = await db.equipment.find_one({"id": equipment_id})
        if not doc:
            doc = next((e for e in EQUIPMENT_LIST if e["id"] == equipment_id), None)
        if not doc:
            return {"error": "Equipment not found"}
        doc = dict(doc)
        doc.pop("_id", None)

        # Get recent inspections for this equipment
        inspections = await db.inspections.find(
            {"equipment_id": equipment_id}
        ).sort("timestamp", -1).limit(10).to_list(10)

        recent = []
        for ins in inspections:
            ins.pop("_id", None)
            if isinstance(ins.get("timestamp"), datetime):
                ins["timestamp"] = ins["timestamp"].isoformat()
            recent.append(ins)

        # Compute equipment health score
        if recent:
            severity_scores = {"Critical": 10, "Serious": 35, "Moderate": 60, "Minor": 80, "Normal": 95}
            avg_score = sum(severity_scores.get(r.get("severity", "Normal"), 95) for r in recent) / len(recent)
            health = round(avg_score)
        else:
            health = 95

        doc["health_score"] = health
        doc["recent_inspections"] = recent
        doc["total_inspections"] = await db.inspections.count_documents({"equipment_id": equipment_id})
        return doc
    except Exception as e:
        logger.error(f"Equipment detail error: {e}")
        return {"error": str(e)}


@router.get("/{equipment_id}/stats")
async def get_equipment_stats(equipment_id: str):
    db = get_db()
    try:
        total = await db.inspections.count_documents({"equipment_id": equipment_id})
        critical = await db.inspections.count_documents({"equipment_id": equipment_id, "severity": "Critical"})
        docs = await db.inspections.find(
            {"equipment_id": equipment_id}, {"delta_t": 1, "compliance_score": 1}
        ).to_list(100)

        delta_ts = [d.get("delta_t", 0) for d in docs if d.get("delta_t")]
        scores = [d.get("compliance_score", 0) for d in docs if d.get("compliance_score")]

        return {
            "equipment_id": equipment_id,
            "total_inspections": total,
            "critical_count": critical,
            "avg_delta_t": round(sum(delta_ts) / len(delta_ts), 1) if delta_ts else 0,
            "max_delta_t": round(max(delta_ts), 1) if delta_ts else 0,
            "avg_compliance_score": round(sum(scores) / len(scores), 1) if scores else 0,
        }
    except Exception as e:
        logger.error(f"Equipment stats error: {e}")
        return {"error": str(e)}
