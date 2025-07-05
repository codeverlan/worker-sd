#!/usr/bin/env python3
"""
Database models for Git Sync Service.
"""

import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from contextlib import contextmanager

from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Text, Boolean, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from config.settings import Settings

Base = declarative_base()

# Global database session
_engine = None
_SessionLocal = None


class SyncRepository(Base):
    """Model for tracking synchronized repositories."""
    
    __tablename__ = "sync_repositories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    github_url = Column(String, nullable=True)
    gitea_url = Column(String, nullable=True)
    sync_status = Column(String, default="pending")  # pending, syncing, synced, failed, conflict
    last_sync = Column(DateTime(timezone=True), nullable=True)
    conflict_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Configuration for this repository
    config = Column(JSON, nullable=True)  # Store repo-specific settings
    
    def __repr__(self):
        return f"<SyncRepository(name='{self.name}', status='{self.sync_status}')>"


class SyncLog(Base):
    """Model for logging synchronization events."""
    
    __tablename__ = "sync_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    repository_name = Column(String, index=True, nullable=False)
    sync_status = Column(String, nullable=False)  # success, failed, conflict, skipped
    details = Column(JSON, nullable=True)  # Store detailed information about the sync
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Additional metadata
    source = Column(String, nullable=True)  # github, gitea, scheduled, manual
    duration_seconds = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<SyncLog(repo='{self.repository_name}', status='{self.sync_status}', time='{self.timestamp}')>"


class SyncConflict(Base):
    """Model for tracking unresolved sync conflicts."""
    
    __tablename__ = "sync_conflicts"
    
    id = Column(Integer, primary_key=True, index=True)
    repository_name = Column(String, index=True, nullable=False)
    conflict_type = Column(String, nullable=False)  # branch_diverged, merge_conflict, etc.
    branch_name = Column(String, nullable=True)
    github_commit = Column(String, nullable=True)
    gitea_commit = Column(String, nullable=True)
    conflict_details = Column(JSON, nullable=True)  # Detailed conflict information
    resolved = Column(Boolean, default=False)
    resolution_strategy = Column(String, nullable=True)  # github_wins, gitea_wins, manual
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<SyncConflict(repo='{self.repository_name}', type='{self.conflict_type}', resolved={self.resolved})>"


class WebhookEvent(Base):
    """Model for tracking webhook events."""
    
    __tablename__ = "webhook_events"
    
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False)  # github, gitea
    event_type = Column(String, nullable=False)  # push, create, delete, etc.
    repository_name = Column(String, index=True, nullable=False)
    event_id = Column(String, nullable=True)  # Unique ID from the webhook source
    payload = Column(JSON, nullable=False)  # Full webhook payload
    processed = Column(Boolean, default=False)
    sync_triggered = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<WebhookEvent(source='{self.source}', type='{self.event_type}', repo='{self.repository_name}')>"


async def init_db(database_url: Optional[str] = None) -> None:
    """Initialize the database."""
    global _engine, _SessionLocal
    
    if not database_url:
        settings = Settings()
        database_url = settings.database_url
    
    _engine = create_engine(
        database_url,
        echo=False,  # Set to True for SQL debugging
        pool_pre_ping=True,  # Verify connections before use
    )
    
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    
    # Create all tables
    Base.metadata.create_all(bind=_engine)


@contextmanager
def get_session() -> Session:
    """Get a database session with automatic cleanup."""
    if not _SessionLocal:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    session = _SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session_factory():
    """Get the session factory."""
    if not _SessionLocal:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _SessionLocal


# Utility functions for common database operations

def create_or_update_repository(
    name: str,
    github_url: Optional[str] = None,
    gitea_url: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> SyncRepository:
    """Create or update a repository record."""
    with get_session() as session:
        repo = session.query(SyncRepository).filter_by(name=name).first()
        
        if repo:
            # Update existing repository
            if github_url:
                repo.github_url = github_url
            if gitea_url:
                repo.gitea_url = gitea_url
            if config:
                repo.config = config
            repo.updated_at = datetime.now(timezone.utc)
        else:
            # Create new repository
            repo = SyncRepository(
                name=name,
                github_url=github_url,
                gitea_url=gitea_url,
                config=config or {},
                created_at=datetime.now(timezone.utc)
            )
            session.add(repo)
        
        session.commit()
        session.refresh(repo)
        return repo


def log_sync_event(
    repository_name: str,
    status: str,
    details: Optional[Dict[str, Any]] = None,
    source: Optional[str] = None,
    duration_seconds: Optional[int] = None,
    error_message: Optional[str] = None
) -> SyncLog:
    """Log a synchronization event."""
    with get_session() as session:
        log_entry = SyncLog(
            repository_name=repository_name,
            sync_status=status,
            details=details or {},
            source=source,
            duration_seconds=duration_seconds,
            error_message=error_message,
            timestamp=datetime.now(timezone.utc)
        )
        session.add(log_entry)
        session.commit()
        session.refresh(log_entry)
        return log_entry


def create_conflict_record(
    repository_name: str,
    conflict_type: str,
    branch_name: Optional[str] = None,
    github_commit: Optional[str] = None,
    gitea_commit: Optional[str] = None,
    conflict_details: Optional[Dict[str, Any]] = None
) -> SyncConflict:
    """Create a conflict record."""
    with get_session() as session:
        conflict = SyncConflict(
            repository_name=repository_name,
            conflict_type=conflict_type,
            branch_name=branch_name,
            github_commit=github_commit,
            gitea_commit=gitea_commit,
            conflict_details=conflict_details or {},
            created_at=datetime.now(timezone.utc)
        )
        session.add(conflict)
        session.commit()
        session.refresh(conflict)
        return conflict


def log_webhook_event(
    source: str,
    event_type: str,
    repository_name: str,
    payload: Dict[str, Any],
    event_id: Optional[str] = None
) -> WebhookEvent:
    """Log a webhook event."""
    with get_session() as session:
        webhook_event = WebhookEvent(
            source=source,
            event_type=event_type,
            repository_name=repository_name,
            event_id=event_id,
            payload=payload,
            created_at=datetime.now(timezone.utc)
        )
        session.add(webhook_event)
        session.commit()
        session.refresh(webhook_event)
        return webhook_event


def get_repositories_by_status(status: str) -> list[SyncRepository]:
    """Get repositories by sync status."""
    with get_session() as session:
        return session.query(SyncRepository).filter_by(sync_status=status).all()


def get_unresolved_conflicts() -> list[SyncConflict]:
    """Get all unresolved conflicts."""
    with get_session() as session:
        return session.query(SyncConflict).filter_by(resolved=False).all()


def get_recent_logs(limit: int = 100, repository_name: Optional[str] = None) -> list[SyncLog]:
    """Get recent sync logs."""
    with get_session() as session:
        query = session.query(SyncLog)
        
        if repository_name:
            query = query.filter_by(repository_name=repository_name)
        
        return query.order_by(SyncLog.timestamp.desc()).limit(limit).all()


def cleanup_old_logs(days: int = 30) -> int:
    """Clean up old log entries."""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    with get_session() as session:
        deleted_count = session.query(SyncLog).filter(
            SyncLog.timestamp < cutoff_date
        ).delete()
        
        # Also clean up old webhook events
        deleted_count += session.query(WebhookEvent).filter(
            WebhookEvent.created_at < cutoff_date
        ).delete()
        
        session.commit()
        return deleted_count