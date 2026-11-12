import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.security import SecurityMiddleware
from backend.app.database.session import init_db
from backend.app.api.incidents import sync_incidents_from_db
from backend.app.api.health import router as health_router
from backend.app.api.services import router as services_router
from backend.app.api.metrics import router as metrics_router
from backend.app.api.incidents import router as incidents_router
from backend.app.api.faults import router as faults_router
from backend.app.api.models import router as models_router
from backend.app.api.evaluations import router as evaluations_router
from backend.app.api.settings import router as settings_router

from simulator.services.mesh import service_mesh
from ml.anomaly_detection.isolation_forest import anomaly_detector
from ml.classification.classifier import incident_classifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("wingman.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Wingman AI Production Platform...")

    # Initialize Database schemas & synchronize incidents
    try:
        await init_db()
        logger.info("Database schemas verified.")
        await sync_incidents_from_db()
        logger.info("Incidents database synchronization completed.")
    except Exception as e:
        logger.warning(f"Database init notice: {e}")

    # Load ML Model Artifacts
    anomaly_path = "ml/artifacts/isolation_forest.joblib"
    classifier_path = "ml/artifacts/lightgbm_model.joblib"

    if os.path.exists(anomaly_path):
        anomaly_detector.load(anomaly_path)
        logger.info(f"Loaded Isolation Forest model (v{anomaly_detector.version}, threshold={anomaly_detector.threshold})")

    if os.path.exists(classifier_path):
        incident_classifier.load(classifier_path)
        logger.info(f"Loaded LightGBM incident classifier (v{incident_classifier.version})")

    # Start Distributed Microservice Simulator & Telemetry Pipeline
    logger.info("Starting distributed microservice simulator mesh & background traffic generator...")
    await service_mesh.start()

    yield

    logger.info("Stopping Wingman AI Platform...")
    await service_mesh.stop()


app = FastAPI(
    title="Wingman AI — Production Incident Investigator",
    description="Autonomous AIOps, ML-Powered Incident Detection & Root Cause Investigation Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enterprise Security Headers & Rate Limiting Middleware
app.add_middleware(SecurityMiddleware)

# Mount Routers
app.include_router(health_router, prefix="/api")
app.include_router(services_router, prefix="/api")
app.include_router(metrics_router, prefix="/api")
app.include_router(incidents_router, prefix="/api")
app.include_router(faults_router, prefix="/api")
app.include_router(models_router, prefix="/api")
app.include_router(evaluations_router, prefix="/api")
app.include_router(settings_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "product": "Wingman AI",
        "tagline": "Your AI-powered production incident investigator.",
        "status": "online",
        "docs_url": "/docs",
        "api_prefix": "/api",
    }
