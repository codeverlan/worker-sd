#!/usr/bin/env python3
"""
Simplified Git Sync Service for initial testing
"""

import os
import asyncio
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(
    title="Git Sync Service",
    description="Bidirectional GitHub ↔ Gitea Synchronization",
    version="1.0.0"
)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "git-sync-service",
        "version": "1.0.0"
    }

@app.get("/status")
async def get_status():
    """Get sync service status."""
    return {
        "status": "running",
        "total_repositories": 0,
        "active_syncs": 0,
        "failed_syncs": 0
    }

@app.get("/repositories")
async def list_repositories():
    """List all tracked repositories."""
    return []

@app.post("/sync/manual")
async def manual_sync(background_tasks: BackgroundTasks, repo_name: str = None):
    """Trigger manual sync for all repositories or specific repository."""
    return {
        "message": f"Manual sync would be triggered for {'all repositories' if not repo_name else repo_name}",
        "status": "queued"
    }

@app.post("/webhooks/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle GitHub webhooks."""
    try:
        payload = await request.json()
        headers = dict(request.headers)
        
        # Log webhook received
        repo_name = payload.get("repository", {}).get("name", "unknown")
        event_type = headers.get("x-github-event", "unknown")
        
        print(f"GitHub webhook received: {event_type} for {repo_name}")
        
        return JSONResponse(content={"status": "processed", "event": event_type, "repo": repo_name})
        
    except Exception as e:
        print(f"Failed to process GitHub webhook: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/webhooks/gitea")
async def gitea_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Gitea webhooks."""
    try:
        payload = await request.json()
        headers = dict(request.headers)
        
        # Log webhook received
        repo_name = payload.get("repository", {}).get("name", "unknown")
        event_type = headers.get("x-gitea-event", "unknown")
        
        print(f"Gitea webhook received: {event_type} for {repo_name}")
        
        return JSONResponse(content={"status": "processed", "event": event_type, "repo": repo_name})
        
    except Exception as e:
        print(f"Failed to process Gitea webhook: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/logs")
async def get_logs(limit: int = 100):
    """Get recent sync logs."""
    return []

if __name__ == "__main__":
    uvicorn.run(
        "simple-main:app",
        host="0.0.0.0",
        port=8080,
        log_level="info",
        reload=False
    )