"""
Image Upload & Thermal Analysis Routes
OpenCV-based hotspot detection and Delta-T analysis
"""

from fastapi import APIRouter, UploadFile, File, Form
from database import get_db, FINDINGS, RECOMMENDATIONS
import logging
import os
import random
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def analyze_thermal_image_cv(image_path: str) -> dict:
    """
    OpenCV-based thermal image analysis.
    Simulates hotspot detection if OpenCV/thermal data unavailable.
    """
    try:
        import cv2
        import numpy as np

        img = cv2.imread(image_path)
        if img is None:
            raise ValueError("Cannot read image")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Normalize to temperature range (typical IR camera: 0-150°C mapped to 0-255)
        ambient_base = 25.0
        scale_factor = 150.0 / 255.0
        temp_map = gray.astype(float) * scale_factor + ambient_base

        # Find hotspot
        max_val = float(np.max(temp_map))
        min_val = float(np.min(temp_map))
        mean_val = float(np.mean(temp_map))

        # Hotspot location
        max_loc = np.unravel_index(np.argmax(temp_map), temp_map.shape)
        hotspot_y, hotspot_x = int(max_loc[0]), int(max_loc[1])

        # Threshold for anomaly detection
        threshold = mean_val + 2 * float(np.std(temp_map))
        anomaly_mask = temp_map > threshold
        anomaly_pixels = int(np.sum(anomaly_mask))

        # Delta-T calculation
        ambient_temp = round(min_val + (mean_val - min_val) * 0.3, 1)
        hotspot_temp = round(max_val, 1)
        delta_t = round(hotspot_temp - ambient_temp, 1)

        # Severity classification per NFPA 70B / ISO 18434
        if delta_t >= 40:
            severity = "Critical"
        elif delta_t >= 25:
            severity = "Serious"
        elif delta_t >= 10:
            severity = "Moderate"
        elif delta_t >= 3:
            severity = "Minor"
        else:
            severity = "Normal"

        compliance_score = max(10, min(100, 100 - int(delta_t * 1.5)))

        return {
            "method": "opencv",
            "ambient_temp": ambient_temp,
            "hotspot_temp": hotspot_temp,
            "delta_t": delta_t,
            "severity": severity,
            "compliance_score": compliance_score,
            "anomaly_pixels": anomaly_pixels,
            "hotspot_coords": [hotspot_x, hotspot_y, 30, 30],
            "temp_min": round(min_val, 1),
            "temp_max": round(max_val, 1),
            "temp_mean": round(mean_val, 1),
        }
    except ImportError:
        logger.warning("OpenCV not available, using simulation")
        return _simulate_analysis()
    except Exception as e:
        logger.warning(f"CV analysis failed: {e}, using simulation")
        return _simulate_analysis()


def _simulate_analysis() -> dict:
    """Simulate thermal analysis when CV unavailable"""
    import random
    severities = ["Critical", "Serious", "Moderate", "Minor", "Normal"]
    weights = [0.08, 0.12, 0.20, 0.25, 0.35]
    severity = random.choices(severities, weights=weights)[0]

    ambient = round(random.uniform(22, 32), 1)
    delta_t_ranges = {
        "Critical": (40, 80), "Serious": (25, 40), "Moderate": (10, 25),
        "Minor": (3, 10), "Normal": (0, 3)
    }
    delta_t = round(random.uniform(*delta_t_ranges[severity]), 1)
    hotspot = round(ambient + delta_t, 1)
    compliance = max(10, min(100, 100 - int(delta_t * 1.5)))

    return {
        "method": "simulation",
        "ambient_temp": ambient,
        "hotspot_temp": hotspot,
        "delta_t": delta_t,
        "severity": severity,
        "compliance_score": compliance,
        "anomaly_pixels": random.randint(0, 5000),
        "hotspot_coords": [random.randint(50, 200), random.randint(50, 200), 30, 30],
        "temp_min": round(ambient - 2, 1),
        "temp_max": hotspot,
        "temp_mean": round(ambient + delta_t * 0.3, 1),
    }


@router.post("/thermal-image")
async def upload_thermal_image(
    file: UploadFile = File(...),
    equipment_id: str = Form("EQ-001"),
    inspector: str = Form("Field Inspector"),
    standard: str = Form("NFPA 70B"),
):
    db = get_db()
    try:
        # Save file
        filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        content = await file.read()
        with open(filepath, "wb") as f:
            f.write(content)

        # Analyze
        analysis = analyze_thermal_image_cv(filepath)
        severity = analysis["severity"]

        # Build inspection record
        inspection_id = f"INS-{datetime.utcnow().strftime('%Y%m%d')}-{random.randint(1000,9999)}"
        record = {
            "inspection_id": inspection_id,
            "equipment_id": equipment_id,
            "equipment_name": equipment_id,
            "inspector": inspector,
            "standard": standard,
            "timestamp": datetime.utcnow(),
            "image_path": filepath,
            "finding": random.choice(FINDINGS[severity]),
            "recommendation": random.choice(RECOMMENDATIONS[severity]),
            "status": "Open" if severity in ["Critical", "Serious"] else "Closed",
            **analysis,
        }

        await db.inspections.update_one(
            {"inspection_id": inspection_id},
            {"$set": record},
            upsert=True
        )

        record.pop("_id", None)
        if isinstance(record.get("timestamp"), datetime):
            record["timestamp"] = record["timestamp"].isoformat()

        return {
            "success": True,
            "inspection_id": inspection_id,
            "analysis": analysis,
            "record": record
        }
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return {"success": False, "error": str(e)}
