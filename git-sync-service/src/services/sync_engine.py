#!/usr/bin/env python3
"""
Core synchronization engine for bidirectional GitHub ↔ Gitea sync.
"""

import asyncio
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import structlog
import httpx
from git import Repo, GitCommandError
from sqlalchemy.orm import Session

from config.settings import Settings
from database.models import SyncRepository, SyncLog, get_session
from utils.git_operations import GitOperations
from utils.api_clients import GitHubClient, GiteaClient


class SyncConflictError(Exception):
    """Raised when a sync conflict cannot be automatically resolved."""
    pass


class SyncEngine:
    """Core synchronization engine."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = structlog.get_logger()
        self.github_client = GitHubClient(settings.github_token, settings.github_user)
        self.gitea_client = GiteaClient(settings.gitea_url, settings.gitea_token, settings.gitea_user)
        self.git_ops = GitOperations(settings)
        self._healthy = True
        
    def is_healthy(self) -> bool:
        """Check if sync engine is healthy."""
        return self._healthy
    
    async def get_status(self) -> Dict[str, Any]:
        """Get sync engine status."""
        with get_session() as session:
            total_repos = session.query(SyncRepository).count()
            active_syncs = session.query(SyncRepository).filter(
                SyncRepository.sync_status == "syncing"
            ).count()
            failed_syncs = session.query(SyncRepository).filter(
                SyncRepository.sync_status == "failed"
            ).count()
            
        return {
            "status": "healthy" if self._healthy else "unhealthy",
            "total_repositories": total_repos,
            "active_syncs": active_syncs,
            "failed_syncs": failed_syncs,
            "last_sync": datetime.now(timezone.utc).isoformat()
        }
    
    async def list_repositories(self) -> List[Dict[str, Any]]:
        """List all tracked repositories."""
        repos = []
        with get_session() as session:
            db_repos = session.query(SyncRepository).all()
            for repo in db_repos:
                repos.append({
                    "name": repo.name,
                    "github_url": repo.github_url,
                    "gitea_url": repo.gitea_url,
                    "sync_status": repo.sync_status,
                    "last_sync": repo.last_sync.isoformat() if repo.last_sync else None,
                    "conflict_count": repo.conflict_count
                })
        return repos
    
    async def discover_repositories(self) -> List[str]:
        """Discover repositories from both GitHub and Gitea."""
        self.logger.info("Discovering repositories")
        
        # Get GitHub repositories
        github_repos = await self.github_client.list_repositories()
        gitea_repos = await self.gitea_client.list_repositories()
        
        # Filter repositories based on settings
        included_repos = self.settings.included_repositories
        excluded_repos = self.settings.excluded_repositories or []
        
        all_repos = set()
        
        # Add GitHub repos
        for repo in github_repos:
            name = repo["name"]
            if included_repos and name not in included_repos:
                continue
            if name in excluded_repos:
                continue
            all_repos.add(name)
            
        # Add Gitea repos
        for repo in gitea_repos:
            name = repo["name"]
            if included_repos and name not in included_repos:
                continue
            if name in excluded_repos:
                continue
            all_repos.add(name)
        
        self.logger.info(f"Discovered {len(all_repos)} repositories", repos=list(all_repos))
        return list(all_repos)
    
    async def sync_repositories(self, repo_name: Optional[str] = None) -> None:
        """Sync all repositories or a specific repository."""
        try:
            if repo_name:
                await self.sync_repository(repo_name)
            else:
                repos = await self.discover_repositories()
                
                # Limit concurrent syncs
                semaphore = asyncio.Semaphore(self.settings.max_concurrent_syncs)
                
                async def sync_with_semaphore(name: str):
                    async with semaphore:
                        await self.sync_repository(name)
                
                # Run syncs concurrently
                tasks = [sync_with_semaphore(name) for name in repos]
                await asyncio.gather(*tasks, return_exceptions=True)
                
        except Exception as e:
            self.logger.error("Failed to sync repositories", error=str(e))
            self._healthy = False
            raise
    
    async def sync_repository(self, repo_name: str, source: str = "auto") -> Dict[str, Any]:
        """Sync a specific repository bidirectionally."""
        self.logger.info("Starting repository sync", repo=repo_name, source=source)
        
        # Update repository status
        await self._update_repo_status(repo_name, "syncing")
        
        try:
            # Get repository information from both platforms
            github_repo = await self.github_client.get_repository(repo_name)
            gitea_repo = await self.gitea_client.get_repository(repo_name)
            
            # Create repository record if it doesn't exist
            await self._ensure_repository_record(repo_name, github_repo, gitea_repo)
            
            # Perform bidirectional sync
            result = await self._perform_bidirectional_sync(repo_name, github_repo, gitea_repo, source)
            
            # Update sync status
            await self._update_repo_status(repo_name, "synced")
            await self._log_sync_result(repo_name, "success", result)
            
            self.logger.info("Repository sync completed", repo=repo_name, result=result)
            return result
            
        except SyncConflictError as e:
            await self._update_repo_status(repo_name, "conflict")
            await self._log_sync_result(repo_name, "conflict", {"error": str(e)})
            self.logger.warning("Sync conflict detected", repo=repo_name, error=str(e))
            raise
            
        except Exception as e:
            await self._update_repo_status(repo_name, "failed")
            await self._log_sync_result(repo_name, "failed", {"error": str(e)})
            self.logger.error("Repository sync failed", repo=repo_name, error=str(e))
            raise
    
    async def _perform_bidirectional_sync(
        self, 
        repo_name: str, 
        github_repo: Optional[Dict], 
        gitea_repo: Optional[Dict],
        source: str
    ) -> Dict[str, Any]:
        """Perform the actual bidirectional synchronization."""
        
        # Create temporary directory for git operations
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir) / repo_name
            
            # Clone or create repositories as needed
            github_exists = github_repo is not None
            gitea_exists = gitea_repo is not None
            
            if not github_exists and not gitea_exists:
                raise ValueError(f"Repository {repo_name} does not exist on either platform")
            
            # Handle repository creation scenarios
            if github_exists and not gitea_exists:
                # Create Gitea repository from GitHub
                await self._create_gitea_from_github(repo_name, work_dir)
                return {"action": "created_gitea", "source": "github"}
                
            elif gitea_exists and not github_exists:
                # Create GitHub repository from Gitea
                await self._create_github_from_gitea(repo_name, work_dir)
                return {"action": "created_github", "source": "gitea"}
            
            # Both repositories exist - perform bidirectional sync
            else:
                return await self._sync_existing_repositories(repo_name, work_dir, source)
    
    async def _create_gitea_from_github(self, repo_name: str, work_dir: Path) -> None:
        """Create Gitea repository from GitHub repository."""
        self.logger.info("Creating Gitea repository from GitHub", repo=repo_name)
        
        # Clone GitHub repository
        github_url = f"https://{self.settings.github_token}@github.com/{self.settings.github_user}/{repo_name}.git"
        repo = Repo.clone_from(github_url, work_dir)
        
        # Create Gitea repository
        await self.gitea_client.create_repository(repo_name)
        
        # Add Gitea remote and push
        gitea_url = f"{self.settings.gitea_url}/{self.settings.gitea_user}/{repo_name}.git"
        gitea_remote = repo.create_remote("gitea", gitea_url)
        gitea_remote.push(refspec="refs/heads/*:refs/heads/*")
        gitea_remote.push(refspec="refs/tags/*:refs/tags/*")
    
    async def _create_github_from_gitea(self, repo_name: str, work_dir: Path) -> None:
        """Create GitHub repository from Gitea repository."""
        self.logger.info("Creating GitHub repository from Gitea", repo=repo_name)
        
        # Clone Gitea repository
        gitea_url = f"{self.settings.gitea_url}/{self.settings.gitea_user}/{repo_name}.git"
        repo = Repo.clone_from(gitea_url, work_dir)
        
        # Create GitHub repository
        await self.github_client.create_repository(repo_name)
        
        # Add GitHub remote and push
        github_url = f"https://{self.settings.github_token}@github.com/{self.settings.github_user}/{repo_name}.git"
        github_remote = repo.create_remote("github", github_url)
        github_remote.push(refspec="refs/heads/*:refs/heads/*")
        github_remote.push(refspec="refs/tags/*:refs/tags/*")
    
    async def _sync_existing_repositories(self, repo_name: str, work_dir: Path, source: str) -> Dict[str, Any]:
        """Sync two existing repositories bidirectionally."""
        self.logger.info("Syncing existing repositories", repo=repo_name, source=source)
        
        # Clone GitHub repository as base
        github_url = f"https://{self.settings.github_token}@github.com/{self.settings.github_user}/{repo_name}.git"
        repo = Repo.clone_from(github_url, work_dir)
        
        # Add Gitea remote
        gitea_url = f"{self.settings.gitea_url}/{self.settings.gitea_user}/{repo_name}.git"
        gitea_remote = repo.create_remote("gitea", gitea_url)
        gitea_remote.fetch()
        
        # Analyze differences
        differences = await self._analyze_repository_differences(repo)
        
        if not differences["has_conflicts"]:
            # No conflicts - perform straightforward sync
            return await self._perform_simple_sync(repo, differences, source)
        else:
            # Handle conflicts based on resolution strategy
            return await self._handle_sync_conflicts(repo, differences, source)
    
    async def _analyze_repository_differences(self, repo: Repo) -> Dict[str, Any]:
        """Analyze differences between GitHub and Gitea repositories."""
        differences = {
            "has_conflicts": False,
            "github_ahead": [],
            "gitea_ahead": [],
            "diverged_branches": [],
            "new_branches": {"github": [], "gitea": []},
            "new_tags": {"github": [], "gitea": []}
        }
        
        # Compare branches
        github_branches = {ref.name.replace("origin/", "") for ref in repo.refs if ref.name.startswith("origin/")}
        gitea_branches = {ref.name.replace("gitea/", "") for ref in repo.refs if ref.name.startswith("gitea/")}
        
        all_branches = github_branches | gitea_branches
        
        for branch in all_branches:
            github_ref = f"origin/{branch}"
            gitea_ref = f"gitea/{branch}"
            
            github_exists = github_ref in [ref.name for ref in repo.refs]
            gitea_exists = gitea_ref in [ref.name for ref in repo.refs]
            
            if github_exists and not gitea_exists:
                differences["new_branches"]["github"].append(branch)
            elif gitea_exists and not github_exists:
                differences["new_branches"]["gitea"].append(branch)
            elif github_exists and gitea_exists:
                # Check if branches have diverged
                try:
                    github_commit = repo.commit(github_ref)
                    gitea_commit = repo.commit(gitea_ref)
                    
                    if github_commit.hexsha != gitea_commit.hexsha:
                        # Check if one is ahead of the other
                        github_ahead = list(repo.iter_commits(f"{gitea_ref}..{github_ref}"))
                        gitea_ahead = list(repo.iter_commits(f"{github_ref}..{gitea_ref}"))
                        
                        if github_ahead and gitea_ahead:
                            differences["diverged_branches"].append(branch)
                            differences["has_conflicts"] = True
                        elif github_ahead:
                            differences["github_ahead"].append(branch)
                        elif gitea_ahead:
                            differences["gitea_ahead"].append(branch)
                            
                except Exception as e:
                    self.logger.warning("Failed to compare branches", branch=branch, error=str(e))
        
        return differences
    
    async def _perform_simple_sync(self, repo: Repo, differences: Dict, source: str) -> Dict[str, Any]:
        """Perform simple sync when there are no conflicts."""
        actions = []
        
        # Push new GitHub branches to Gitea
        for branch in differences["new_branches"]["github"]:
            repo.git.push("gitea", f"origin/{branch}:{branch}")
            actions.append(f"pushed_to_gitea: {branch}")
        
        # Push new Gitea branches to GitHub
        for branch in differences["new_branches"]["gitea"]:
            repo.git.push("origin", f"gitea/{branch}:{branch}")
            actions.append(f"pushed_to_github: {branch}")
        
        # Sync branches where one is ahead
        for branch in differences["github_ahead"]:
            repo.git.push("gitea", f"origin/{branch}:{branch}")
            actions.append(f"synced_to_gitea: {branch}")
        
        for branch in differences["gitea_ahead"]:
            repo.git.push("origin", f"gitea/{branch}:{branch}")
            actions.append(f"synced_to_github: {branch}")
        
        # Sync tags if enabled
        if self.settings.sync_tags:
            repo.git.push("gitea", "--tags")
            repo.git.push("origin", "gitea/*:refs/tags/*")
            actions.append("synced_tags")
        
        return {"action": "synced", "details": actions}
    
    async def _handle_sync_conflicts(self, repo: Repo, differences: Dict, source: str) -> Dict[str, Any]:
        """Handle sync conflicts based on resolution strategy."""
        if self.settings.conflict_resolution == "manual":
            raise SyncConflictError(f"Manual intervention required for conflicted branches: {differences['diverged_branches']}")
        
        actions = []
        
        for branch in differences["diverged_branches"]:
            if self.settings.conflict_resolution == "github_wins":
                # Force push GitHub version to Gitea
                repo.git.push("gitea", f"origin/{branch}:{branch}", "--force")
                actions.append(f"github_wins: {branch}")
            elif self.settings.conflict_resolution == "gitea_wins":
                # Force push Gitea version to GitHub
                repo.git.push("origin", f"gitea/{branch}:{branch}", "--force")
                actions.append(f"gitea_wins: {branch}")
        
        return {"action": "conflict_resolved", "details": actions}
    
    async def _ensure_repository_record(self, repo_name: str, github_repo: Optional[Dict], gitea_repo: Optional[Dict]) -> None:
        """Ensure repository record exists in database."""
        with get_session() as session:
            existing = session.query(SyncRepository).filter_by(name=repo_name).first()
            if not existing:
                repo_record = SyncRepository(
                    name=repo_name,
                    github_url=github_repo["clone_url"] if github_repo else None,
                    gitea_url=f"{self.settings.gitea_url}/{self.settings.gitea_user}/{repo_name}.git" if gitea_repo else None,
                    sync_status="pending",
                    created_at=datetime.now(timezone.utc)
                )
                session.add(repo_record)
                session.commit()
    
    async def _update_repo_status(self, repo_name: str, status: str) -> None:
        """Update repository sync status."""
        with get_session() as session:
            repo = session.query(SyncRepository).filter_by(name=repo_name).first()
            if repo:
                repo.sync_status = status
                if status == "synced":
                    repo.last_sync = datetime.now(timezone.utc)
                elif status == "conflict":
                    repo.conflict_count += 1
                session.commit()
    
    async def _log_sync_result(self, repo_name: str, status: str, details: Dict) -> None:
        """Log sync result to database."""
        with get_session() as session:
            log_entry = SyncLog(
                repository_name=repo_name,
                sync_status=status,
                details=details,
                timestamp=datetime.now(timezone.utc)
            )
            session.add(log_entry)
            session.commit()
    
    async def get_recent_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent sync logs."""
        logs = []
        with get_session() as session:
            db_logs = session.query(SyncLog).order_by(SyncLog.timestamp.desc()).limit(limit).all()
            for log in db_logs:
                logs.append({
                    "repository": log.repository_name,
                    "status": log.sync_status,
                    "details": log.details,
                    "timestamp": log.timestamp.isoformat()
                })
        return logs
    
    async def resolve_conflict(self, repo_name: str, resolution: Dict[str, Any]) -> Dict[str, Any]:
        """Manually resolve a repository conflict."""
        self.logger.info("Resolving conflict manually", repo=repo_name, resolution=resolution)
        
        # Implementation would depend on the specific resolution strategy
        # For now, return a placeholder
        return {"status": "resolved", "repository": repo_name, "resolution": resolution}