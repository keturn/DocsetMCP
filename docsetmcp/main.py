from pathlib import Path

from fastmcp.server.providers import FileSystemProvider
from starlette.routing import Mount

from docsetmcp.server import (
    cheatsheet_extractors,
    docsetmcp_config,
    extractors,
    initialize_extractors,
    mcp,
)
from docsetmcp import web


initialize_extractors()

mcp.add_provider(FileSystemProvider(Path(__file__).parent))

for web_path, handler in web.routes:
    mcp.custom_route(web_path, ["GET", "HEAD"])(handler)


def main():
    """Main entry point for the MCP server"""
    import sys
    import argparse

    try:
        from . import __version__
    except ImportError:
        from docsetmcp import __version__

    parser = argparse.ArgumentParser(
        prog="docsetmcp",
        description="Model Context Protocol server for Dash-style docsets",
        epilog="For more information, visit: https://github.com/codybrom/docsetmcp",
    )

    parser.add_argument("--version", "-v", action="version", version=f"DocsetMCP {__version__}")

    parser.add_argument(
        "--list-docsets",
        action="store_true",
        help="List all available docsets and exit",
    )

    parser.add_argument(
        "--test-connection",
        action="store_true",
        help="Test MCP server startup and exit",
    )

    parser.add_argument(
        "--docset-path",
        type=str,
        help="Custom path to docsets directory (overrides DOCSET_PATH environment variable)",
    )

    parser.add_argument(
        "--cheatsheet-path",
        type=str,
        help="Custom path to cheatsheets directory (overrides CHEATSHEET_PATH environment variable)",
    )

    parser.add_argument(
        "--additional-docset-paths",
        nargs="*",
        help="Additional docset paths to search in addition to default location",
    )

    parser.add_argument(
        "--additional-cheatsheet-paths",
        nargs="*",
        help="Additional cheatsheet paths to search in addition to default location",
    )

    # Parse args but allow for no args (normal MCP mode)
    args = parser.parse_args()

    # Update global configuration with CLI arguments
    if args.docset_path:
        docsetmcp_config.docset_path = args.docset_path
        # Re-initialize extractors with new path
        initialize_extractors()

    if args.cheatsheet_path:
        docsetmcp_config.cheatsheet_path = args.cheatsheet_path

    if args.additional_docset_paths:
        docsetmcp_config.additional_docset_paths = args.additional_docset_paths
        # Re-initialize extractors with new paths
        initialize_extractors()

    if args.additional_cheatsheet_paths:
        docsetmcp_config.additional_cheatsheet_paths = args.additional_cheatsheet_paths

    # Handle special commands
    if args.list_docsets:
        print("Available DocsetMCP docsets:")
        if extractors:
            for docset_id, extractor in sorted(extractors.items()):
                languages = list(extractor.language_names)
                lang_str = ", ".join(languages) if languages else "no languages"
                print(f"  {docset_id}: {extractor.title} ({lang_str})")
            print(f"\nTotal: {len(extractors)} docsets available")
        else:
            print("  No docsets found. Please install docsets in Dash.app first.")
        return

    if args.test_connection:
        print(f"DocsetMCP {__version__}")
        print("Testing MCP server startup...")
        try:
            # Quick initialization test
            print(f"✓ Found {len(extractors)} docset(s)")
            print(f"✓ Found {len(cheatsheet_extractors)} cheatsheet(s) cached")
            print("✓ MCP server initialized successfully")
            print("\nStarting MCP server (use Ctrl+C to stop)...")
            # Fall through to normal MCP mode for a few seconds to test
        except Exception as e:
            print(f"✗ Error initializing MCP server: {e}")
            sys.exit(1)

    # Normal MCP server mode
    mcp.run()


if __name__ == "__main__":
    main()
