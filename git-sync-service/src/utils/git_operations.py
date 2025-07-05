#!/usr/bin/env python3
"""
Git operations utilities for repository synchronization.
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import structlog
from git import Repo, GitCommandError, Remote

from config.settings import Settings


class GitOperations:
    """Utilities for Git operations."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = structlog.get_logger()
    
    def clone_repository(self, repo_url: str, target_dir: Path, auth_token: Optional[str] = None) -> Repo:
        """Clone a repository with authentication if needed."""
        if auth_token and "github.com" in repo_url:
            # Inject token into GitHub URL
            auth_url = repo_url.replace("https://github.com/", f"https://{auth_token}@github.com/")
        elif auth_token and self.settings.gitea_url in repo_url:
            # For Gitea, we might need different auth handling
            auth_url = repo_url  # Gitea auth handling would go here
        else:
            auth_url = repo_url
        
        try:
            self.logger.info("Cloning repository", url=repo_url, target=str(target_dir))
            return Repo.clone_from(auth_url, target_dir, env={"GIT_TERMINAL_PROMPT": "0"})
        except GitCommandError as e:
            self.logger.error("Failed to clone repository", url=repo_url, error=str(e))
            raise
    
    def add_remote(self, repo: Repo, name: str, url: str, auth_token: Optional[str] = None) -> Remote:
        """Add a remote to the repository."""
        if auth_token and "github.com" in url:
            auth_url = url.replace("https://github.com/", f"https://{auth_token}@github.com/")
        else:
            auth_url = url
        
        try:
            self.logger.info("Adding remote", name=name, url=url)
            return repo.create_remote(name, auth_url)
        except GitCommandError as e:
            self.logger.error("Failed to add remote", name=name, url=url, error=str(e))
            raise
    
    def fetch_all_remotes(self, repo: Repo) -> None:
        """Fetch from all remotes."""
        for remote in repo.remotes:
            try:
                self.logger.info("Fetching from remote", remote=remote.name)
                remote.fetch()
            except GitCommandError as e:
                self.logger.warning("Failed to fetch from remote", remote=remote.name, error=str(e))
                # Continue with other remotes even if one fails
    
    def get_branch_differences(self, repo: Repo, branch1: str, branch2: str) -> Dict[str, List[str]]:
        """Get differences between two branches."""
        try:
            # Get commits that are in branch1 but not in branch2
            ahead_commits = list(repo.iter_commits(f"{branch2}..{branch1}"))
            
            # Get commits that are in branch2 but not in branch1
            behind_commits = list(repo.iter_commits(f"{branch1}..{branch2}"))
            
            return {
                "ahead": [commit.hexsha for commit in ahead_commits],
                "behind": [commit.hexsha for commit in behind_commits],
                "diverged": len(ahead_commits) > 0 and len(behind_commits) > 0
            }
        except GitCommandError as e:
            self.logger.error("Failed to get branch differences", branch1=branch1, branch2=branch2, error=str(e))
            raise
    
    def list_branches(self, repo: Repo, remote: Optional[str] = None) -> List[str]:
        """List branches in the repository."""
        branches = []
        
        if remote:
            # List remote branches
            remote_obj = repo.remotes[remote]
            for ref in remote_obj.refs:
                branch_name = ref.name.replace(f"{remote}/", "")
                if branch_name != "HEAD":
                    branches.append(branch_name)
        else:
            # List local branches
            for branch in repo.branches:
                branches.append(branch.name)
        
        return branches
    
    def list_tags(self, repo: Repo) -> List[str]:
        """List tags in the repository."""
        return [tag.name for tag in repo.tags]
    
    def push_branch(self, repo: Repo, remote_name: str, local_branch: str, remote_branch: str = None, force: bool = False) -> None:
        """Push a branch to a remote."""
        if remote_branch is None:
            remote_branch = local_branch
        
        try:
            remote = repo.remotes[remote_name]
            refspec = f"{local_branch}:{remote_branch}"
            
            self.logger.info("Pushing branch", remote=remote_name, refspec=refspec, force=force)
            
            if force:
                remote.push(refspec=refspec, force=True)
            else:
                remote.push(refspec=refspec)
                
        except GitCommandError as e:
            self.logger.error("Failed to push branch", remote=remote_name, refspec=refspec, error=str(e))
            raise
    
    def push_tags(self, repo: Repo, remote_name: str, force: bool = False) -> None:
        """Push tags to a remote."""
        try:
            remote = repo.remotes[remote_name]
            self.logger.info("Pushing tags", remote=remote_name, force=force)
            
            if force:
                remote.push(tags=True, force=True)
            else:
                remote.push(tags=True)
                
        except GitCommandError as e:
            self.logger.error("Failed to push tags", remote=remote_name, error=str(e))
            raise
    
    def create_branch(self, repo: Repo, branch_name: str, start_point: str = None) -> None:
        """Create a new branch."""
        try:
            self.logger.info("Creating branch", branch=branch_name, start_point=start_point)
            
            if start_point:
                repo.create_head(branch_name, start_point)
            else:
                repo.create_head(branch_name)
                
        except GitCommandError as e:
            self.logger.error("Failed to create branch", branch=branch_name, error=str(e))
            raise
    
    def checkout_branch(self, repo: Repo, branch_name: str, create: bool = False) -> None:
        """Checkout a branch."""
        try:
            self.logger.info("Checking out branch", branch=branch_name, create=create)
            
            if create:
                # Create and checkout new branch
                new_branch = repo.create_head(branch_name)
                new_branch.checkout()
            else:
                # Checkout existing branch
                repo.heads[branch_name].checkout()
                
        except GitCommandError as e:
            self.logger.error("Failed to checkout branch", branch=branch_name, error=str(e))
            raise
    
    def merge_branch(self, repo: Repo, source_branch: str, target_branch: str = None) -> bool:
        """Merge one branch into another."""
        try:
            if target_branch:
                self.checkout_branch(repo, target_branch)
            
            self.logger.info("Merging branch", source=source_branch, target=target_branch or "current")
            
            # Perform the merge
            merge_base = repo.merge_base(repo.active_branch, repo.heads[source_branch])
            repo.index.merge_tree(repo.heads[source_branch], base=merge_base[0] if merge_base else None)
            
            # Check if there are conflicts
            if repo.index.unmerged_blobs():
                self.logger.warning("Merge conflicts detected", source=source_branch, target=target_branch)
                return False
            
            # Commit the merge
            repo.index.commit(f"Merge branch '{source_branch}'")
            return True
            
        except GitCommandError as e:
            self.logger.error("Failed to merge branch", source=source_branch, target=target_branch, error=str(e))
            raise
    
    def is_clean_working_directory(self, repo: Repo) -> bool:
        """Check if the working directory is clean."""
        return not repo.is_dirty(untracked_files=True)
    
    def get_commit_info(self, repo: Repo, commit_sha: str) -> Dict[str, str]:
        """Get information about a commit."""
        try:
            commit = repo.commit(commit_sha)
            return {
                "sha": commit.hexsha,
                "message": commit.message.strip(),
                "author": f"{commit.author.name} <{commit.author.email}>",
                "date": commit.committed_datetime.isoformat()
            }
        except GitCommandError as e:
            self.logger.error("Failed to get commit info", sha=commit_sha, error=str(e))
            raise
    
    def reset_to_commit(self, repo: Repo, commit_sha: str, hard: bool = False) -> None:
        """Reset repository to a specific commit."""
        try:
            self.logger.info("Resetting to commit", sha=commit_sha, hard=hard)
            
            if hard:
                repo.head.reset(commit_sha, index=True, working_tree=True)
            else:
                repo.head.reset(commit_sha, index=True, working_tree=False)
                
        except GitCommandError as e:
            self.logger.error("Failed to reset to commit", sha=commit_sha, error=str(e))
            raise