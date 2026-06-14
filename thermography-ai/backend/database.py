"""
MongoDB Atlas Database Connection & Seed Data
"""

import os
import logging
from datetime import datetime, timedelta
import random
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "thermography_ai")

client: AsyncIOMotorClient = None
db = None


async def connect_db():
    global client, db
    try:
        client = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
        await client.admin.command("ping")
        db = client[DB_NAME]
        logger.info(f"Connected to MongoDB: {DB_NAME}")
    except Exception as e:
        logger.warning(f"MongoDB connection failed ({e}). Using in-memory fallback.")
        # Use in-memory mock if MongoDB unavailable
        db = MockDB()


async def disconnect_db():
    global client
    if client:
        client.close()


def get_db():
    return db


EQUIPMENT_LIST = [
    {"id": "EQ-001", "name": "Main Distribution Panel A", "type": "Electrical Panel", "location": "Building A - Room 101", "criticality": "Critical", "last_inspection": "2025-05-15", "next_inspection": "2025-08-15"},
    {"id": "EQ-002", "name": "Transformer TR-2400", "type": "Power Transformer", "location": "Substation 1", "criticality": "Critical", "last_inspection": "2025-04-20", "next_inspection": "2025-07-20"},
    {"id": "EQ-003", "name": "Motor Drive MCC-7", "type": "Motor Control Center", "location": "Production Floor B", "criticality": "High", "last_inspection": "2025-05-01", "next_inspection": "2025-08-01"},
    {"id": "EQ-004", "name": "Switchgear SG-480V", "type": "Switchgear", "location": "Building C - Basement", "criticality": "Critical", "last_inspection": "2025-03-10", "next_inspection": "2025-06-10"},
    {"id": "EQ-005", "name": "Compressor Motor CM-150", "type": "Induction Motor", "location": "Utility Room 3", "criticality": "Medium", "last_inspection": "2025-05-20", "next_inspection": "2025-09-20"},
    {"id": "EQ-006", "name": "UPS System UPS-200K", "type": "UPS", "location": "Data Center", "criticality": "Critical", "last_inspection": "2025-04-05", "next_inspection": "2025-07-05"},
    {"id": "EQ-007", "name": "Bus Duct BD-2000A", "type": "Bus Duct", "location": "Main Plant - Level 2", "criticality": "High", "last_inspection": "2025-02-28", "next_inspection": "2025-05-28"},
    {"id": "EQ-008", "name": "HVAC Unit AHU-12", "type": "HVAC Motor", "location": "Rooftop - West Wing", "criticality": "Low", "last_inspection": "2025-05-25", "next_inspection": "2025-11-25"},
]

SEVERITIES = ["Critical", "Serious", "Moderate", "Minor", "Normal"]
SEVERITY_WEIGHTS = [0.08, 0.12, 0.20, 0.25, 0.35]

FINDINGS = {
    "Critical": ["Severe overheating detected - immediate shutdown required", "Phase imbalance >15% with hotspot 95°C above ambient", "Loose connection causing arcing risk"],
    "Serious": ["Hot connection on bus bar - Delta-T 35°C", "Overloaded phase conductor identified", "Failing capacitor bank detected"],
    "Moderate": ["Elevated temperature on breaker terminal", "Unbalanced load distribution noted", "Insulation degradation indicated"],
    "Minor": ["Slight temperature asymmetry observed", "Minor dust accumulation on cooling fins", "Marginal overload on one phase"],
    "Normal": ["All temperatures within acceptable limits", "No anomalies detected", "Equipment operating normally"],
}

RECOMMENDATIONS = {
    "Critical": ["Immediate de-energization and repair", "Emergency maintenance team dispatch", "Replace faulty component before re-energization"],
    "Serious": ["Schedule repair within 72 hours", "Tighten connections and re-torque to spec", "Monitor continuously until repair"],
    "Moderate": ["Schedule maintenance within 30 days", "Investigate root cause of temperature rise", "Re-inspect after load balancing"],
    "Minor": ["Document and monitor at next scheduled inspection", "Clean equipment during next PM window", "No immediate action required"],
    "Normal": ["Continue normal monitoring schedule", "Maintain current maintenance intervals", "No action required"],
}


