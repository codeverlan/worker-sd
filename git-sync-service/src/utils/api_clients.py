#!/usr/bin/env python3
"""
API clients for GitHub and Gitea.
"""

import asyncio
from typing import Dict, List, Optional, Any
import structlog
import httpx


class GitHubClient:
    """GitHub API client."""
    
    def __init__(self, token: str, username: str):
        self.token = token
        self.username = username
        self.base_url = "https://api.github.com"
        self.logger = structlog.get_logger()
        
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "git-sync-service/1.0"
        }
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an authenticated request to GitHub API."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method,
                    url,
                    headers=self.headers,
                    timeout=30.0,
                    **kwargs
                )
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                self.logger.error("GitHub API error", status=e.response.status_code, url=url, error=str(e))
                raise
            except Exception as e:
                self.logger.error("GitHub API request failed", url=url, error=str(e))
                raise
    
    async def list_repositories(self) -> List[Dict[str, Any]]:
        """List user repositories."""
        self.logger.info("Fetching GitHub repositories", user=self.username)
        
        repos = []
        page = 1
        per_page = 100
        
        while True:
            data = await self._make_request(
                "GET",
                f"users/{self.username}/repos",
                params={"page": page, "per_page": per_page, "sort": "updated"}
            )
            
            if not data:
                break
                
            repos.extend(data)
            
            if len(data) < per_page:
                break
                
            page += 1
        
        self.logger.info(f"Found {len(repos)} GitHub repositories")
        return repos
    
    async def get_repository(self, repo_name: str) -> Optional[Dict[str, Any]]:
        """Get repository information."""
        try:
            return await self._make_request("GET", f"repos/{self.username}/{repo_name}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
    
    async def create_repository(self, repo_name: str, description: str = "", private: bool = False) -> Dict[str, Any]:
        """Create a new repository."""
        self.logger.info("Creating GitHub repository", repo=repo_name)
        
        data = {
            "name": repo_name,
            "description": description,
            "private": private,
            "has_issues": True,
            "has_projects": True,
            "has_wiki": True
        }
        
        return await self._make_request("POST", "user/repos", json=data)
    
    async def delete_repository(self, repo_name: str) -> None:
        """Delete a repository."""
        self.logger.warning("Deleting GitHub repository", repo=repo_name)
        await self._make_request("DELETE", f"repos/{self.username}/{repo_name}")
    
    async def get_branches(self, repo_name: str) -> List[Dict[str, Any]]:
        """Get repository branches."""
        return await self._make_request("GET", f"repos/{self.username}/{repo_name}/branches")
    
    async def get_tags(self, repo_name: str) -> List[Dict[str, Any]]:
        """Get repository tags."""
        return await self._make_request("GET", f"repos/{self.username}/{repo_name}/tags")
    
    async def get_releases(self, repo_name: str) -> List[Dict[str, Any]]:
        """Get repository releases."""
        return await self._make_request("GET", f"repos/{self.username}/{repo_name}/releases")
    
    async def create_webhook(self, repo_name: str, webhook_url: str, secret: str) -> Dict[str, Any]:
        """Create a webhook for the repository."""
        self.logger.info("Creating GitHub webhook", repo=repo_name, url=webhook_url)
        
        data = {
            "name": "web",
            "active": True,
            "events": ["push", "create", "delete", "repository", "release"],
            "config": {
                "url": webhook_url,
                "content_type": "json",
                "secret": secret,
                "insecure_ssl": "0"
            }
        }
        
        return await self._make_request("POST", f"repos/{self.username}/{repo_name}/hooks", json=data)


class GiteaClient:
    """Gitea API client."""
    
    def __init__(self, base_url: str, token: str, username: str):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.username = username
        self.logger = structlog.get_logger()
        
        self.headers = {
            "Authorization": f"token {token}",
            "Content-Type": "application/json",
            "User-Agent": "git-sync-service/1.0"
        }
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an authenticated request to Gitea API."""
        url = f"{self.base_url}/api/v1/{endpoint.lstrip('/')}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method,
                    url,
                    headers=self.headers,
                    timeout=30.0,
                    **kwargs
                )
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                self.logger.error("Gitea API error", status=e.response.status_code, url=url, error=str(e))
                raise
            except Exception as e:
                self.logger.error("Gitea API request failed", url=url, error=str(e))
                raise
    
    async def list_repositories(self) -> List[Dict[str, Any]]:
        """List user repositories."""
        self.logger.info("Fetching Gitea repositories", user=self.username)
        
        repos = []
        page = 1
        limit = 50
        
        while True:
            data = await self._make_request(
                "GET",
                f"users/{self.username}/repos",
                params={"page": page, "limit": limit}
            )
            
            if not data:
                break
                
            repos.extend(data)
            
            if len(data) < limit:
                break
                
            page += 1
        
        self.logger.info(f"Found {len(repos)} Gitea repositories")
        return repos
    
    async def get_repository(self, repo_name: str) -> Optional[Dict[str, Any]]:
        """Get repository information."""
        try:
            return await self._make_request("GET", f"repos/{self.username}/{repo_name}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
    
    async def create_repository(self, repo_name: str, description: str = "", private: bool = False) -> Dict[str, Any]:
        """Create a new repository."""
        self.logger.info("Creating Gitea repository", repo=repo_name)
        
        data = {
            "name": repo_name,
            "description": description,
            "private": private,
            "auto_init": False
        }
        
        return await self._make_request("POST", "user/repos", json=data)
    
    async def delete_repository(self, repo_name: str) -> None:
        """Delete a repository."""
        self.logger.warning("Deleting Gitea repository", repo=repo_name)
        await self._make_request("DELETE", f"repos/{self.username}/{repo_name}")
    
    async def get_branches(self, repo_name: str) -> List[Dict[str, Any]]:
        """Get repository branches."""
        return await self._make_request("GET", f"repos/{self.username}/{repo_name}/branches")
    
    async def get_tags(self, repo_name: str) -> List[Dict[str, Any]]:
        """Get repository tags."""
        return await self._make_request("GET", f"repos/{self.username}/{repo_name}/tags")
    
    async def get_releases(self, repo_name: str) -> List[Dict[str, Any]]:
        """Get repository releases."""
        return await self._make_request("GET", f"repos/{self.username}/{repo_name}/releases")
    
    async def create_webhook(self, repo_name: str, webhook_url: str, secret: str) -> Dict[str, Any]:
        """Create a webhook for the repository."""
        self.logger.info("Creating Gitea webhook", repo=repo_name, url=webhook_url)
        
        data = {
            "type": "gitea",
            "active": True,
            "events": ["push", "create", "delete", "repository", "release"],
            "config": {
                "url": webhook_url,
                "content_type": "json",
                "secret": secret
            }
        }
        
        return await self._make_request("POST", f"repos/{self.username}/{repo_name}/hooks", json=data)