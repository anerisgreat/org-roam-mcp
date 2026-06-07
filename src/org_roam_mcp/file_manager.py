"""File management for org-roam files."""

import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import logging

from .config import OrgRoamConfig
from .database import OrgRoamNode

logger = logging.getLogger(__name__)


class OrgRoamFileManager:
    """Manages org-roam file operations."""

    def __init__(self, config: OrgRoamConfig):
        """Initialize file manager.

        Args:
            config: Org-roam configuration
        """
        self.config = config
        self.org_roam_dir = Path(config.org_roam_directory)

        # Ensure directory exists
        self.org_roam_dir.mkdir(parents=True, exist_ok=True)

    def read_file_content(self, file_path: str) -> str:
        """Read content of an org file.

        Args:
            file_path: Path to the org file (may have quotes)

        Returns:
            File content as string
        """
        try:
            # Clean file path by removing quotes if present
            clean_path = file_path.strip('"') if file_path else ""

            # Handle both absolute and relative paths
            if not os.path.isabs(clean_path):
                clean_path = os.path.join(self.config.org_roam_directory, clean_path)

            with open(clean_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"File not found: {clean_path}")
            return ""
        except Exception as e:
            logger.error(f"Error reading file {clean_path}: {e}")
            return ""

    def read_node_content(self, node: OrgRoamNode) -> str:
        """Read content for a specific node.

        Args:
            node: The org-roam node

        Returns:
            Node content as string
        """
        content = self.read_file_content(node.file)

        if node.level == 0:
            # File-level node, return entire content
            return content
        else:
            # Heading-level node, extract specific section
            return self._extract_heading_content(content, node.pos, node.level)

    def _extract_heading_content(self, content: str, pos: int, level: int) -> str:
        """Extract content for a specific heading.

        Args:
            content: Full file content
            pos: Position of the heading
            level: Heading level

        Returns:
            Heading content
        """
        lines = content.splitlines()

        # Find the starting line (approximately)
        char_count = 0
        start_line = 0

        for i, line in enumerate(lines):
            char_count += len(line) + 1  # +1 for newline
            if char_count >= pos:
                start_line = i
                break

        # Find the end of this heading section
        heading_prefix = "*" * level
        end_line = len(lines)

        for i in range(start_line + 1, len(lines)):
            line = lines[i].strip()
            if line.startswith("*") and not line.startswith("*" * (level + 1)):
                # Found a heading of same or higher level
                end_line = i
                break

        return "\n".join(lines[start_line:end_line])

    def create_node(
        self, title: str, content: str = "", tags: Optional[List[str]] = None
    ) -> Tuple[str, str]:
        """Create a new org-roam node.

        Args:
            title: Node title
            content: Node content
            tags: List of tags

        Returns:
            Tuple of (node_id, absolute_file_path)
        """
        if tags is None:
            tags = []

        # Generate UUID for the node
        node_id = str(uuid.uuid4())

        # Create filename from title
        filename = self._title_to_filename(title)
        file_path = self.org_roam_dir / f"{filename}.org"

        # Ensure filename is unique
        counter = 1
        while file_path.exists():
            file_path = self.org_roam_dir / f"{filename}_{counter}.org"
            counter += 1

        # Create org file content
        org_content = self._create_org_content(node_id, title, content, tags)

        # Write file
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(org_content)
            logger.info(f"Created new org-roam node: {file_path}")
            return node_id, str(file_path)
        except Exception as e:
            logger.error(f"Error creating node file {file_path}: {e}")
            raise

    def update_node_content(self, node: OrgRoamNode, new_content: str) -> None:
        """Update content of an existing node.

        Args:
            node: The node to update
            new_content: New content
        """
        if node.level == 0:
            # File-level node, replace entire content
            self._update_file_content(node.file, new_content)
        else:
            # Heading-level node, update specific section
            self._update_heading_content(node, new_content)

    def _update_file_content(self, file_path: str, new_content: str) -> None:
        """Update entire file content.

        Args:
            file_path: Path to the file (may have quotes)
            new_content: New content
        """
        try:
            # Clean file path by removing quotes if present
            clean_path = file_path.strip('"') if file_path else ""

            # Handle both absolute and relative paths
            if not os.path.isabs(clean_path):
                clean_path = os.path.join(self.config.org_roam_directory, clean_path)

            with open(clean_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            logger.info(f"Updated file content: {clean_path}")
        except Exception as e:
            logger.error(f"Error updating file {clean_path}: {e}")
            raise

    def _update_heading_content(self, node: OrgRoamNode, new_content: str) -> None:
        """Update content for a specific heading.

        Args:
            node: The node to update
            new_content: New content for the heading
        """
        # This is complex - would need to parse org structure properly
        # For now, log that this is not implemented
        logger.warning(f"Heading-level content updates not yet implemented for node {node.id}")
        raise NotImplementedError("Heading-level content updates not yet implemented")

    def _title_to_filename(self, title: str) -> str:
        """Convert title to valid filename.

        Args:
            title: Node title

        Returns:
            Valid filename (without extension)
        """
        # Remove or replace invalid filename characters
        filename = re.sub(r"[^\w\s-]", "", title)
        filename = re.sub(r"[-\s]+", "-", filename)
        filename = filename.strip("-").lower()

        # Ensure filename is not empty
        if not filename:
            filename = f"untitled-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        # Limit length
        if len(filename) > 100:
            filename = filename[:100]

        return filename

    def _create_org_content(self, node_id: str, title: str, content: str, tags: List[str]) -> str:
        """Create org file content with proper org-roam structure.

        Args:
            node_id: Unique node ID
            title: Node title
            content: Node content
            tags: List of tags

        Returns:
            Formatted org content
        """
        # Create properties drawer
        properties = [":PROPERTIES:", f":ID: {node_id}", ":END:"]

        # Create title line
        title_line = f"#+title: {title}"

        # Create filetags line if tags provided
        lines = properties + ["", title_line]

        if tags:
            tags_line = "#+filetags: " + " ".join(f":{tag}:" for tag in tags)
            lines.append(tags_line)

        lines.append("")  # Empty line after metadata

        # Add content
        if content:
            lines.append(content)

        return "\n".join(lines)

    def add_link_to_node(
        self,
        source_file: str,
        target_node_id: str,
        target_title: str,
        position: Optional[int] = None,
    ) -> None:
        """Add a link from one node to another.

        Args:
            source_file: Source file path
            target_node_id: Target node ID
            target_title: Target node title
            position: Position to insert link (if None, append at end)
        """
        link_text = f"[[id:{target_node_id}][{target_title}]]"

        try:
            # Read current content
            current_content = self.read_file_content(source_file)

            if position is None:
                # Append at end
                new_content = current_content.rstrip() + f"\n\n{link_text}"
            else:
                # Insert at specific position (basic implementation)
                new_content = current_content[:position] + link_text + current_content[position:]

            self._update_file_content(source_file, new_content)
            logger.info(f"Added link to {target_title} in {source_file}")

        except Exception as e:
            logger.error(f"Error adding link to {source_file}: {e}")
            raise

    def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from org file.

        Args:
            file_path: Path to org file

        Returns:
            Dictionary with metadata
        """
        content = self.read_file_content(file_path)
        metadata = {}

        # Extract properties
        properties_match = re.search(r":PROPERTIES:(.*?):END:", content, re.DOTALL)
        if properties_match:
            props_text = properties_match.group(1)
            for line in props_text.strip().split("\n"):
                line = line.strip()
                if ":" in line:
                    key, value = line.split(":", 2)[1:]
                    metadata[key.strip()] = value.strip()

        # Extract title
        title_match = re.search(r"^\s*#\+title:\s*(.+)$", content, re.MULTILINE | re.IGNORECASE)
        if title_match:
            metadata["title"] = title_match.group(1).strip()

        # Extract filetags
        tags_match = re.search(r"^\s*#\+filetags:\s*(.+)$", content, re.MULTILINE | re.IGNORECASE)
        if tags_match:
            tags_text = tags_match.group(1).strip()
            # Parse tags in format :tag1::tag2:
            tags = re.findall(r":([^:]+):", tags_text)
            metadata["tags"] = tags

        return metadata

    def list_org_files(self) -> List[str]:
        """List all .org files in the org-roam directory.

        Returns:
            List of file paths relative to org-roam directory
        """
        org_files = []
        try:
            for file_path in self.org_roam_dir.glob("**/*.org"):
                if file_path.is_file():
                    rel_path = file_path.relative_to(self.org_roam_dir)
                    org_files.append(str(rel_path))
        except Exception as e:
            logger.error(f"Error listing org files: {e}")

        return sorted(org_files)
