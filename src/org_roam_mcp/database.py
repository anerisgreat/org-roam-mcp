"""Database interface for org-roam SQLite database."""

import sqlite3
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class OrgRoamNode:
    """Represents an org-roam node."""
    id: str
    file: str
    level: int
    pos: int
    todo: Optional[str]
    priority: Optional[str]
    scheduled: Optional[str]
    deadline: Optional[str]
    title: Optional[str]
    properties: Optional[str]
    olp: Optional[str]


@dataclass
class OrgRoamLink:
    """Represents a link between org-roam nodes."""
    pos: int
    source: str
    dest: str
    type: str
    properties: str


@dataclass
class OrgRoamFile:
    """Represents an org-roam file."""
    file: str
    title: Optional[str]
    hash: str
    atime: int
    mtime: int


class OrgRoamDatabase:
    """Interface to org-roam SQLite database."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database connection.
        
        Args:
            db_path: Path to org-roam.db file. If None, auto-detect.
        """
        self.db_path = db_path or self._find_database()
        self.conn = None
        self._connect()
    
    def _find_database(self) -> str:
        """Auto-detect org-roam database location."""
        possible_paths = [
            os.path.expanduser("~/.emacs.d/org-roam.db"),
            os.path.expanduser("~/org-roam.db"),
            os.path.expanduser("~/.config/emacs/org-roam.db"),
            os.path.expanduser("~/Documents/org-roam/org-roam.db"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found org-roam database at: {path}")
                return path
        
        raise FileNotFoundError("Could not find org-roam database. Please specify ORG_ROAM_DB_PATH.")
    
    def _connect(self):
        """Establish database connection."""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Org-roam database not found at: {self.db_path}")
        
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        logger.info(f"Connected to org-roam database: {self.db_path}")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def _clean_path(self, path: Optional[str]) -> Optional[str]:
        """Clean file path by removing quotes if present.
        
        Args:
            path: File path that may have quotes
            
        Returns:
            Clean file path without quotes
        """
        if not path:
            return path
        return path.strip('"')
    
    def _clean_string(self, value: Optional[str]) -> Optional[str]:
        """Clean string value by removing quotes if present.
        
        Args:
            value: String value that may have quotes
            
        Returns:
            Clean string without quotes
        """
        if not value:
            return value
        return value.strip('"')
    
    def get_all_nodes(self, limit: Optional[int] = None) -> List[OrgRoamNode]:
        """Get all nodes from the database.
        
        Args:
            limit: Maximum number of nodes to return
            
        Returns:
            List of OrgRoamNode objects
        """
        query = """
        SELECT id, file, level, pos, todo, priority, scheduled, deadline, 
               title, properties, olp 
        FROM nodes
        ORDER BY title
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor = self.conn.execute(query)
        rows = cursor.fetchall()
        
        return [
            OrgRoamNode(
                id=self._clean_string(row['id']),
                file=self._clean_path(row['file']),
                level=row['level'],
                pos=row['pos'],
                todo=row['todo'],
                priority=row['priority'],
                scheduled=row['scheduled'],
                deadline=row['deadline'],
                title=self._clean_string(row['title']),
                properties=row['properties'],
                olp=row['olp']
            )
            for row in rows
        ]
    
    def get_node_by_id(self, node_id: str) -> Optional[OrgRoamNode]:
        """Get a specific node by ID.
        
        Args:
            node_id: The node ID to search for (with or without quotes)
            
        Returns:
            OrgRoamNode if found, None otherwise
        """
        # Normalize input ID - add quotes if not present, as DB stores quoted IDs
        search_id = node_id if node_id.startswith('"') and node_id.endswith('"') else f'"{node_id}"'
        
        query = """
        SELECT id, file, level, pos, todo, priority, scheduled, deadline,
               title, properties, olp
        FROM nodes 
        WHERE id = ?
        """
        
        cursor = self.conn.execute(query, (search_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return OrgRoamNode(
            id=self._clean_string(row['id']),
            file=self._clean_path(row['file']),
            level=row['level'],
            pos=row['pos'],
            todo=row['todo'],
            priority=row['priority'],
            scheduled=row['scheduled'],
            deadline=row['deadline'],
            title=self._clean_string(row['title']),
            properties=row['properties'],
            olp=row['olp']
        )
    
    def search_nodes(self, query: str, limit: Optional[int] = None) -> List[OrgRoamNode]:
        """Search nodes by title, aliases, or tags.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            
        Returns:
            List of matching OrgRoamNode objects
        """
        sql_query = """
        SELECT DISTINCT n.id, n.file, n.level, n.pos, n.todo, n.priority, 
               n.scheduled, n.deadline, n.title, n.properties, n.olp
        FROM nodes n
        LEFT JOIN aliases a ON n.id = a.node_id
        LEFT JOIN tags t ON n.id = t.node_id
        WHERE n.title LIKE ? 
           OR a.alias LIKE ?
           OR t.tag LIKE ?
        ORDER BY n.title
        """
        
        if limit:
            sql_query += f" LIMIT {limit}"
        
        search_pattern = f"%{query}%"
        cursor = self.conn.execute(sql_query, (search_pattern, search_pattern, search_pattern))
        rows = cursor.fetchall()
        
        return [
            OrgRoamNode(
                id=self._clean_string(row['id']),
                file=self._clean_path(row['file']),
                level=row['level'],
                pos=row['pos'],
                todo=row['todo'],
                priority=row['priority'],
                scheduled=row['scheduled'],
                deadline=row['deadline'],
                title=self._clean_string(row['title']),
                properties=row['properties'],
                olp=row['olp']
            )
            for row in rows
        ]
    
    def get_backlinks(self, node_id: str) -> List[OrgRoamLink]:
        """Get all links pointing to a specific node.
        
        Args:
            node_id: The target node ID (with or without quotes)
            
        Returns:
            List of OrgRoamLink objects
        """
        # Normalize input ID - add quotes if not present, as DB stores quoted IDs
        search_id = node_id if node_id.startswith('"') and node_id.endswith('"') else f'"{node_id}"'
        
        query = """
        SELECT pos, source, dest, type, properties
        FROM links
        WHERE dest = ?
        """
        
        cursor = self.conn.execute(query, (search_id,))
        rows = cursor.fetchall()
        
        return [
            OrgRoamLink(
                pos=row['pos'],
                source=row['source'],
                dest=row['dest'],
                type=row['type'],
                properties=row['properties']
            )
            for row in rows
        ]
    
    def get_forward_links(self, node_id: str) -> List[OrgRoamLink]:
        """Get all links from a specific node.
        
        Args:
            node_id: The source node ID (with or without quotes)
            
        Returns:
            List of OrgRoamLink objects
        """
        # Normalize input ID - add quotes if not present, as DB stores quoted IDs
        search_id = node_id if node_id.startswith('"') and node_id.endswith('"') else f'"{node_id}"'
        
        query = """
        SELECT pos, source, dest, type, properties
        FROM links
        WHERE source = ?
        """
        
        cursor = self.conn.execute(query, (search_id,))
        rows = cursor.fetchall()
        
        return [
            OrgRoamLink(
                pos=row['pos'],
                source=row['source'],
                dest=row['dest'],
                type=row['type'],
                properties=row['properties']
            )
            for row in rows
        ]
    
    def get_node_tags(self, node_id: str) -> List[str]:
        """Get tags for a specific node.
        
        Args:
            node_id: The node ID (with or without quotes)
            
        Returns:
            List of tag strings
        """
        # Normalize input ID - add quotes if not present, as DB stores quoted IDs
        search_id = node_id if node_id.startswith('"') and node_id.endswith('"') else f'"{node_id}"'
        query = "SELECT tag FROM tags WHERE node_id = ?"
        cursor = self.conn.execute(query, (search_id,))
        return [row['tag'] for row in cursor.fetchall()]
    
    def get_node_aliases(self, node_id: str) -> List[str]:
        """Get aliases for a specific node.
        
        Args:
            node_id: The node ID (with or without quotes)
            
        Returns:
            List of alias strings
        """
        # Normalize input ID - add quotes if not present, as DB stores quoted IDs
        search_id = node_id if node_id.startswith('"') and node_id.endswith('"') else f'"{node_id}"'
        query = "SELECT alias FROM aliases WHERE node_id = ?"
        cursor = self.conn.execute(query, (search_id,))
        return [row['alias'] for row in cursor.fetchall()]
    
    def get_all_files(self) -> List[OrgRoamFile]:
        """Get all files from the database.
        
        Returns:
            List of OrgRoamFile objects
        """
        query = "SELECT file, title, hash, atime, mtime FROM files ORDER BY file"
        cursor = self.conn.execute(query)
        rows = cursor.fetchall()
        
        return [
            OrgRoamFile(
                file=row['file'],
                title=row['title'],
                hash=row['hash'],
                atime=row['atime'],
                mtime=row['mtime']
            )
            for row in rows
        ]
    
    def get_database_stats(self) -> Dict[str, int]:
        """Get database statistics.
        
        Returns:
            Dictionary with counts for various entities
        """
        stats = {}
        
        # Count nodes
        cursor = self.conn.execute("SELECT COUNT(*) as count FROM nodes")
        stats['nodes'] = cursor.fetchone()['count']
        
        # Count files  
        cursor = self.conn.execute("SELECT COUNT(*) as count FROM files")
        stats['files'] = cursor.fetchone()['count']
        
        # Count links
        cursor = self.conn.execute("SELECT COUNT(*) as count FROM links")
        stats['links'] = cursor.fetchone()['count']
        
        # Count tags
        cursor = self.conn.execute("SELECT COUNT(DISTINCT tag) as count FROM tags")
        stats['unique_tags'] = cursor.fetchone()['count']
        
        # Count aliases
        cursor = self.conn.execute("SELECT COUNT(*) as count FROM aliases")
        stats['aliases'] = cursor.fetchone()['count']
        
        return stats
    
    def refresh_connection(self):
        """Refresh the database connection to pick up external changes.
        
        This is useful when the org-roam database is modified externally
        (e.g., by Emacs) and we need to see the latest changes.
        """
        if self.conn:
            self.conn.close()
        self._connect()
        logger.info("Database connection refreshed")