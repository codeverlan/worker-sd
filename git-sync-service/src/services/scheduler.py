#!/usr/bin/env python3
"""
Scheduler service for periodic synchronization tasks.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional
import structlog

from config.settings import Settings
from services.sync_engine import SyncEngine


class SyncScheduler:
    """Handles scheduled synchronization tasks."""
    
    def __init__(self, settings: Settings, sync_engine: SyncEngine):
        self.settings = settings
        self.sync_engine = sync_engine
        self.logger = structlog.get_logger()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            self.logger.warning("Scheduler already running")
            return
            
        self._running = True
        self.logger.info("Starting sync scheduler", interval=self.settings.sync_interval)
        
        # Start the main scheduler loop
        self._task = asyncio.create_task(self._scheduler_loop())
        
    async def stop(self) -> None:
        """Stop the scheduler."""
        if not self._running:
            return
            
        self.logger.info("Stopping sync scheduler")
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            
        self.logger.info("Sync scheduler stopped")
        
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        self.logger.info("Scheduler loop started")
        last_sync_time = datetime.now(timezone.utc)
        
        while self._running:
            try:
                current_time = datetime.now(timezone.utc)
                
                # Check if it's time for a sync
                if (current_time - last_sync_time).total_seconds() >= self.settings.sync_interval:
                    self.logger.info("Starting scheduled sync")
                    
                    try:
                        await self.sync_engine.sync_repositories()
                        last_sync_time = current_time
                        self.logger.info("Scheduled sync completed successfully")
                        
                    except Exception as e:
                        self.logger.error("Scheduled sync failed", error=str(e))
                        
                        # Wait a bit before retrying
                        await asyncio.sleep(self.settings.retry_delay)
                
                # Health check
                await self._perform_health_check()
                
                # Sleep for a short interval before checking again
                await asyncio.sleep(min(60, self.settings.sync_interval // 10))
                
            except asyncio.CancelledError:
                self.logger.info("Scheduler loop cancelled")
                break
            except Exception as e:
                self.logger.error("Unexpected error in scheduler loop", error=str(e))
                await asyncio.sleep(30)  # Wait before retrying
                
    async def _perform_health_check(self) -> None:
        """Perform periodic health checks."""
        try:
            if not self.sync_engine.is_healthy():
                self.logger.warning("Sync engine is unhealthy")
                
            # Additional health checks could be added here
            # For example: checking connectivity to GitHub/Gitea APIs
            
        except Exception as e:
            self.logger.error("Health check failed", error=str(e))
            
    async def trigger_immediate_sync(self, repo_name: Optional[str] = None) -> None:
        """Trigger an immediate sync outside of the regular schedule."""
        self.logger.info("Triggering immediate sync", repo=repo_name)
        
        try:
            if repo_name:
                await self.sync_engine.sync_repository(repo_name)
            else:
                await self.sync_engine.sync_repositories()
                
            self.logger.info("Immediate sync completed", repo=repo_name)
            
        except Exception as e:
            self.logger.error("Immediate sync failed", repo=repo_name, error=str(e))
            raise
            
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running