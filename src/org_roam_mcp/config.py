"""Configuration management for org-roam MCP server."""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class OrgRoamConfig:
    """Configuration for org-roam MCP server."""
    
    db_path: str
    org_roam_directory: str
    max_search_results: int = 50
    default_file_extension: str = "org"
    
    @classmethod
    def from_environment(cls) -> "OrgRoamConfig":
        """Create configuration from environment variables."""
        
        # Database path
        db_path = os.environ.get("ORG_ROAM_DB_PATH")
        if not db_path:
            db_path = cls._find_database()
        
        # Org-roam directory
        org_roam_dir = os.environ.get("ORG_ROAM_DIR")
        if not org_roam_dir:
            org_roam_dir = cls._find_org_roam_directory(db_path)
        
        # Optional settings
        max_results = int(os.environ.get("ORG_ROAM_MAX_SEARCH_RESULTS", "50"))
        
        return cls(
            db_path=db_path,
            org_roam_directory=org_roam_dir,
            max_search_results=max_results
        )
    
    @staticmethod
    def _find_database() -> str:
        """Find org-roam database file."""
        possible_paths = [
            os.path.expanduser("~/.emacs.d/org-roam.db"),
            os.path.expanduser("~/org-roam.db"), 
            os.path.expanduser("~/.config/emacs/org-roam.db"),
            os.path.expanduser("~/Documents/org-roam/org-roam.db"),
            os.path.expanduser("~/org-roam/org-roam.db"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found org-roam database: {path}")
                return path
        
        raise FileNotFoundError(
            "Could not find org-roam database. Set ORG_ROAM_DB_PATH environment variable."
        )
    
    @staticmethod
    def _find_org_roam_directory(db_path: str) -> str:
        """Find org-roam directory based on database location or common locations."""
        # Try to infer from database path
        db_dir = os.path.dirname(db_path)
        
        # Common patterns
        possible_dirs = [
            os.path.join(db_dir, "org-roam"),
            os.path.expanduser("~/org-roam"),
            os.path.expanduser("~/Documents/org-roam"),
            os.path.expanduser("~/Dropbox/org-roam"),
            os.path.expanduser("~/iCloud/org-roam"),
            os.path.expanduser("~/Notes"),
            os.path.expanduser("~/notes"),
        ]
        
        for directory in possible_dirs:
            if os.path.isdir(directory) and OrgRoamConfig._has_org_files(directory):
                logger.info(f"Found org-roam directory: {directory}")
                return directory
        
        # Default to first existing directory, or create default
        default_dir = os.path.expanduser("~/org-roam")
        if not os.path.exists(default_dir):
            logger.warning(f"Creating default org-roam directory: {default_dir}")
            os.makedirs(default_dir, exist_ok=True)
        
        return default_dir
    
    @staticmethod
    def _has_org_files(directory: str) -> bool:
        """Check if directory contains .org files."""
        try:
            org_files = list(Path(directory).glob("*.org"))
            return len(org_files) > 0
        except (OSError, PermissionError):
            return False
    
    def validate(self):
        """Validate configuration."""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        
        if not os.path.exists(self.org_roam_directory):
            raise FileNotFoundError(f"Org-roam directory not found: {self.org_roam_directory}")
        
        if not os.access(self.org_roam_directory, os.W_OK):
            raise PermissionError(f"No write access to org-roam directory: {self.org_roam_directory}")
        
        logger.info(f"Configuration valid - DB: {self.db_path}, Dir: {self.org_roam_directory}")