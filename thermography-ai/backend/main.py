"""
Thermography Compliance AI - FastAPI Backend
Enterprise-grade industrial thermography monitoring platform
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn
import logging
from contextlib import asynccontextmanager

from database import connect_db, disconnect_db, seed_demo_data
from routers import dashboard, inspections, equipment, reports, ai_assistant, uploads

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Thermography Compliance AI...")
    await connect_db()
    await seed_demo_data()
    yield
    await disconnect_db()
    logger.info("Shutting down...")


app = FastAPI(
    title="Thermography Compliance AI",
    description="Enterprise Industrial Thermography Monitoring Platform",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="../frontend/static"), name="static")
templates = Jinja2Templates(directory="../frontend/templates")

# Include routers
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(inspections.router, prefix="/api/inspections", tags=["Inspections"])
app.include_router(equipment.router, prefix="/api/equipment", tags=["Equipment"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(ai_assistant.router, prefix="/api/ai", tags=["AI Assistant"])
app.include_router(uploads.router, prefix="/api/uploads", tags=["Uploads"])


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health():
    return {"status": "operational", "platform": "Thermography Compliance AI v2.0"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
