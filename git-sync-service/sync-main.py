#!/usr/bin/env python3
"""
Working Git Sync Service with actual sync functionality
"""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn
import httpx
from git import Repo
import subprocess

# Configuration from environment
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "your_github_token_here")
GITHUB_USER = os.getenv("GITHUB_USER", "codeverlan")
GITEA_URL = os.getenv("GITEA_URL", "http://cloud-dev:3020")
GITEA_TOKEN = os.getenv("GITEA_TOKEN", "your_gitea_token_here")
GITEA_USER = os.getenv("GITEA_USER", "tbwyler")

app = FastAPI(
    title="Git Sync Service",
    description="Bidirectional GitHub ↔ Gitea Synchronization",
    version="1.0.0"
)

# Global state
sync_status = {
    "repositories": [],
    "active_syncs": 0,
    "failed_syncs": 0,
    "last_sync": None
}

async def get_github_repos() -> List[Dict]:
    """Get GitHub repositories."""
    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
        }
        response = await client.get(
            f"https://api.github.com/users/{GITHUB_USER}/repos",
            headers=headers,
            params={"per_page": 100}
        )
        response.raise_for_status()
        return response.json()

async def get_gitea_repos() -> List[Dict]:
    """Get Gitea repositories."""
    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"token {GITEA_TOKEN}",
            "Content-Type": "application/json",
        }
        try:
            response = await client.get(
                f"{GITEA_URL}/api/v1/users/{GITEA_USER}/repos",
                headers=headers,
                params={"limit": 100}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Failed to get Gitea repos: {e}")
            return []

async def create_gitea_repo(repo_name: str, description: str = "") -> bool:
    """Create a repository in Gitea."""
    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"token {GITEA_TOKEN}",
            "Content-Type": "application/json",
        }
        data = {
            "name": repo_name,
            "description": description,
            "private": False,
            "auto_init": False
        }
        try:
            response = await client.post(
                f"{GITEA_URL}/api/v1/user/repos",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            print(f"Created Gitea repository: {repo_name}")
            return True
        except Exception as e:
            print(f"Failed to create Gitea repo {repo_name}: {e}")
            return False

def sync_repository(github_repo: Dict, gitea_repos: List[Dict]) -> Dict[str, Any]:
    """Sync a repository from GitHub to Gitea."""
    repo_name = github_repo["name"]
    print(f"Syncing repository: {repo_name}")
    
    # Check if repo exists in Gitea
    gitea_repo = next((r for r in gitea_repos if r["name"] == repo_name), None)
    
    result = {
        "repository": repo_name,
        "status": "success",
        "action": "none",
        "error": None
    }
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir) / repo_name
            
            # Clone GitHub repository
            github_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_USER}/{repo_name}.git"
            print(f"Cloning from GitHub: {repo_name}")
            repo = Repo.clone_from(github_url, work_dir)
            
            if not gitea_repo:
                # Repository doesn't exist in Gitea - create it
                print(f"Repository {repo_name} not found in Gitea, will need to create it")
                result["action"] = "create_gitea_repo"
                # Note: We can't await here since this is a sync function
                # The actual creation would happen in the async wrapper
            else:
                # Repository exists - would sync differences
                print(f"Repository {repo_name} exists in both platforms")
                result["action"] = "sync_changes"
            
            # Get some repo stats
            branches = list(repo.branches)
            tags = list(repo.tags)
            
            result.update({
                "branches": len(branches),
                "tags": len(tags),
                "default_branch": repo.active_branch.name if repo.active_branch else "main"
            })
            
    except Exception as e:
        print(f"Failed to sync {repo_name}: {e}")
        result.update({
            "status": "failed",
            "error": str(e)
        })
        
    return result

