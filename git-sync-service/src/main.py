#!/usr/bin/env python3
"""
Git Sync Service - Bidirectional GitHub ↔ Gitea Synchronization
Provides real-time bidirectional sync between GitHub and Gitea repositories.
"""

import asyncio
import logging
import os
import signal
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse

from config.settings import Settings
from services.sync_engine import SyncEngine
from services.webhook_handler import WebhookHandler
from services.scheduler import SyncScheduler
from database.models import init_db
# from utils.logger import setup_logging


# Global instances
sync_engine: SyncEngine = None
webhook_handler: WebhookHandler = None
scheduler: SyncScheduler = None
settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    global sync_engine, webhook_handler, scheduler
    
    # Startup
    logger = structlog.get_logger()
    logger.info("Starting Git Sync Service", version="1.0.0")
    
    try:
        # Initialize database
        await init_db()
        
        # Initialize services
        sync_engine = SyncEngine(settings)
        webhook_handler = WebhookHandler(settings, sync_engine)
        scheduler = SyncScheduler(settings, sync_engine)
        
        # Start background scheduler
        asyncio.create_task(scheduler.start())
        
        logger.info("Git Sync Service started successfully")
        
        yield
        
    except Exception as e:
        logger.error("Failed to start Git Sync Service", error=str(e))
        raise
    
    # Shutdown
    logger.info("Shutting down Git Sync Service")
    if scheduler:
        await scheduler.stop()


# Create FastAPI app
app = FastAPI(
    title="Git Sync Service",
    description="Bidirectional GitHub ↔ Gitea Synchronization",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "git-sync-service",
        "version": "1.0.0",
        "sync_engine": sync_engine.is_healthy() if sync_engine else False
    }


@app.get("/status")
async def get_status():
    """Get sync service status."""
    if not sync_engine:
        raise HTTPException(status_code=503, detail="Sync engine not initialized")
    
    return await sync_engine.get_status()


@app.get("/repositories")
async def list_repositories():
    """List all tracked repositories."""
    if not sync_engine:
        raise HTTPException(status_code=503, detail="Sync engine not initialized")
    
    return await sync_engine.list_repositories()


@app.post("/sync/manual")
async def manual_sync(background_tasks: BackgroundTasks, repo_name: str = None):
    """Trigger manual sync for all repositories or specific repository."""
    if not sync_engine:
        raise HTTPException(status_code=503, detail="Sync engine not initialized")
    
    background_tasks.add_task(sync_engine.sync_repositories, repo_name)
    
    return {
        "message": f"Manual sync triggered for {'all repositories' if not repo_name else repo_name}",
        "status": "queued"
    }


@app.post("/webhooks/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle GitHub webhooks."""
    if not webhook_handler:
        raise HTTPException(status_code=503, detail="Webhook handler not initialized")
    
    try:
        payload = await request.json()
        headers = dict(request.headers)
        
        result = await webhook_handler.handle_github_webhook(payload, headers)
        
        if result.get("sync_required"):
            background_tasks.add_task(
                sync_engine.sync_repository,
                result["repository"],
                "github"
            )
        
        return JSONResponse(content={"status": "processed"})
        
    except Exception as e:
        logger = structlog.get_logger()
        logger.error("Failed to process GitHub webhook", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/webhooks/gitea")
async def gitea_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Gitea webhooks."""
    if not webhook_handler:
        raise HTTPException(status_code=503, detail="Webhook handler not initialized")
    
    try:
        payload = await request.json()
        headers = dict(request.headers)
        
        result = await webhook_handler.handle_gitea_webhook(payload, headers)
        
        if result.get("sync_required"):
            background_tasks.add_task(
                sync_engine.sync_repository,
                result["repository"],
                "gitea"
            )
        
        return JSONResponse(content={"status": "processed"})
        
    except Exception as e:
        logger = structlog.get_logger()
        logger.error("Failed to process Gitea webhook", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/logs")
async def get_logs(limit: int = 100):
    """Get recent sync logs."""
    if not sync_engine:
        raise HTTPException(status_code=503, detail="Sync engine not initialized")
    
    return await sync_engine.get_recent_logs(limit)


@app.post("/repositories/{repo_name}/conflict/resolve")
async def resolve_conflict(repo_name: str, resolution: Dict[str, Any]):
    """Manually resolve a repository conflict."""
    if not sync_engine:
        raise HTTPException(status_code=503, detail="Sync engine not initialized")
    
    return await sync_engine.resolve_conflict(repo_name, resolution)


def handle_signal(signum, frame):
    """Handle shutdown signals."""
    logger = structlog.get_logger()
    logger.info("Received shutdown signal", signal=signum)
    sys.exit(0)


if __name__ == "__main__":
    # Setup signal handlers
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        log_level="info",
        reload=False
    )