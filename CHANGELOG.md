# Changelog

All notable changes to the org-roam MCP server project will be documented in this file.

## [0.2.0] - 2024-12-XX - Enhanced Reliability

### 🔧 Fixed
- **File Path Handling**: Resolved issues with quoted file paths returned from the org-roam database
- **Node ID Lookup**: Fixed node retrieval by properly handling both quoted and unquoted node ID formats
- **Database Queries**: Corrected path escaping issues in update and link operations
- **Error Handling**: Fixed malformed path errors in file operations

### ✨ Added  
- **Input Validation**: Comprehensive validation for all tool inputs with descriptive error messages
- **Path Normalization**: Automatic cleaning of file paths and node IDs with quote removal
- **Database Refresh**: Automatic database connection refresh after file operations
- **Better Logging**: Enhanced error reporting and debugging information
- **Test Suite**: Comprehensive test script (`test_improvements.py`) to validate functionality

### 🚀 Improved
- **Search Synchronization**: New nodes and updates now appear immediately in search results
- **Error Messages**: More descriptive and actionable error messages throughout
- **Code Robustness**: Better handling of edge cases and malformed data
- **Documentation**: Updated README with recent improvements and troubleshooting

### 🧪 Testing
- Added comprehensive test suite covering:
  - Database connection and queries
  - Node ID format handling  
  - File path normalization
  - Search functionality
  - Node creation and updates
  - Database refresh operations

## [0.1.0] - Initial Release

### ✨ Added
- Basic MCP server implementation for org-roam integration
- Node search by title, tags, and aliases
- Node retrieval with detailed information
- Backlink and forward link exploration
- Node creation with title, content, and tags
- Content updates for existing nodes
- Link creation between nodes
- File listing functionality
- Auto-detection of org-roam database and directory
- Environment variable configuration support