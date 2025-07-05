#!/usr/bin/env python3
"""
Webhook handler for GitHub and Gitea webhooks.
"""

import hmac
import hashlib
import json
from typing import Dict, Any, Optional
import structlog

from config.settings import Settings
from services.sync_engine import SyncEngine


class WebhookHandler:
    """Handles webhooks from GitHub and Gitea."""
    
    def __init__(self, settings: Settings, sync_engine: SyncEngine):
        self.settings = settings
        self.sync_engine = sync_engine
        self.logger = structlog.get_logger()
    
    async def handle_github_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """Handle GitHub webhook payload."""
        self.logger.info("Processing GitHub webhook", event=headers.get("x-github-event"))
        
        # Verify webhook signature if secret is configured
        if self.settings.webhook_secret:
            if not self._verify_github_signature(payload, headers):
                raise ValueError("Invalid webhook signature")
        
        event_type = headers.get("x-github-event")
        repository_name = payload.get("repository", {}).get("name")
        
        if not repository_name:
            self.logger.warning("No repository name in webhook payload")
            return {"sync_required": False}
        
        # Filter repositories
        if not self._should_sync_repository(repository_name):
            self.logger.info("Repository filtered out", repo=repository_name)
            return {"sync_required": False}
        
        # Process different event types
        if event_type in ["push", "create", "delete"]:
            return await self._handle_github_push_event(payload, repository_name)
        elif event_type == "repository" and payload.get("action") == "created":
            return await self._handle_github_repo_created(payload, repository_name)
        elif event_type == "release":
            return await self._handle_github_release_event(payload, repository_name)
        else:
            self.logger.info("Ignoring GitHub event", event=event_type, repo=repository_name)
            return {"sync_required": False}
    
    async def handle_gitea_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """Handle Gitea webhook payload."""
        self.logger.info("Processing Gitea webhook", event=headers.get("x-gitea-event"))
        
        # Verify webhook signature if secret is configured
        if self.settings.webhook_secret:
            if not self._verify_gitea_signature(payload, headers):
                raise ValueError("Invalid webhook signature")
        
        event_type = headers.get("x-gitea-event")
        repository_name = payload.get("repository", {}).get("name")
        
        if not repository_name:
            self.logger.warning("No repository name in webhook payload")
            return {"sync_required": False}
        
        # Filter repositories
        if not self._should_sync_repository(repository_name):
            self.logger.info("Repository filtered out", repo=repository_name)
            return {"sync_required": False}
        
        # Process different event types
        if event_type == "push":
            return await self._handle_gitea_push_event(payload, repository_name)
        elif event_type == "repository" and payload.get("action") == "created":
            return await self._handle_gitea_repo_created(payload, repository_name)
        elif event_type == "release":
            return await self._handle_gitea_release_event(payload, repository_name)
        else:
            self.logger.info("Ignoring Gitea event", event=event_type, repo=repository_name)
            return {"sync_required": False}
    
    def _verify_github_signature(self, payload: Dict[str, Any], headers: Dict[str, str]) -> bool:
        """Verify GitHub webhook signature."""
        signature = headers.get("x-hub-signature-256")
        if not signature:
            return False
        
        # Recreate the signature
        payload_body = json.dumps(payload, separators=(',', ':')).encode('utf-8')
        expected_signature = "sha256=" + hmac.new(
            self.settings.webhook_secret.encode('utf-8'),
            payload_body,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    def _verify_gitea_signature(self, payload: Dict[str, Any], headers: Dict[str, str]) -> bool:
        """Verify Gitea webhook signature."""
        signature = headers.get("x-gitea-signature")
        if not signature:
            return False
        
        # Recreate the signature
        payload_body = json.dumps(payload, separators=(',', ':')).encode('utf-8')
        expected_signature = hmac.new(
            self.settings.webhook_secret.encode('utf-8'),
            payload_body,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    def _should_sync_repository(self, repository_name: str) -> bool:
        """Check if repository should be synced based on filters."""
        included_repos = self.settings.included_repositories
        excluded_repos = self.settings.excluded_repositories or []
        
        # Check inclusion filter
        if included_repos and repository_name not in included_repos:
            return False
        
        # Check exclusion filter
        if repository_name in excluded_repos:
            return False
        
        return True
    
    async def _handle_github_push_event(self, payload: Dict[str, Any], repository_name: str) -> Dict[str, Any]:
        """Handle GitHub push event."""
        ref = payload.get("ref", "")
        deleted = payload.get("deleted", False)
        created = payload.get("created", False)
        
        self.logger.info(
            "GitHub push event",
            repo=repository_name,
            ref=ref,
            deleted=deleted,
            created=created,
            commits=len(payload.get("commits", []))
        )
        
        # Check if this is a branch we should sync
        if ref.startswith("refs/heads/") and self.settings.sync_branches:
            return {
                "sync_required": True,
                "repository": repository_name,
                "event_type": "push",
                "ref": ref,
                "source": "github"
            }
        elif ref.startswith("refs/tags/") and self.settings.sync_tags:
            return {
                "sync_required": True,
                "repository": repository_name,
                "event_type": "tag",
                "ref": ref,
                "source": "github"
            }
        
        return {"sync_required": False}
    
    async def _handle_gitea_push_event(self, payload: Dict[str, Any], repository_name: str) -> Dict[str, Any]:
        """Handle Gitea push event."""
        ref = payload.get("ref", "")
        deleted = payload.get("deleted", False)
        created = payload.get("created", False)
        
        self.logger.info(
            "Gitea push event",
            repo=repository_name,
            ref=ref,
            deleted=deleted,
            created=created,
            commits=len(payload.get("commits", []))
        )
        
        # Check if this is a branch we should sync
        if ref.startswith("refs/heads/") and self.settings.sync_branches:
            return {
                "sync_required": True,
                "repository": repository_name,
                "event_type": "push",
                "ref": ref,
                "source": "gitea"
            }
        elif ref.startswith("refs/tags/") and self.settings.sync_tags:
            return {
                "sync_required": True,
                "repository": repository_name,
                "event_type": "tag",
                "ref": ref,
                "source": "gitea"
            }
        
        return {"sync_required": False}
    
    async def _handle_github_repo_created(self, payload: Dict[str, Any], repository_name: str) -> Dict[str, Any]:
        """Handle GitHub repository creation event."""
        self.logger.info("GitHub repository created", repo=repository_name)
        
        return {
            "sync_required": True,
            "repository": repository_name,
            "event_type": "repository_created",
            "source": "github"
        }
    
    async def _handle_gitea_repo_created(self, payload: Dict[str, Any], repository_name: str) -> Dict[str, Any]:
        """Handle Gitea repository creation event."""
        self.logger.info("Gitea repository created", repo=repository_name)
        
        return {
            "sync_required": True,
            "repository": repository_name,
            "event_type": "repository_created",
            "source": "gitea"
        }
    
    async def _handle_github_release_event(self, payload: Dict[str, Any], repository_name: str) -> Dict[str, Any]:
        """Handle GitHub release event."""
        if not self.settings.sync_releases:
            return {"sync_required": False}
        
        action = payload.get("action")
        release = payload.get("release", {})
        tag_name = release.get("tag_name")
        
        self.logger.info(
            "GitHub release event",
            repo=repository_name,
            action=action,
            tag=tag_name
        )
        
        if action in ["published", "created", "edited", "deleted"]:
            return {
                "sync_required": True,
                "repository": repository_name,
                "event_type": "release",
                "action": action,
                "tag_name": tag_name,
                "source": "github"
            }
        
        return {"sync_required": False}
    
    async def _handle_gitea_release_event(self, payload: Dict[str, Any], repository_name: str) -> Dict[str, Any]:
        """Handle Gitea release event."""
        if not self.settings.sync_releases:
            return {"sync_required": False}
        
        action = payload.get("action")
        release = payload.get("release", {})
        tag_name = release.get("tag_name")
        
        self.logger.info(
            "Gitea release event",
            repo=repository_name,
            action=action,
            tag=tag_name
        )
        
        if action in ["published", "created", "edited", "deleted"]:
            return {
                "sync_required": True,
                "repository": repository_name,
                "event_type": "release",
                "action": action,
                "tag_name": tag_name,
                "source": "gitea"
            }
        
        return {"sync_required": False}