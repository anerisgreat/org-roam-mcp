"""Tests for file manager functionality."""

import pytest
import tempfile
import os
from pathlib import Path

from org_roam_mcp.config import OrgRoamConfig
from org_roam_mcp.file_manager import OrgRoamFileManager
from org_roam_mcp.database import OrgRoamNode


@pytest.fixture
def temp_org_dir():
    """Create a temporary org-roam directory."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


@pytest.fixture
def config(temp_org_dir):
    """Create test configuration."""
    # Create a dummy database file
    db_path = os.path.join(temp_org_dir, "org-roam.db")
    Path(db_path).touch()

    return OrgRoamConfig(db_path=db_path, org_roam_directory=temp_org_dir, max_search_results=50)


@pytest.fixture
def file_manager(config):
    """Create file manager instance."""
    return OrgRoamFileManager(config)


def test_title_to_filename(file_manager):
    """Test title to filename conversion."""
    assert file_manager._title_to_filename("Simple Title") == "simple-title"
    assert file_manager._title_to_filename("Title with Symbols! @#$") == "title-with-symbols"
    assert file_manager._title_to_filename("Multiple   Spaces") == "multiple-spaces"
    assert file_manager._title_to_filename("") != ""  # Should generate timestamp


def test_create_org_content(file_manager):
    """Test org content creation."""
    node_id = "test-id-123"
    title = "Test Title"
    content = "This is test content"
    tags = ["tag1", "tag2"]

    org_content = file_manager._create_org_content(node_id, title, content, tags)

    assert ":PROPERTIES:" in org_content
    assert f":ID: {node_id}" in org_content
    assert f"#+title: {title}" in org_content
    assert "#+filetags: :tag1: :tag2:" in org_content
    assert content in org_content


def test_create_node(file_manager):
    """Test node creation."""
    title = "Test Node"
    content = "Test content here"
    tags = ["test", "node"]

    node_id = file_manager.create_node(title, content, tags)

    # Verify UUID format
    assert len(node_id) == 36
    assert node_id.count("-") == 4

    # Check file was created
    org_files = file_manager.list_org_files()
    assert len(org_files) == 1

    # Check content
    created_file = org_files[0]
    content_read = file_manager.read_file_content(created_file)
    assert title in content_read
    assert content in content_read
    assert node_id in content_read


def test_read_file_content(file_manager):
    """Test file content reading."""
    # Create a test file
    test_file = Path(file_manager.config.org_roam_directory) / "test.org"
    test_content = ":PROPERTIES:\n:ID: test-123\n:END:\n#+title: Test\n\nContent here"

    with open(test_file, "w") as f:
        f.write(test_content)

    # Test reading
    content = file_manager.read_file_content("test.org")
    assert content == test_content

    # Test reading non-existent file
    content = file_manager.read_file_content("nonexistent.org")
    assert content == ""


def test_get_file_metadata(file_manager):
    """Test extracting metadata from org files."""
    # Create test file with metadata
    test_file = Path(file_manager.config.org_roam_directory) / "metadata_test.org"
    content = """:PROPERTIES:
:ID: test-id-456
:CREATED: 2024-01-01
:END:
#+title: Metadata Test
#+filetags: :meta::test:

Some content here"""

    with open(test_file, "w") as f:
        f.write(content)

    metadata = file_manager.get_file_metadata("metadata_test.org")

    assert metadata["ID"] == "test-id-456"
    assert metadata["title"] == "Metadata Test"
    assert "meta" in metadata["tags"]
    assert "test" in metadata["tags"]
    assert metadata["CREATED"] == "2024-01-01"


def test_list_org_files(file_manager):
    """Test listing org files."""
    # Create some test files
    test_files = ["note1.org", "note2.org", "subdir/note3.org"]

    for file_path in test_files:
        full_path = Path(file_manager.config.org_roam_directory) / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text("#+title: Test")

    # Also create a non-org file
    (Path(file_manager.config.org_roam_directory) / "not_org.txt").write_text("not org")

    org_files = file_manager.list_org_files()

    assert len(org_files) == 3
    assert "note1.org" in org_files
    assert "note2.org" in org_files
    assert "subdir/note3.org" in org_files
    assert "not_org.txt" not in org_files


def test_read_node_content(file_manager):
    """Test reading content for specific nodes."""
    # Create test file
    test_file = Path(file_manager.config.org_roam_directory) / "node_test.org"
    content = """:PROPERTIES:
:ID: file-level-id
:END:
#+title: File Level Node

File level content here."""

    with open(test_file, "w") as f:
        f.write(content)

    # Test file-level node
    node = OrgRoamNode(
        id="file-level-id",
        file="node_test.org",
        level=0,
        pos=0,
        todo=None,
        priority=None,
        scheduled=None,
        deadline=None,
        title="File Level Node",
        properties=None,
        olp=None,
    )

    node_content = file_manager.read_node_content(node)
    assert "File Level Node" in node_content
    assert "File level content" in node_content


def test_update_file_content(file_manager):
    """Test updating file content."""
    # Create test file
    test_file = Path(file_manager.config.org_roam_directory) / "update_test.org"
    original_content = ":PROPERTIES:\n:ID: update-test\n:END\n#+title: Original"

    with open(test_file, "w") as f:
        f.write(original_content)

    # Update content
    new_content = ":PROPERTIES:\n:ID: update-test\n:END:\n#+title: Updated\n\nNew content!"
    file_manager._update_file_content("update_test.org", new_content)

    # Verify update
    updated_content = file_manager.read_file_content("update_test.org")
    assert "Updated" in updated_content
    assert "New content!" in updated_content
