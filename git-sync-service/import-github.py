#!/usr/bin/env python3
"""
Import GitHub repositories to existing empty Gitea repositories
"""

import asyncio
import os
import tempfile
from pathlib import Path
from git import Repo
import httpx

# Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "your_github_token_here")
GITHUB_USER = os.getenv("GITHUB_USER", "codeverlan")
GITEA_URL = os.getenv("GITEA_URL", "http://cloud-dev:3020")
GITEA_TOKEN = os.getenv("GITEA_TOKEN", "your_gitea_token_here")
GITEA_USER = os.getenv("GITEA_USER", "tbwyler")

async def get_github_repos():
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

def import_repository(repo_name: str):
    """Import a repository from GitHub to existing Gitea repo."""
    print(f"\n🔄 Importing {repo_name}...")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir) / repo_name
            
            # Clone GitHub repository
            github_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_USER}/{repo_name}.git"
            print(f"  📥 Cloning from GitHub...")
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
            
            print(f"  ✅ Successfully imported {repo_name}")
            print(f"     📊 {len(branches)} branches, {len(tags)} tags")
            
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

async def main():
    """Import all GitHub repositories to Gitea."""
    print("🚀 Starting GitHub → Gitea Import")
    print("=" * 50)
    
    # Get GitHub repositories
    print("📋 Fetching GitHub repositories...")
    github_repos = await get_github_repos()
    print(f"   Found {len(github_repos)} repositories")
    
    # Import each repository
    results = []
    for i, repo in enumerate(github_repos, 1):
        repo_name = repo["name"]
        print(f"\n[{i}/{len(github_repos)}] Processing {repo_name}")
        result = import_repository(repo_name)
        results.append(result)
    
    # Summary
    print("\n" + "=" * 50)
    print("📈 IMPORT SUMMARY")
    print("=" * 50)
    
    successful = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "failed"]
    
    print(f"✅ Successful imports: {len(successful)}")
    for r in successful:
        print(f"   • {r['repository']} ({r['branches']} branches, {r['tags']} tags)")
    
    if failed:
        print(f"\n❌ Failed imports: {len(failed)}")
        for r in failed:
            print(f"   • {r['repository']}: {r['error']}")
    
    print(f"\n🎉 Import complete! {len(successful)}/{len(results)} repositories imported successfully.")

if __name__ == "__main__":
    asyncio.run(main())