"""Tests for database functionality."""

import pytest
import tempfile
import sqlite3
import os
from pathlib import Path

from org_roam_mcp.database import OrgRoamDatabase, OrgRoamNode, OrgRoamLink


@pytest.fixture
def mock_db_path():
    """Create a temporary database with org-roam schema."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    # Create a minimal org-roam schema
    conn = sqlite3.connect(db_path)

    # Create tables
    conn.execute("""
        CREATE TABLE files (
            file TEXT PRIMARY KEY,
            title TEXT,
            hash TEXT NOT NULL,
            atime INTEGER NOT NULL,
            mtime INTEGER NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE nodes (
            id TEXT PRIMARY KEY,
            file TEXT NOT NULL,
            level INTEGER NOT NULL,
            pos INTEGER NOT NULL,
            todo TEXT,
            priority TEXT,
            scheduled TEXT,
            deadline TEXT,
            title TEXT,
            properties TEXT,
            olp TEXT,
            FOREIGN KEY (file) REFERENCES files (file) ON DELETE CASCADE
        )
    """)

    conn.execute("""
        CREATE TABLE links (
            pos INTEGER NOT NULL,
            source TEXT NOT NULL,
            dest TEXT NOT NULL,
            type TEXT NOT NULL,
            properties TEXT NOT NULL,
            FOREIGN KEY (source) REFERENCES nodes (id) ON DELETE CASCADE
        )
    """)

    conn.execute("""
        CREATE TABLE tags (
            node_id TEXT NOT NULL,
            tag TEXT,
            FOREIGN KEY (node_id) REFERENCES nodes (id) ON DELETE CASCADE
        )
    """)

    conn.execute("""
        CREATE TABLE aliases (
            node_id TEXT NOT NULL,
            alias TEXT,
            FOREIGN KEY (node_id) REFERENCES nodes (id) ON DELETE CASCADE
        )
    """)

    # Insert test data
    test_file = "/tmp/test.org"
    conn.execute(
        "INSERT INTO files (file, title, hash, atime, mtime) VALUES (?, ?, ?, ?, ?)",
        (test_file, "Test File", "abc123", 1234567890, 1234567890),
    )

    test_node_id = '"test-node-id-1"'
    conn.execute(
        """INSERT INTO nodes (id, file, level, pos, todo, priority, scheduled, deadline, title, properties, olp) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (test_node_id, test_file, 0, 0, None, None, None, None, "Test Node", None, None),
    )

    conn.execute("INSERT INTO tags (node_id, tag) VALUES (?, ?)", (test_node_id, "test-tag"))

    conn.execute("INSERT INTO aliases (node_id, alias) VALUES (?, ?)", (test_node_id, "test-alias"))

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    os.unlink(db_path)


def test_database_connection(mock_db_path):
    """Test database connection."""
    db = OrgRoamDatabase(mock_db_path)
    assert db.conn is not None

    stats = db.get_database_stats()
    assert stats["nodes"] == 1
    assert stats["files"] == 1

    db.close()


def test_get_all_nodes(mock_db_path):
    """Test getting all nodes."""
    db = OrgRoamDatabase(mock_db_path)

    nodes = db.get_all_nodes()
    assert len(nodes) == 1

    node = nodes[0]
    assert node.id == "test-node-id-1"
    assert node.title == "Test Node"
    assert node.file == "/tmp/test.org"

    db.close()


def test_get_node_by_id(mock_db_path):
    """Test getting node by ID."""
    db = OrgRoamDatabase(mock_db_path)

    node = db.get_node_by_id("test-node-id-1")
    assert node is not None
    assert node.title == "Test Node"

    # Test non-existent node
    node = db.get_node_by_id("non-existent")
    assert node is None

    db.close()


def test_search_nodes(mock_db_path):
    """Test node search functionality."""
    db = OrgRoamDatabase(mock_db_path)

    # Search by title
    results = db.search_nodes("Test")
    assert len(results) == 1
    assert results[0].title == "Test Node"

    # Search by tag
    results = db.search_nodes("test-tag")
    assert len(results) == 1

    # Search by alias
    results = db.search_nodes("test-alias")
    assert len(results) == 1

    # Search with no results
    results = db.search_nodes("nonexistent")
    assert len(results) == 0

    db.close()


def test_get_node_tags_and_aliases(mock_db_path):
    """Test getting node tags and aliases."""
    db = OrgRoamDatabase(mock_db_path)

    tags = db.get_node_tags("test-node-id-1")
    assert "test-tag" in tags

    aliases = db.get_node_aliases("test-node-id-1")
    assert "test-alias" in aliases

    db.close()


def test_auto_detect_database():
    """Test auto-detection of database fails gracefully."""
    # This should raise FileNotFoundError since no standard paths exist
    with pytest.raises(FileNotFoundError):
        OrgRoamDatabase()
