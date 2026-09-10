# ZDocsetMCP

**Access your local Dash documentation directly from AI assistants** 🚀

ZDocsetMCP is a Model Context Protocol (MCP) server that seamlessly integrates your local Dash docsets with AI
assistants like Claude, enabling instant access to offline documentation without leaving your conversation.

You probably don't need ZDocsetMCP on macOS, because [Dash](https://kapeli.com/dash) has [MCP support built in](https://blog.kapeli.com/dash-8).
ZDocsetMCP works as a companion to [Zeal](https://zealdocs.org/) on Linux, where Dash is not available.

Searching your local documentation is fast, unhindered by external rate limits, and most importantly:
the results are always from the reference documentation, not unknown websites.

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Features](#-features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Available Tools](#available-tools)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Quick Start

```json
{
  "mcpServers": {
    "docsetmcp": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/keturn/ZDocsetMCP", "docsetmcp"]
    }
  }
}
```

Add to your MCP config and restart your MCP client. Then try asking something like "Find me the AppIntent documentation."

## ✨ Features

### Documentation Search

- **Multi-Docset Support**: Search across 165+ supported docsets including Apple, Node.js, Python, and more
- **Language Filtering**: Target specific programming languages within docsets
- **Name-Based Search**: Only returns entries where search terms match item names for precise results
- **Smart Ranking**: Results ranked by match type (exact > prefix > substring) and dynamic type ordering
- **Container Guidance**: Framework and class entries show drilldown notes for exploring members

### Cheatsheet Access

- **Quick Reference**: Instant access to Git, Vim, Docker, and 40+ other cheatsheets
- **Fuzzy Matching**: Find cheatsheets even with partial names
- **Category Browsing**: Explore commands by category within each cheatsheet
- **Search Within**: Query specific commands inside any cheatsheet

### Performance & Integration

- **Efficient Caching**: In-memory caching for repeated queries
- **Direct Database Access**: No intermediate servers or APIs
- **Universal**: Works with Claude Desktop, Cursor, VS Code, and any MCP-compatible client
- **Framework Discovery**: List all available frameworks/types in any docset
- **Container Guidance**: Automatic drilldown notes for frameworks and classes with members

## 📦 Supported Docsets

ZDocsetMCP supports all the same docsets as [Zeal](https://zealdocs.org/).

Use `list_available_docsets` to see all docsets installed on your system.

## Prerequisites

- [Dash](https://kapeli.com/dash) with desired docsets downloaded
- Python 3.14 or higher
- UV package manager ([How to Install](https://docs.astral.sh/uv/getting-started/installation/))
- An AI assistant that supports MCP (Claude Desktop, Claude Code CLI, Cursor IDE, etc.)

## Configuration

### Custom Docset Locations

By default, DocsetMCP looks for docsets in Dash's standard directories:

- **Docsets**: `~/Library/Application Support/Dash/DocSets`
- **Cheatsheets**: `~/Library/Application Support/Dash/Cheat Sheets`

You can customize these locations using:

#### Environment Variables

```bash
# Set custom docset directory
export DOCSET_PATH="/path/to/your/docsets"

# Set custom cheatsheet directory
export CHEATSHEET_PATH="/path/to/your/cheatsheets"

# Run with custom paths
docsetmcp
```

#### Command Line Arguments

```bash
# Test with custom docset path
docsetmcp --docset-path "/path/to/your/docsets" --list-docsets

# Test with custom cheatsheet path
docsetmcp --cheatsheet-path "/path/to/your/cheatsheets" --test-connection

# Use both custom paths
docsetmcp --docset-path "/custom/docsets" --cheatsheet-path "/custom/cheatsheets"

# Use additional search paths (searches multiple locations)
docsetmcp --additional-docset-paths "/extra/docsets" "/more/docsets"
docsetmcp --additional-cheatsheet-paths "/extra/cheatsheets" "/more/cheatsheets"
```

**Priority Order:**

1. CLI arguments (highest priority)
2. Environment variables
3. Default Dash locations (lowest priority)

**Additional Search Paths:**

The `--additional-docset-paths` and `--additional-cheatsheet-paths` options allow DocsetMCP to search in multiple locations beyond the primary path. This is useful when:

- You have docsets in multiple directories
- You want to include third-party or custom docsets
- You're sharing docsets across different tools

DocsetMCP will automatically discover and configure docsets found in these additional paths.

### MCP Client Setup

Choose your MCP client below for specific setup instructions:

<details>
<summary><b>🤖 Claude Desktop</b></summary>

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "docsetmcp": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/keturn/ZDocsetMCP", "docsetmcp"]
    }
  }
}
```

**For custom docset locations:**

```json
{
  "mcpServers": {
    "docsetmcp": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/keturn/ZDocsetMCP", "docsetmcp"],
      "env": {
        "DOCSET_PATH": "/path/to/your/docsets",
        "CHEATSHEET_PATH": "/path/to/your/cheatsheets"
      }
    }
  }
}
```

</details>

<details>
<summary><b>⌨️ Claude Code CLI</b></summary>

```bash
# For current project
claude mcp add zdocsetmcp "uvx --from git+https://github.com/keturn/ZDocsetMCP docsetmcp"

# For all projects
claude mcp add --scope user zdocsetmcp "uvx --from git+https://github.com/keturn/ZDocsetMCP docsetmcp"
```

</details>

<details>
<summary><b>📝 Cursor, VS Code, Windsurf and other MCP-compatible clients</b></summary>

Add to your MCP configuration (Cursor: `.mcp/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "docsetmcp": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/keturn/ZDocsetMCP", "docsetmcp"]
    }
  }
}
```

**Note**: Restart your client and check your MCP settings for connection status.

</details>

## Installation

### No Installation Required (Recommended)

If your MCP client supports `uvx`, no installation is needed! The package will be automatically downloaded and run when needed. See the [Quick Start](#quick-start) or [Configuration](#configuration) sections.

### Manual Installation

If you prefer to install locally or your MCP client doesn't support `uvx`:

```bash
uv tool install git+https://github.com/keturn/ZDocsetMCP
```

Then use `docsetmcp` instead of `uvx docsetmcp` in your configuration.

## Usage Examples

Once configured, you can ask your AI assistant to search documentation naturally:

### 🍎 iOS/macOS Development

```text
"Search for URLSession documentation"
"Show me how to use AppIntent in SwiftUI"
"Find CarPlay framework documentation"  # Returns framework + related entries with drilldown notes
"Search for CPListTemplate class"       # Returns specific CarPlay class
"Find NSPredicate examples"
```

### 🌐 Web Development

```text
"Look up Express.js middleware documentation"
"Search React hooks in the React docset"
"Find CSS flexbox properties"
```

### 🛠️ DevOps & Terminal

```text
"Search git rebase commands in the Git cheatsheet"
"Show Docker compose syntax from the cheatsheet"
"Find bash array manipulation commands"
```

### 📊 Data Science

```text
"Search pandas DataFrame methods"
"Look up NumPy array broadcasting"
"Find matplotlib pyplot functions"
```

### Advanced Usage

```text
# Search specific docset with language filter
"Use search_docs for 'URLSession' in the apple_api_reference docset with Swift language"

