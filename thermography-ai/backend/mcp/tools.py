"""
MCP (Model Context Protocol) Tools for Thermography AI
Provides live MongoDB data to the LLM via structured tool calls
"""

import json
import logging
from datetime import datetime, timedelta
from database import get_db, EQUIPMENT_LIST

logger = logging.getLogger(__name__)

MCP_TOOLS = [
    {
        "name": "get_dashboard_stats",
        "description": "Retrieves live dashboard statistics including total inspections, critical alerts, compliance scores, severity distribution, and equipment count from MongoDB.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_inspection_history",
        "description": "Retrieves recent inspection records from MongoDB. Use when user asks about recent inspections, findings, or inspection trends.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days to look back (default 30)", "default": 30},
                "severity": {"type": "string", "description": "Filter by severity: Critical, Serious, Moderate, Minor, Normal"},
                "limit": {"type": "integer", "description": "Maximum records to return (default 10)", "default": 10}
            },
            "required": []
        }
    },
    {
        "name": "get_critical_alerts",
        "description": "Retrieves current critical and serious alerts that need immediate attention.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_equipment_details",
        "description": "Retrieves details about monitored equipment including health scores and recent inspection history.",
        "input_schema": {
            "type": "object",
            "properties": {
                "equipment_id": {"type": "string", "description": "Equipment ID (e.g., EQ-001). If not provided, returns all equipment."}
            },
            "required": []
        }
    },
    {
        "name": "analyze_temperatures",
        "description": "Analyzes temperature data and provides Delta-T severity classification per NFPA 70B/ISO 18434 standards.",
        "input_schema": {
            "type": "object",
            "properties": {
                "hotspot_temp": {"type": "number", "description": "Hotspot temperature in °C"},
                "ambient_temp": {"type": "number", "description": "Ambient temperature in °C"},
                "equipment_type": {"type": "string", "description": "Type of equipment being analyzed"}
            },
            "required": ["hotspot_temp", "ambient_temp"]
        }
    },
    {
        "name": "get_compliance_status",
        "description": "Retrieves overall compliance status, scores by equipment, and regulatory compliance information.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]


async def execute_tool(tool_name: str, tool_input: dict) -> dict:
    """Execute an MCP tool and return structured results"""
    db = get_db()
    try:
        if tool_name == "get_dashboard_stats":
            return await _get_dashboard_stats(db)
        elif tool_name == "get_inspection_history":
            return await _get_inspection_history(db, **tool_input)
        elif tool_name == "get_critical_alerts":
            return await _get_critical_alerts(db)
        elif tool_name == "get_equipment_details":
            return await _get_equipment_details(db, **tool_input)
        elif tool_name == "analyze_temperatures":
            return _analyze_temperatures(**tool_input)
        elif tool_name == "get_compliance_status":
            return await _get_compliance_status(db)
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    except Exception as e:
        logger.error(f"Tool execution error ({tool_name}): {e}")
        return {"error": str(e), "tool": tool_name}


async def _get_dashboard_stats(db) -> dict:
    total = await db.inspections.count_documents({})
    critical = await db.inspections.count_documents({"severity": "Critical"})
    serious = await db.inspections.count_documents({"severity": "Serious"})
    moderate = await db.inspections.count_documents({"severity": "Moderate"})
    minor = await db.inspections.count_documents({"severity": "Minor"})
    normal = await db.inspections.count_documents({"severity": "Normal"})
    open_alerts = await db.inspections.count_documents({"severity": {"$in": ["Critical", "Serious"]}, "status": {"$ne": "Closed"}})

    docs = await db.inspections.find({}, {"compliance_score": 1}).to_list(1000)
    scores = [d.get("compliance_score", 0) for d in docs if d.get("compliance_score")]
    avg_compliance = round(sum(scores) / len(scores), 1) if scores else 0

    week_ago = datetime.utcnow() - timedelta(days=7)
    recent = await db.inspections.count_documents({"timestamp": {"$gte": week_ago}})

    return {
        "total_inspections": total,
        "critical_alerts": critical,
        "serious_alerts": serious,
        "moderate_alerts": moderate,
        "minor_alerts": minor,
        "normal_count": normal,
        "open_alerts": open_alerts,
        "recent_7_days": recent,
        "avg_compliance_score": avg_compliance,
        "equipment_monitored": 8,
        "summary": f"Platform has {total} total inspections with {critical} critical and {serious} serious alerts. Average compliance score is {avg_compliance}%. There are {open_alerts} open alerts requiring attention."
    }


async def _get_inspection_history(db, days: int = 30, severity: str = None, limit: int = 10) -> dict:
    cutoff = datetime.utcnow() - timedelta(days=days)
    query = {"timestamp": {"$gte": cutoff}}
    if severity:
        query["severity"] = severity

    docs = await db.inspections.find(query).sort("timestamp", -1).limit(limit).to_list(limit)
    inspections = []
    for d in docs:
        d.pop("_id", None)
        if isinstance(d.get("timestamp"), datetime):
            d["timestamp"] = d["timestamp"].isoformat()
        inspections.append({
            "id": d.get("inspection_id"),
            "equipment": d.get("equipment_name"),
            "severity": d.get("severity"),
            "delta_t": d.get("delta_t"),
            "hotspot": d.get("hotspot_temp"),
            "finding": d.get("finding"),
            "recommendation": d.get("recommendation"),
            "date": d.get("timestamp"),
            "status": d.get("status"),
            "compliance_score": d.get("compliance_score"),
        })

    total = await db.inspections.count_documents(query)
    return {
        "inspections": inspections,
        "total_in_period": total,
        "period_days": days,
        "severity_filter": severity or "all",
        "summary": f"Found {total} inspections in the last {days} days. Showing {len(inspections)} most recent."
    }


async def _get_critical_alerts(db) -> dict:
    docs = await db.inspections.find(
        {"severity": {"$in": ["Critical", "Serious"]}, "status": {"$ne": "Closed"}}
    ).sort("timestamp", -1).limit(10).to_list(10)

    alerts = []
    for d in docs:
        d.pop("_id", None)
        if isinstance(d.get("timestamp"), datetime):
            d["timestamp"] = d["timestamp"].isoformat()
        alerts.append({
            "id": d.get("inspection_id"),
            "equipment": d.get("equipment_name"),
            "location": d.get("location"),
            "severity": d.get("severity"),
            "delta_t": d.get("delta_t"),
            "hotspot_temp": d.get("hotspot_temp"),
            "finding": d.get("finding"),
            "recommendation": d.get("recommendation"),
            "date": d.get("timestamp"),
            "status": d.get("status"),
        })

    return {
        "alerts": alerts,
        "total_open": len(alerts),
        "summary": f"There are {len(alerts)} open critical/serious alerts requiring immediate attention." if alerts else "No open critical alerts at this time."
    }


async def _get_equipment_details(db, equipment_id: str = None) -> dict:
    if equipment_id:
        doc = await db.equipment.find_one({"id": equipment_id})
        if not doc:
            doc = next((e for e in EQUIPMENT_LIST if e["id"] == equipment_id), None)
        if not doc:
            return {"error": f"Equipment {equipment_id} not found"}
        doc = dict(doc)
        doc.pop("_id", None)
        total = await db.inspections.count_documents({"equipment_id": equipment_id})
        critical = await db.inspections.count_documents({"equipment_id": equipment_id, "severity": "Critical"})
        doc["total_inspections"] = total
        doc["critical_count"] = critical
        return {"equipment": doc, "summary": f"Equipment {doc.get('name')} has had {total} inspections with {critical} critical findings."}
    else:
        docs = await db.equipment.find({}).to_list(100)
        equipment = []
        for d in docs:
            d.pop("_id", None)
            eq_id = d.get("id")
            total = await db.inspections.count_documents({"equipment_id": eq_id})
            critical = await db.inspections.count_documents({"equipment_id": eq_id, "severity": "Critical"})
            d["total_inspections"] = total
            d["critical_count"] = critical
            equipment.append(d)
        if not equipment:
            equipment = EQUIPMENT_LIST
        return {
            "equipment": equipment,
            "total": len(equipment),
            "summary": f"Monitoring {len(equipment)} pieces of equipment across the facility."
        }


def _analyze_temperatures(hotspot_temp: float, ambient_temp: float, equipment_type: str = "Electrical") -> dict:
    delta_t = hotspot_temp - ambient_temp

    if delta_t >= 40:
        severity = "Critical"
        action = "IMMEDIATE shutdown and repair required. Do not re-energize until repaired."
        nfpa_class = "Priority 1"
        timeframe = "Immediately"
    elif delta_t >= 25:
        severity = "Serious"
        action = "Schedule repair within 72 hours. Increase monitoring frequency."
        nfpa_class = "Priority 2"
        timeframe = "Within 72 hours"
    elif delta_t >= 10:
        severity = "Moderate"
        action = "Schedule repair within 30 days. Monitor until repaired."
        nfpa_class = "Priority 3"
        timeframe = "Within 30 days"
    elif delta_t >= 3:
        severity = "Minor"
        action = "Document and monitor at next scheduled inspection."
        nfpa_class = "Priority 4"
        timeframe = "Next scheduled maintenance"
    else:
        severity = "Normal"
        action = "No action required. Continue normal monitoring."
        nfpa_class = "Normal"
        timeframe = "No action needed"

    compliance_score = max(10, min(100, 100 - int(delta_t * 1.5)))

    return {
        "hotspot_temp": hotspot_temp,
        "ambient_temp": ambient_temp,
        "delta_t": round(delta_t, 1),
        "severity": severity,
        "nfpa_70b_class": nfpa_class,
        "recommended_action": action,
        "repair_timeframe": timeframe,
        "compliance_score": compliance_score,
        "standard_reference": "NFPA 70B-2023 / ISO 18434-1:2008",
        "summary": f"Delta-T of {delta_t:.1f}°C classifies as {severity} per NFPA 70B. {action}"
    }


async def _get_compliance_status(db) -> dict:
    total = await db.inspections.count_documents({})
    docs = await db.inspections.find({}, {"compliance_score": 1, "severity": 1, "equipment_id": 1}).to_list(1000)

    scores = [d.get("compliance_score", 0) for d in docs if d.get("compliance_score")]
    avg = round(sum(scores) / len(scores), 1) if scores else 0

    critical = sum(1 for d in docs if d.get("severity") == "Critical")
    serious = sum(1 for d in docs if d.get("severity") == "Serious")

    status = "Critical" if avg < 50 else "Poor" if avg < 65 else "Fair" if avg < 75 else "Good" if avg < 90 else "Excellent"

    return {
        "overall_compliance_score": avg,
        "compliance_status": status,
        "total_inspections": total,
        "critical_findings": critical,
        "serious_findings": serious,
        "standards_referenced": ["NFPA 70B-2023", "IEC 60076", "ISO 18434-1:2008", "NETA MTS"],
        "summary": f"Overall compliance score is {avg}% ({status}). {critical} critical and {serious} serious findings identified across {total} inspections."
    }
