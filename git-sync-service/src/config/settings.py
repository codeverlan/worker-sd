"""Configuration settings for Git Sync Service."""

import os
from typing import Optional, Literal
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # GitHub Configuration
    github_token: str = Field(..., env="GITHUB_TOKEN")
    github_user: str = Field(..., env="GITHUB_USER")
    github_api_url: str = Field("https://api.github.com", env="GITHUB_API_URL")
    
    # Gitea Configuration
    gitea_url: str = Field(..., env="GITEA_URL")
    gitea_token: str = Field(..., env="GITEA_TOKEN")
    gitea_user: str = Field(..., env="GITEA_USER")
    
    # Sync Configuration
    sync_interval: int = Field(300, env="SYNC_INTERVAL")  # seconds
    conflict_resolution: Literal["github_wins", "gitea_wins", "manual"] = Field(
        "manual", env="CONFLICT_RESOLUTION"
    )
    dry_run: bool = Field(False, env="DRY_RUN")
    max_retries: int = Field(3, env="MAX_RETRIES")
    retry_delay: int = Field(30, env="RETRY_DELAY")  # seconds
    
    # Webhook Configuration
    webhook_secret: Optional[str] = Field(None, env="WEBHOOK_SECRET")
    webhook_timeout: int = Field(30, env="WEBHOOK_TIMEOUT")
    
    # Database Configuration
    database_url: str = Field("sqlite:///data/sync.db", env="DATABASE_URL")
    
    # Redis Configuration
    redis_url: str = Field("redis://redis:6379/0", env="REDIS_URL")
    
    # Logging Configuration
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_format: str = Field("json", env="LOG_FORMAT")
    
    # Sync Behavior
    sync_branches: bool = Field(True, env="SYNC_BRANCHES")
    sync_tags: bool = Field(True, env="SYNC_TAGS")
    sync_releases: bool = Field(True, env="SYNC_RELEASES")
    sync_issues: bool = Field(False, env="SYNC_ISSUES")  # Complex, disabled by default
    sync_prs: bool = Field(False, env="SYNC_PRS")  # Complex, disabled by default
    
    # Repository Filtering
    include_repos: Optional[str] = Field(None, env="INCLUDE_REPOS")  # Comma-separated
    exclude_repos: Optional[str] = Field(None, env="EXCLUDE_REPOS")  # Comma-separated
    
    # Performance
    max_concurrent_syncs: int = Field(5, env="MAX_CONCURRENT_SYNCS")
    git_timeout: int = Field(300, env="GIT_TIMEOUT")  # seconds
    
    # Monitoring
    metrics_enabled: bool = Field(True, env="METRICS_ENABLED")
    health_check_interval: int = Field(60, env="HEALTH_CHECK_INTERVAL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    @property
    def included_repositories(self) -> Optional[list]:
        """Get list of included repositories."""
        if self.include_repos:
            return [repo.strip() for repo in self.include_repos.split(",")]
        return None
    
    @property
    def excluded_repositories(self) -> Optional[list]:
        """Get list of excluded repositories."""
        if self.exclude_repos:
            return [repo.strip() for repo in self.exclude_repos.split(",")]
        return None