# Explore framework members using drilldown guidance
"Search for 'SwiftData' then follow the drilldown note to see all members"

# List all available tools
"What frameworks are available in the nodejs docset?"

# Browse cheatsheet categories
"Show all categories in the vim cheatsheet"
```

## Discovery Workflow

DocsetMCP is designed for **name-based searches**, not keyword searching. Follow this workflow:

### 1. **Start with Discovery Tools**

```text
# Find what languages are available
"List all available programming languages"

# Find docsets for your language
"Show me all Python docsets"

# See what types are available in a docset
"List all types in the apple_api_reference docset for Swift"

# Browse entries by type with letter filters
"Show me all Classes starting with 'UI' in apple_api_reference for Swift"
```

### 2. **Then Search by Exact Names**

```text
# Once you know exact names, search for them
"Search for UIViewController in apple_api_reference with Swift"
"Find readFile documentation in nodejs docset"
"Show me the CarPlay framework documentation"
```

### 3. **Use Drilldown Notes**

When you find container types (frameworks, classes), follow the drilldown guidance:

```text
# Container entry will show: "contains 42 additional members - use search_docs('ContainerName', max_results=50)"
"Search for SwiftData in apple_api_reference with max_results=50"
```

## How It Works

1. **Multi-Format Support**: Handles both Apple cache format and tarix compression
2. **Direct Database Access**: Queries Dash's SQLite databases for fast lookups
3. **Name-Based Matching**: Only returns entries where search terms match item names (no false positives)
4. **Smart Ranking**: Prioritizes exact matches, then prefix matches, then substring matches
5. **Dynamic Type Ordering**: Uses docset configuration files for intelligent result prioritization
6. **Container Detection**: Automatically detects frameworks/classes with members and provides exploration guidance
7. **Smart Extraction**: Decompresses Apple's DocC JSON or extracts HTML from tarix archives
8. **Markdown Formatting**: Converts documentation to readable Markdown

## Available Tools

DocsetMCP provides eleven powerful tools for accessing your documentation:

### 🔍 `search_docs`

Search and extract documentation from any docset.

| Parameter     | Type   | Description                                | Default        |
|---------------|--------|--------------------------------------------|----------------|
| `query`       | string | **Exact name** to search (not keywords)    | *required*     |
| `docset`      | string | Target docset (e.g., 'nodejs', 'python_3') | *required*     |
| `language`    | string | Programming language filter                | docset default |
| `max_results` | int    | Number of results (1-10)                   | 3              |

### 📋 `search_cheatsheet`

Search Dash cheatsheets for quick command reference.

| Parameter     | Type   | Description                          | Default    |
|---------------|--------|--------------------------------------|------------|
| `cheatsheet`  | string | Cheatsheet name (e.g., 'git', 'vim') | *required* |
| `query`       | string | Search within cheatsheet             | -          |
| `category`    | string | Filter by category                   | -          |
| `max_results` | int    | Number of results (1-50)             | 10         |

### 📚 `list_available_docsets`

List all installed Dash docsets with their supported languages.

### 📝 `list_available_cheatsheets`

List all available Dash cheatsheets that can be searched.

### 🏗️ `list_frameworks`

List frameworks/types within a specific docset.

| Parameter | Type   | Description            | Default    |
|-----------|--------|------------------------|------------|
| `docset`  | string | Target docset          | *required* |
| `filter`  | string | Filter framework names | -          |

### 🌍 `list_languages`

Discover all programming languages with available documentation.

### 📖 `list_docsets_by_language`

Find all docsets that support a specific programming language.

| Parameter  | Type   | Description          | Default    |
|------------|--------|----------------------|------------|
| `language` | string | Programming language | *required* |

### 🏷️ `list_types`

List all available types (Class, Protocol, Function, etc.) in a docset/language.

| Parameter  | Type   | Description                 | Default    |
|------------|--------|-----------------------------|------------|
| `docset`   | string | Target docset               | *required* |
| `language` | string | Programming language filter | -          |

### 📋 `list_entries`

List entries filtered by type and optional name prefix.

| Parameter     | Type   | Description                                   | Default    |
|---------------|--------|-----------------------------------------------|------------|
| `docset`      | string | Target docset                                 | *required* |
| `type_name`   | string | Type to filter by (e.g., 'Class', 'Protocol') | *required* |
| `language`    | string | Programming language filter                   | -          |
| `name_filter` | string | Filter entries by name prefix                 | -          |
| `max_results` | int    | Number of results (1-100)                     | 20         |

### 📂 `list_cheatsheet_categories`

List all categories within a specific cheatsheet.

| Parameter    | Type   | Description     | Default    |
|--------------|--------|-----------------|------------|
| `cheatsheet` | string | Cheatsheet name | *required* |

### 📄 `fetch_cheatsheet`

Fetch entire cheatsheet content (recommended for comprehensive access).

| Parameter    | Type   | Description     | Default    |
|--------------|--------|-----------------|------------|
| `cheatsheet` | string | Cheatsheet name | *required* |

## Troubleshooting

<details>
<summary><b>❌ "Docset not found" error</b></summary>

This means the docset isn't installed in Zeal. To fix:

1. Open Zeal
2. Go to File → Docset Library
3. Download the required docset
4. Restart your MCP client

</details>

<details>
<summary><b>📭 No results found</b></summary>

- The content might not be in your local Dash cache
- Try searching with different terms or partial matches
- Use `list_available_docsets` to verify the docset is loaded
- Some docsets may use different naming conventions (e.g., 'fs' vs 'filesystem')

</details>

## Development

### Building from Source

```bash
# Clone the repository
git clone https://github.com/keturn/ZDocsetMCP.git
cd docsetmcp

# Create venv and install project + dev dependencies
uv sync --all-extras

# Set up pre-commit hooks
uv run pre-commit install
```

### Testing

```bash
# Run basic structure tests
pytest tests/test_docsets.py::TestDocsets::test_yaml_structure -v

# Run quick tests (structure + existence)
pytest tests/ -k "yaml_structure or test_docset_exists" -v

# Run full test suite (all docsets)
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=docsetmcp --cov-report=html -v

# Run tests in parallel
pytest tests/ -n auto -v

# Validate cheatsheets
python scripts/validate_cheatsheets.py
```

### Code Quality

```bash
# Format Python code with ruff
ruff docsetmcp/

# Format YAML files with yamlfix
yamlfix docsetmcp/docsets/*.yaml

# Run all pre-commit hooks
pre-commit run --all-files

# Run specific hook
pre-commit run yamlfix --all-files

# Run spell check (cspell installed automatically during setup)
npm run spell
```

### CLI Commands

```bash
# Test version
docsetmcp --version

# List available docsets
docsetmcp --list-docsets

# Test server startup
docsetmcp --test-connection

# Test with custom paths
docsetmcp --docset-path "/custom/path" --list-docsets
```

### Building Distribution

```bash
# Build package
uv build
```

## Architecture

### Core Components

- **docsetmcp/server.py**: Main MCP server implementation using FastMCP. Contains the DashExtractor class that handles:
    - Apple cache format (SHA-1 UUID-based with brotli compression)
    - Tarix format (tar.gz archives)
    - SQLite database queries for documentation lookup
    - HTML to Markdown conversion

- **docsetmcp/config_loader.py**: Configuration system that loads YAML configs for 165+ supported docsets. Provides smart defaults and handles both simple and complex configuration formats.

- **docsetmcp/docsets/**: YAML configuration files for each supported docset, defining:
    - Docset paths and formats
    - Language variants and filters
    - Type priorities for search results

### Key Implementation Details

1. **Multi-Format Support**: The server detects and handles both Apple's modern cache format (using SHA-1 based UUIDs) and the older tarix compression format automatically based on docset configuration.

2. **Caching Strategy**: Extracted documentation is cached in memory (_fs_cache for Apple format, _html_cache for tarix) to improve performance on repeated queries.

3. **Search Algorithm**: Uses SQLite case-insensitive LIKE queries on the optimizedIndex.dsidx database. Results are ranked by match type (exact > prefix > substring) and then by dynamic type ordering from docset configuration files. Only returns entries where the search term matches the item name.

4. **Configuration Loading**: The ConfigLoader applies smart defaults, allowing minimal YAML configs while supporting complex overrides when needed.

5. **Container Type Detection**: Framework, class, and module entries automatically include drilldown notes when they contain additional members, guiding users to search for more specific content.

## Contributing

### Reporting Issues

- 🐛 [Bug Reports](https://github.com/keturn/ZDocsetMCP/issues/new?labels=bug)
- 💡 [Feature Requests](https://github.com/keturn/ZDocsetMCP/issues/new?labels=enhancement)
- 📚 [Documentation Issues](https://github.com/keturn/ZDocsetMCP/issues/new?labels=documentation)

### Development Guidelines

- Follow PEP 8 style guidelines
- Add tests for new features
- Update documentation as needed
- Keep commits focused and descriptive

## Technical Architecture

DocsetMCP leverages Dash's internal structure for efficient documentation access:

- **Format Support**: Handles both Apple's modern cache format (SHA-1 UUID-based with brotli compression) and traditional tarix archives
- **Caching Strategy**: In-memory caching for repeated queries
- **Database Access**: Direct SQLite queries to Dash's optimized indexes
- **Content Extraction**: Smart extraction with fallback strategies
- **Type System**: Full type hints for better IDE support

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

ZDocsetMCP is derived from [DocsetMCP](https://github.com/codybrom/DocsetMCP) by [Cody Bromley](https://github.com/codybrom/).

Thanks to [Kapeli](https://kapeli.com/) for creating Dash,
and to [Oleg Shparber](https://github.com/trollixx) and team for [Zeal](https://zealdocs.org/).

Built on the [Model Context Protocol](https://modelcontextprotocol.io/) standard.
