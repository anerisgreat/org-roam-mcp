"""Main MCP server implementation for org-roam integration."""

import asyncio
import logging
from typing import Any, Dict, List, Optional
import json

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

from .config import OrgRoamConfig
from .database import OrgRoamDatabase, OrgRoamNode
from .file_manager import OrgRoamFileManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize server
server = Server("org-roam-mcp")

# Global variables for database and config
config: Optional[OrgRoamConfig] = None
db: Optional[OrgRoamDatabase] = None
file_manager: Optional[OrgRoamFileManager] = None



@server.list_resources()  # type: ignore
async def handle_list_resources() -> List[types.Resource]:
    """List available org-roam resources."""
    return [
        types.Resource(
            uri="org-roam://nodes",  # type: ignore
            name="All Nodes",
            description="All nodes in the org-roam database",
            mimeType="application/json",
        ),
        types.Resource(
            uri="org-roam://stats",  # type: ignore
            name="Database Statistics",
            description="Statistics about the org-roam database",
            mimeType="application/json",
        ),
    ]


@server.read_resource()  # type: ignore
async def handle_read_resource(uri: str) -> str:
    """Read org-roam resources."""
    if not db:
        raise RuntimeError("Database not initialized")
    if not config:
        raise RuntimeError("Config not initialized")
    if not file_manager:
        raise RuntimeError("File manager not initialized")

    if uri == "org-roam://nodes":
        nodes = db.get_all_nodes(limit=config.max_search_results)
        nodes_data = [
            {
                "id": node.id,
                "title": node.title,
                "file": node.file,
                "level": node.level,
                "tags": db.get_node_tags(node.id),
                "aliases": db.get_node_aliases(node.id),
            }
            for node in nodes
        ]
        return json.dumps(nodes_data, indent=2)

    elif uri == "org-roam://stats":
        stats = db.get_database_stats()
        return json.dumps(stats, indent=2)

    elif uri.startswith("org-roam://node/"):
        node_id = uri.replace("org-roam://node/", "")
        node = db.get_node_by_id(node_id)
        if not node:
            raise ValueError(f"Node not found: {node_id}")

        # Get additional node information
        tags = db.get_node_tags(node_id)
        aliases = db.get_node_aliases(node_id)
        backlinks = db.get_backlinks(node_id)
        forward_links = db.get_forward_links(node_id)

        # Read file content
        content = file_manager.read_node_content(node)

        node_data = {
            "id": node.id,
            "title": node.title,
            "file": node.file,
            "level": node.level,
            "content": content,
            "tags": tags,
            "aliases": aliases,
            "backlinks": [{"source": link.source, "type": link.type} for link in backlinks],
            "forward_links": [{"dest": link.dest, "type": link.type} for link in forward_links],
        }
        return json.dumps(node_data, indent=2)

    else:
        raise ValueError(f"Unknown resource: {uri}")


@server.list_tools()  # type: ignore
async def handle_list_tools() -> List[types.Tool]:
    """List available tools."""
    return [
        types.Tool(
            name="search_nodes",
            description="Search for nodes by title, tags, or aliases",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query string"},
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 50)",
                        "default": 50,
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="get_node",
            description="Get detailed information about a specific node",
            inputSchema={
                "type": "object",
                "properties": {
                    "node_id": {"type": "string", "description": "The ID of the node to retrieve"}
                },
                "required": ["node_id"],
            },
        ),
        types.Tool(
            name="get_backlinks",
            description="Get all nodes that link to a specific node",
            inputSchema={
                "type": "object",
                "properties": {
                    "node_id": {"type": "string", "description": "The ID of the target node"}
                },
                "required": ["node_id"],
            },
        ),
        types.Tool(
            name="create_node",
            description="Create a new org-roam node",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Title of the new node"},
                    "content": {
                        "type": "string",
                        "description": "Content of the new node",
                        "default": "",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for the new node",
                        "default": [],
                    },
                },
                "required": ["title"],
            },
        ),
        types.Tool(
            name="update_node",
            description="Update content of an existing node",
            inputSchema={
                "type": "object",
                "properties": {
                    "node_id": {"type": "string", "description": "ID of the node to update"},
                    "content": {"type": "string", "description": "New content for the node"},
                },
                "required": ["node_id", "content"],
            },
        ),
        types.Tool(
            name="add_link",
            description="Add a link from one node to another",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_node_id": {"type": "string", "description": "ID of the source node"},
                    "target_node_id": {"type": "string", "description": "ID of the target node"},
                },
                "required": ["source_node_id", "target_node_id"],
            },
        ),
        types.Tool(
            name="list_files",
            description="List all org files in the org-roam directory",
            inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
        ),
    ]