async def seed_demo_data():
    global db
    if isinstance(db, MockDB):
        return

    try:
        # Check if already seeded
        count = await db.inspections.count_documents({})
        if count > 10:
            logger.info("Demo data already present.")
            return

        # Seed equipment
        for eq in EQUIPMENT_LIST:
            await db.equipment.update_one({"id": eq["id"]}, {"$set": eq}, upsert=True)

        # Seed inspections (90 days of history)
        inspections = []
        for days_ago in range(90, 0, -1):
            num_inspections = random.randint(1, 4)
            for _ in range(num_inspections):
                eq = random.choice(EQUIPMENT_LIST)
                severity = random.choices(SEVERITIES, weights=SEVERITY_WEIGHTS)[0]
                ambient = round(random.uniform(22, 32), 1)
                hotspot = ambient + {
                    "Critical": random.uniform(60, 95),
                    "Serious": random.uniform(30, 60),
                    "Moderate": random.uniform(15, 30),
                    "Minor": random.uniform(5, 15),
                    "Normal": random.uniform(0, 5),
                }[severity]
                delta_t = round(hotspot - ambient, 1)
                ts = datetime.utcnow() - timedelta(days=days_ago, hours=random.randint(0, 23))

                inspections.append({
                    "inspection_id": f"INS-{ts.strftime('%Y%m%d')}-{random.randint(1000, 9999)}",
                    "equipment_id": eq["id"],
                    "equipment_name": eq["name"],
                    "equipment_type": eq["type"],
                    "location": eq["location"],
                    "inspector": random.choice(["J. Martinez", "R. Patel", "S. Chen", "A. Williams"]),
                    "timestamp": ts,
                    "ambient_temp": ambient,
                    "hotspot_temp": round(hotspot, 1),
                    "delta_t": delta_t,
                    "severity": severity,
                    "finding": random.choice(FINDINGS[severity]),
                    "recommendation": random.choice(RECOMMENDATIONS[severity]),
                    "compliance_score": {
                        "Critical": random.randint(10, 35),
                        "Serious": random.randint(36, 55),
                        "Moderate": random.randint(56, 70),
                        "Minor": random.randint(71, 85),
                        "Normal": random.randint(86, 100),
                    }[severity],
                    "standard": random.choice(["NFPA 70B", "IEC 60076", "ISO 18434-1", "NETA MTS"]),
                    "image_path": None,
                    "hotspot_coords": [random.randint(50, 200), random.randint(50, 200), random.randint(20, 60), random.randint(20, 60)],
                    "status": "Closed" if days_ago > 7 else random.choice(["Open", "In Progress", "Closed"]),
                })

        if inspections:
            await db.inspections.insert_many(inspections)

        logger.info(f"Seeded {len(inspections)} demo inspections")

    except Exception as e:
        logger.error(f"Seed error: {e}")


class MockDB:
    """In-memory fallback when MongoDB is unavailable"""
    def __init__(self):
        self._collections = {}

    def __getattr__(self, name):
        if name not in self._collections:
            self._collections[name] = MockCollection(name)
        return self._collections[name]


class MockCollection:
    def __init__(self, name):
        self.name = name
        self._data = []

    async def count_documents(self, query):
        return len(self._data)

    async def find_one(self, query):
        return None

    async def insert_many(self, docs):
        self._data.extend(docs)

    async def update_one(self, query, update, upsert=False):
        pass

    def find(self, query=None, **kwargs):
        return MockCursor(self._data)

    async def aggregate(self, pipeline):
        return []

    async def distinct(self, field, query=None):
        return []


class MockCursor:
    def __init__(self, data):
        self._data = data
        self._idx = 0

    def sort(self, *args, **kwargs):
        return self

    def skip(self, n):
        return self

    def limit(self, n):
        self._data = self._data[:n]
        return self

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._idx >= len(self._data):
            raise StopAsyncIteration
        item = self._data[self._idx]
        self._idx += 1
        return item

    async def to_list(self, length=None):
        return self._data[:length] if length else self._data
