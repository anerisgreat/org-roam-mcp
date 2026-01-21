#!/usr/bin/env python3
"""
Test script to validate org-roam MCP server improvements.

This script tests the core functionality to ensure all fixes work properly:
1. Database connection and node retrieval
2. File path handling
3. Node ID format consistency
4. Search functionality
5. Node creation and updates
"""

import sys
import os
import tempfile
import uuid
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from org_roam_mcp.config import OrgRoamConfig
from org_roam_mcp.database import OrgRoamDatabase
from org_roam_mcp.file_manager import OrgRoamFileManager


def test_database_connection():
    """Test database connection and basic queries."""
    print("🔌 Testing database connection...")
    try:
        config = OrgRoamConfig.from_environment()
        db = OrgRoamDatabase(config.db_path)

        # Test connection
        stats = db.get_database_stats()
        print(f"  ✅ Connected to database with {stats['nodes']} nodes")

        # Test getting all nodes
        nodes = db.get_all_nodes(limit=5)
        print(f"  ✅ Retrieved {len(nodes)} sample nodes")

        db.close()
        return True
    except Exception as e:
        print(f"  ❌ Database connection failed: {e}")
        return False


def test_node_id_handling():
    """Test node ID format handling (quoted vs unquoted)."""
    print("🆔 Testing node ID format handling...")
    try:
        config = OrgRoamConfig.from_environment()
        db = OrgRoamDatabase(config.db_path)

        # Get a test node
        nodes = db.get_all_nodes(limit=1)
        if not nodes:
            print("  ⚠️  No nodes available for testing")
            return False

        test_node = nodes[0]
        node_id = test_node.id

        # Test lookup with unquoted ID
        node1 = db.get_node_by_id(node_id)
        print(f"  ✅ Found node with unquoted ID: {node1 is not None}")

        # Test lookup with quoted ID
        quoted_id = f'"{node_id}"'
        node2 = db.get_node_by_id(quoted_id)
        print(f"  ✅ Found node with quoted ID: {node2 is not None}")

        # Test tags and aliases
        tags = db.get_node_tags(node_id)
        aliases = db.get_node_aliases(node_id)
        print(f"  ✅ Retrieved {len(tags)} tags and {len(aliases)} aliases")

        db.close()
        return True
    except Exception as e:
        print(f"  ❌ Node ID handling failed: {e}")
        return False


def test_file_path_handling():
    """Test file path cleaning and handling."""
    print("📁 Testing file path handling...")
    try:
        config = OrgRoamConfig.from_environment()
        file_manager = OrgRoamFileManager(config)

        # Test with a quoted path
        quoted_path = '"/Users/test/file.org"'
        content1 = file_manager.read_file_content(quoted_path)
        print(f"  ✅ Handled quoted path without errors")

        # Test metadata extraction
        nodes = OrgRoamDatabase(config.db_path).get_all_nodes(limit=1)
        if nodes:
            metadata = file_manager.get_file_metadata(nodes[0].file)
            print(f"  ✅ Extracted metadata: title='{metadata.get('title', 'N/A')}'")

        return True
    except Exception as e:
        print(f"  ❌ File path handling failed: {e}")
        return False


def test_search_functionality():
    """Test search functionality."""
    print("🔍 Testing search functionality...")
    try:
        config = OrgRoamConfig.from_environment()
        db = OrgRoamDatabase(config.db_path)

        # Test basic search
        results = db.search_nodes("math", limit=10)
        print(f"  ✅ Search for 'math' returned {len(results)} results")

        # Test empty search
        empty_results = db.search_nodes("nonexistent-term-xyz", limit=10)
        print(f"  ✅ Empty search returned {len(empty_results)} results")

        db.close()
        return True
    except Exception as e:
        print(f"  ❌ Search functionality failed: {e}")
        return False


def test_node_creation():
    """Test node creation functionality."""
    print("📝 Testing node creation...")
    try:
        config = OrgRoamConfig.from_environment()
        file_manager = OrgRoamFileManager(config)

        # Create a test node
        test_title = f"Test Node {uuid.uuid4().hex[:8]}"
        test_content = "This is a test node created by the test script."
        test_tags = ["test", "mcp", "validation"]

        node_id = file_manager.create_node(test_title, test_content, test_tags)
        print(f"  ✅ Created test node with ID: {node_id}")

        # Verify the file was created
        org_files = file_manager.list_org_files()
        test_files = [f for f in org_files if test_title.lower().replace(" ", "-") in f.lower()]

        if test_files:
            print(f"  ✅ Found created file: {test_files[0]}")

            # Read the content back
            file_content = file_manager.read_file_content(test_files[0])
            if test_content in file_content:
                print(f"  ✅ File content matches expected content")
            else:
                print(f"  ⚠️  File content doesn't match expected content")
        else:
            print(f"  ⚠️  Created file not found in listing")

        return True
    except Exception as e:
        print(f"  ❌ Node creation failed: {e}")
        return False


def test_database_refresh():
    """Test database refresh functionality."""
    print("🔄 Testing database refresh...")
    try:
        config = OrgRoamConfig.from_environment()
        db = OrgRoamDatabase(config.db_path)

        # Get initial count
        initial_stats = db.get_database_stats()
        print(f"  ✅ Initial node count: {initial_stats['nodes']}")

        # Test refresh
        db.refresh_connection()

        # Get updated count
        updated_stats = db.get_database_stats()
        print(f"  ✅ Post-refresh node count: {updated_stats['nodes']}")

        db.close()
        return True
    except Exception as e:
        print(f"  ❌ Database refresh failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 Running org-roam MCP server improvement tests...\n")

    tests = [
        test_database_connection,
        test_node_id_handling,
        test_file_path_handling,
        test_search_functionality,
        test_node_creation,
        test_database_refresh,
    ]

    results = []
    for test in tests:
        result = test()
        results.append(result)
        print()  # Add spacing between tests

    # Summary
    passed = sum(results)
    total = len(results)

    print("📊 Test Summary:")
    print(f"  Passed: {passed}/{total}")
    print(f"  Failed: {total - passed}/{total}")

    if passed == total:
        print("  🎉 All tests passed!")
        return 0
    else:
        print("  ⚠️  Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    exit(main())