@server.call_tool()  # type: ignore
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle tool calls."""
    if not db:
        raise RuntimeError("Database not initialized")
    if not file_manager:
        raise RuntimeError("File manager not initialized")

    if name == "search_nodes":
        query = arguments["query"]
        limit = arguments.get("limit", 50)

        # Input validation
        if not query or not isinstance(query, str):
            return [
                types.TextContent(
                    type="text", text=json.dumps({"error": "Query must be a non-empty string"})
                )
            ]

        if not isinstance(limit, int) or limit < 1 or limit > 1000:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({"error": "Limit must be an integer between 1 and 1000"}),
                )
            ]

        nodes = db.search_nodes(query.strip(), limit=limit)
        results = []

        for node in nodes:
            tags = db.get_node_tags(node.id)
            aliases = db.get_node_aliases(node.id)

            results.append(
                {
                    "id": node.id,
                    "title": node.title,
                    "file": node.file,
                    "tags": tags,
                    "aliases": aliases,
                }
            )

        return [
            types.TextContent(
                type="text",
                text=json.dumps(
                    {"query": query, "results": results, "count": len(results)}, indent=2
                ),
            )
        ]

    elif name == "get_node":
        node_id = arguments["node_id"]

        # Input validation
        if not node_id or not isinstance(node_id, str):
            return [
                types.TextContent(
                    type="text", text=json.dumps({"error": "Node ID must be a non-empty string"})
                )
            ]

        fetched_node = db.get_node_by_id(node_id)

        if not fetched_node:
            return [types.TextContent(type="text", text=f"Node not found: {node_id}")]

        tags = db.get_node_tags(node_id)
        aliases = db.get_node_aliases(node_id)
        backlinks = db.get_backlinks(node_id)
        forward_links = db.get_forward_links(node_id)

        # Read actual file content
        content = file_manager.read_node_content(fetched_node)

        result = {
            "id": fetched_node.id,
            "title": fetched_node.title,
            "file": fetched_node.file,
            "level": fetched_node.level,
            "content": content,
            "tags": tags,
            "aliases": aliases,
            "backlinks_count": len(backlinks),
            "forward_links_count": len(forward_links),
        }

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "get_backlinks":
        node_id = arguments["node_id"]
        backlinks = db.get_backlinks(node_id)

        # Get details about source nodes
        results = []
        for link in backlinks:
            source_node = db.get_node_by_id(link.source)
            if source_node:
                results.append(
                    {
                        "source_id": link.source,
                        "source_title": source_node.title,
                        "source_file": source_node.file,
                        "link_type": link.type,
                    }
                )

        return [
            types.TextContent(
                type="text",
                text=json.dumps(
                    {"target_node": node_id, "backlinks": results, "count": len(results)}, indent=2
                ),
            )
        ]

    elif name == "create_node":
        title = arguments["title"]
        content = arguments.get("content", "")
        tags = arguments.get("tags", [])

        # Input validation
        if not title or not isinstance(title, str):
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {"success": False, "error": "Title must be a non-empty string"}
                    ),
                )
            ]

        if not isinstance(content, str):
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({"success": False, "error": "Content must be a string"}),
                )
            ]

        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({"success": False, "error": "Tags must be a list of strings"}),
                )
            ]

        try:
            # Create the node using file manager
            node_id, file_path = file_manager.create_node(title.strip(), content, tags)

            # Write node directly into the SQLite DB — no Emacs required
            db.insert_file_node(file_path, node_id, title.strip(), tags)

            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": True,
                            "node_id": node_id,
                            "title": title,
                            "message": f"Created new node: {title}",
                        },
                        indent=2,
                    ),
                )
            ]
        except Exception as e:
            logger.error(f"Error creating node '{title}': {e}")
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {"success": False, "error": f"Failed to create node: {str(e)}"}
                    ),
                )
            ]

    elif name == "update_node":
        node_id = arguments["node_id"]
        new_content = arguments["content"]

        # Get the node first
        node_to_update = db.get_node_by_id(node_id)
        if not node_to_update:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({"success": False, "error": f"Node not found: {node_id}"}),
                )
            ]

        try:
            file_manager.update_node_content(node_to_update, new_content)
            # Update the file hash so Emacs re-indexes on next sync
            db.update_file_hash(node_to_update.file)
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": True,
                            "node_id": node_id,
                            "message": f"Updated node: {node_to_update.title}",
                        },
                        indent=2,
                    ),
                )
            ]
        except Exception as e:
            return [
                types.TextContent(type="text", text=json.dumps({"success": False, "error": str(e)}))
            ]

    elif name == "add_link":
        source_node_id = arguments["source_node_id"]
        target_node_id = arguments["target_node_id"]

        # Get both nodes
        source_node = db.get_node_by_id(source_node_id)
        target_node = db.get_node_by_id(target_node_id)

        if not source_node:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {"success": False, "error": f"Source node not found: {source_node_id}"}
                    ),
                )
            ]

        if not target_node:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {"success": False, "error": f"Target node not found: {target_node_id}"}
                    ),
                )
            ]

        try:
            file_manager.add_link_to_node(
                source_node.file, target_node_id, target_node.title or "Untitled"
            )
            # Update the file hash so Emacs re-indexes the new link on next sync
            db.update_file_hash(source_node.file)
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": True,
                            "source_node": source_node.title,
                            "target_node": target_node.title,
                            "message": f"Added link from '{source_node.title}' to '{target_node.title}'",
                        },
                        indent=2,
                    ),
                )
            ]
        except Exception as e:
            return [
                types.TextContent(type="text", text=json.dumps({"success": False, "error": str(e)}))
            ]

    elif name == "list_files":
        org_files = file_manager.list_org_files()

        # Get metadata for each file
        files_info = []
        for file_path in org_files[:50]:  # Limit to avoid too much data
            try:
                metadata = file_manager.get_file_metadata(file_path)
                files_info.append(
                    {
                        "file": file_path,
                        "title": metadata.get("title", ""),
                        "id": metadata.get("ID", ""),
                        "tags": metadata.get("tags", []),
                    }
                )
            except Exception as e:
                logger.warning(f"Error reading metadata for {file_path}: {e}")

        return [
            types.TextContent(
                type="text",
                text=json.dumps(
                    {
                        "files": files_info,
                        "total_count": len(org_files),
                        "displayed_count": len(files_info),
                    },
                    indent=2,
                ),
            )
        ]

    else:
        raise ValueError(f"Unknown tool: {name}")


async def main() -> None:
    """Main server entry point."""
    global config, db, file_manager

    # Initialize configuration
    try:
        config = OrgRoamConfig.from_environment()
        config.validate()
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        raise

    # Initialize database
    try:
        db = OrgRoamDatabase(config.db_path)
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise

    # Initialize file manager
    try:
        file_manager = OrgRoamFileManager(config)
        logger.info("File manager initialized")
    except Exception as e:
        logger.error(f"File manager initialization error: {e}")
        raise

    # Run the server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="org-roam-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def cli_main():
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())