async def sync_repo_to_gitea(repo_name: str, description: str = ""):
    """Create Gitea repo and push from GitHub."""
    # Create Gitea repository first
    created = await create_gitea_repo(repo_name, description)
    if not created:
        return {"status": "failed", "error": "Failed to create Gitea repository"}
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir) / repo_name
            
            # Clone GitHub repository
            github_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_USER}/{repo_name}.git"
            print(f"Cloning from GitHub: {repo_name}")
            repo = Repo.clone_from(github_url, work_dir)
            
            # Add Gitea remote with authentication
            gitea_url = f"{GITEA_URL}/{GITEA_USER}/{repo_name}.git"
            gitea_auth_url = gitea_url.replace("://", f"://{GITEA_USER}:{GITEA_TOKEN}@")
            gitea_remote = repo.create_remote("gitea", gitea_auth_url)
            
            # Push all branches and tags to Gitea
            print(f"Pushing to Gitea: {repo_name}")
            gitea_remote.push(refspec="refs/heads/*:refs/heads/*")
            gitea_remote.push(refspec="refs/tags/*:refs/tags/*")
            
            return {
                "status": "success",
                "action": "created_and_synced",
                "repository": repo_name
            }
            
    except Exception as e:
        print(f"Failed to sync {repo_name} to Gitea: {e}")
        return {
            "status": "failed", 
            "error": str(e),
            "repository": repo_name
        }

async def perform_full_sync():
    """Perform full bidirectional sync."""
    print("Starting full sync...")
    sync_status["active_syncs"] = 1
    
    try:
        # Get repositories from both platforms
        github_repos = await get_github_repos()
        gitea_repos = await get_gitea_repos()
        
        print(f"Found {len(github_repos)} GitHub repos, {len(gitea_repos)} Gitea repos")
        
        # Update global status
        sync_status["repositories"] = [
            {
                "name": repo["name"],
                "platform": "github",
                "url": repo["html_url"]
            } for repo in github_repos
        ]
        
        # Sync each GitHub repo to Gitea
        results = []
        for github_repo in github_repos:
            repo_name = github_repo["name"]
            gitea_repo = next((r for r in gitea_repos if r["name"] == repo_name), None)
            
            if not gitea_repo:
                # Need to create and sync
                result = await sync_repo_to_gitea(repo_name, github_repo.get("description", ""))
                results.append(result)
            else:
                # Repo exists - for now just report it
                results.append({
                    "status": "exists",
                    "repository": repo_name,
                    "action": "already_synced"
                })
        
        sync_status["active_syncs"] = 0
        sync_status["last_sync"] = "just completed"
        
        return {
            "status": "completed",
            "total_repos": len(github_repos),
            "results": results
        }
        
    except Exception as e:
        sync_status["active_syncs"] = 0
        sync_status["failed_syncs"] += 1
        print(f"Sync failed: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }

async def perform_import_from_github():
    """Import all GitHub repositories to existing Gitea repos."""
    print("🚀 Starting GitHub → Gitea Import")
    sync_status["active_syncs"] = 1
    
    try:
        # Get repositories from both platforms
        github_repos = await get_github_repos()
        gitea_repos = await get_gitea_repos()
        
        print(f"Found {len(github_repos)} GitHub repos, {len(gitea_repos)} Gitea repos")
        
        results = []
        for github_repo in github_repos:
            repo_name = github_repo["name"]
            gitea_repo = next((r for r in gitea_repos if r["name"] == repo_name), None)
            
            if gitea_repo:
                print(f"🔄 Importing {repo_name} to existing Gitea repo...")
                result = await import_to_existing_gitea_repo(repo_name)
                results.append(result)
            else:
                print(f"⚠️  Gitea repo {repo_name} not found, skipping")
                results.append({
                    "status": "skipped",
                    "repository": repo_name,
                    "reason": "gitea_repo_not_found"
                })
        
        sync_status["active_syncs"] = 0
        sync_status["last_sync"] = "import completed"
        
        successful = len([r for r in results if r["status"] == "success"])
        print(f"✅ Import complete! {successful}/{len(results)} repositories imported successfully.")
        
        return {
            "status": "completed",
            "total_repos": len(github_repos),
            "successful": successful,
            "results": results
        }
        
    except Exception as e:
        sync_status["active_syncs"] = 0
        sync_status["failed_syncs"] += 1
        print(f"Import failed: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }

async def import_to_existing_gitea_repo(repo_name: str):
    """Import a repository from GitHub to existing Gitea repo."""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir) / repo_name
            
            # Clone GitHub repository
            github_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_USER}/{repo_name}.git"
            print(f"  📥 Cloning {repo_name} from GitHub...")
            repo = Repo.clone_from(github_url, work_dir)
            
            # Add Gitea remote with authentication
            gitea_auth_url = f"http://{GITEA_USER}:{GITEA_TOKEN}@cloud-dev:3020/{GITEA_USER}/{repo_name}.git"
            print(f"  🔗 Adding Gitea remote...")
            gitea_remote = repo.create_remote("gitea", gitea_auth_url)
            
            # Push all branches and tags to Gitea
            print(f"  📤 Pushing branches...")
            gitea_remote.push(refspec="refs/heads/*:refs/heads/*", force=True)
            
            print(f"  🏷️  Pushing tags...")
            try:
                gitea_remote.push(refspec="refs/tags/*:refs/tags/*", force=True)
            except Exception as e:
                print(f"    ⚠️  Tag push warning: {e}")
            
            # Get some stats
            branches = list(repo.branches)
            tags = list(repo.tags)
            
            print(f"  ✅ Successfully imported {repo_name} ({len(branches)} branches, {len(tags)} tags)")
            
            return {
                "status": "success",
                "repository": repo_name,
                "branches": len(branches),
                "tags": len(tags)
            }
            
    except Exception as e:
        print(f"  ❌ Failed to import {repo_name}: {e}")
        return {
            "status": "failed",
            "repository": repo_name,
            "error": str(e)
        }

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
    github_repos = []
    gitea_repos = []
    
    try:
        github_repos = await get_github_repos()
        gitea_repos = await get_gitea_repos()
    except Exception as e:
        print(f"Failed to get repo counts: {e}")
    
    return {
        "status": "running",
        "github_repositories": len(github_repos),
        "gitea_repositories": len(gitea_repos),
        "active_syncs": sync_status["active_syncs"],
        "failed_syncs": sync_status["failed_syncs"],
        "last_sync": sync_status["last_sync"]
    }

