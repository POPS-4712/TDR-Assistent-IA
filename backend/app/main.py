"""
Main FastAPI application for Automation Center Backend.
"""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .core.logging import logger
from .api.routes import system, automations, credentials, profiles, backup
from .database.migrations import run_migrations

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Automation Center Backend API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(system.router, prefix="/api/v1/system", tags=["system"])
app.include_router(automations.router, prefix="/api/v1/automations", tags=["automations"])
app.include_router(credentials.router, prefix="/api/v1/credentials", tags=["credentials"])
app.include_router(profiles.router, prefix="/api/v1/profiles", tags=["profiles"])
app.include_router(backup.router, prefix="/api/v1/backup", tags=["backup"])

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle events."""
    logger.info("Starting Automation Center")
    try:
        if settings.ENABLE_DATABASE_MIGRATIONS:
            logger.info("Running database migrations...")
            from .database.db import get_session
            async with get_session() as session:
                await run_migrations(session)
            logger.info("Database migrations completed")
        yield
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    finally:
        logger.info("Shutting down Automation Center")

# Set lifespan
app.router.lifespan_context = lifespan

# Health check
@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "app": settings.APP_NAME}

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )