#!/usr/bin/env python3
"""Simple test version of the sync service."""

import os
import uvicorn
from fastapi import FastAPI

app = FastAPI(title="Git Sync Service Test")

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "git-sync-test"}

@app.get("/")
async def root():
    return {"message": "Git Sync Service is running"}

if __name__ == "__main__":
    uvicorn.run(
        "test-service:app",
        host="0.0.0.0",
        port=8080,
        reload=False
    )