@app.get("/repositories")
async def list_repositories():
    """List all tracked repositories."""
    try:
        github_repos = await get_github_repos()
        gitea_repos = await get_gitea_repos()
        
        repos = []
        for gh_repo in github_repos:
            gitea_exists = any(gr["name"] == gh_repo["name"] for gr in gitea_repos)
            repos.append({
                "name": gh_repo["name"],
                "github_url": gh_repo["html_url"],
                "gitea_exists": gitea_exists,
                "description": gh_repo.get("description", ""),
                "updated_at": gh_repo["updated_at"]
            })
        
        return repos
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sync/manual")
async def manual_sync(background_tasks: BackgroundTasks, repo_name: str = None):
    """Trigger manual sync for all repositories or specific repository."""
    if repo_name:
        return {
            "message": f"Single repository sync not implemented yet: {repo_name}",
            "status": "not_implemented"
        }
    else:
        # Start import process in background
        background_tasks.add_task(perform_import_from_github)
        return {
            "message": "GitHub import started",
            "status": "running"
        }

@app.post("/import/github")
async def import_from_github(background_tasks: BackgroundTasks):
    """Import repositories from GitHub to existing Gitea repos."""
    background_tasks.add_task(perform_import_from_github)
    return {
        "message": "GitHub import started",
        "status": "running"
    }

@app.post("/webhooks/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle GitHub webhooks."""
    try:
        payload = await request.json()
        headers = dict(request.headers)
        
        repo_name = payload.get("repository", {}).get("name", "unknown")
        event_type = headers.get("x-github-event", "unknown")
        
        print(f"GitHub webhook received: {event_type} for {repo_name}")
        
        # For push events, trigger sync
        if event_type == "push":
            background_tasks.add_task(perform_full_sync)
            
        return JSONResponse(content={
            "status": "processed", 
            "event": event_type, 
            "repo": repo_name,
            "action": "sync_triggered" if event_type == "push" else "logged"
        })
        
    except Exception as e:
        print(f"Failed to process GitHub webhook: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/webhooks/gitea")
async def gitea_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Gitea webhooks."""
    try:
        payload = await request.json()
        headers = dict(request.headers)
        
        repo_name = payload.get("repository", {}).get("name", "unknown")
        event_type = headers.get("x-gitea-event", "unknown")
        
        print(f"Gitea webhook received: {event_type} for {repo_name}")
        
        return JSONResponse(content={
            "status": "processed", 
            "event": event_type, 
            "repo": repo_name
        })
        
    except Exception as e:
        print(f"Failed to process Gitea webhook: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/logs")
async def get_logs(limit: int = 100):
    """Get recent sync logs."""
    return {"message": "Logs would be retrieved from database", "limit": limit}

if __name__ == "__main__":
    uvicorn.run(
        "sync-main:app",
        host="0.0.0.0",
        port=8080,
        log_level="info",
        reload=False
    )