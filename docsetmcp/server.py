#!/usr/bin/env python3
"""
Dash MCP Server - Extract documentation from Dash docsets as Markdown
"""

import os
from pathlib import Path
from typing import TypedDict, Optional

from fastmcp import FastMCP

from docsetmcp.common import (
    ProcessedDocsetConfig,
)


class MatchedDocsetInfo(TypedDict):
    config: ProcessedDocsetConfig
    matched_lang: Optional[str]


# Create MCP server
mcp = FastMCP("Dash")


# Global configuration class to hold runtime settings
class DocsetMCPConfig:
    def __init__(self):
        self.docset_path: str | None = None
        self.cheatsheet_path: str | None = None
        self.additional_docset_paths: list[str] = []
        self.additional_cheatsheet_paths: list[str] = []

    def parse_path_list(self, value: str | list[str] | None) -> list[str]:
        """Parse path list from various input formats"""
        if not value:
            return []
        if isinstance(value, list):
            return [os.path.expanduser(p) for p in value if p.strip()]
        # Must be str at this point since we've ruled out None and list
        return [os.path.expanduser(p.strip()) for p in value.split(":") if p.strip()]


# Global config instance
docsetmcp_config = DocsetMCPConfig()

from docsetmcp.cheatsheet_extractor import CheatsheetExtractor
from docsetmcp.dash_extractor import DashExtractor

# Initialize extractors for available docsets (will be populated by initialize_extractors)
extractors: dict[str, DashExtractor] = {}

# Initialize cheatsheet extractors (will be populated as needed)
cheatsheet_extractors: dict[str, CheatsheetExtractor] = {}


def initialize_extractors():
    """Initialize extractors with current configuration"""
    global extractors
    extractors.clear()

    # Load available docset configs using new system
    from docsetmcp.config_loader import ConfigLoader

    loader = ConfigLoader()
    try:
        # Pass additional docset paths for auto-detection
        additional_paths = []
        if docsetmcp_config.additional_docset_paths:
            additional_paths = docsetmcp_config.parse_path_list(
                docsetmcp_config.additional_docset_paths
            )

        all_configs = loader.load_all_configs(
            additional_paths if additional_paths else None
        )

        # Try to initialize each docset
        for docset_type, config in all_configs.items():
            try:
                # Create a modified DashExtractor that uses the provided config
                extractor = DashExtractor.__new__(DashExtractor)
                extractor.config = config

                # Build list of paths to search for docsets
                search_paths: list[str] = []

                # Use custom docset location if provided, otherwise use configured paths
                if docsetmcp_config.docset_path:
                    search_paths.append(
                        os.path.expanduser(docsetmcp_config.docset_path)
                    )
                else:
                    # Check environment variable for custom location
                    env_path = os.getenv("DOCSET_PATH")
                    if env_path:
                        search_paths.append(os.path.expanduser(env_path))

                    # Add additional paths from global config
                    if docsetmcp_config.additional_docset_paths:
                        additional_search_paths = docsetmcp_config.parse_path_list(
                            docsetmcp_config.additional_docset_paths
                        )
                        search_paths.extend(additional_search_paths)

                    # If no custom paths specified, use default Dash location
                    if not search_paths:
                        search_paths.append(
                            os.path.expanduser(
                                "~/Library/Application Support/Dash/DocSets"
                            )
                        )

                # Find the docset in the search paths
                extractor.docset = None
                for search_path in search_paths:
                    potential_docset = Path(search_path) / config["docset_path"]
                    if potential_docset.exists():
                        extractor.docset = potential_docset
                        break

                # If not found, skip this docset
                if extractor.docset is None:
                    continue

                # Set up paths based on docset format
                if config["format"] == "apple":
                    extractor.fs_dir = (
                        extractor.docset / "Contents/Resources/Documents/fs"
                    )
                    extractor.optimized_db = (
                        extractor.docset / "Contents/Resources/optimizedIndex.dsidx"
                    )
                    extractor.cache_db = (
                        extractor.docset / "Contents/Resources/Documents/cache.db"
                    )
                    # Cache for decompressed fs files
                    extractor.fs_cache = {}
                elif config["format"] == "tarix":
                    extractor.optimized_db = (
                        extractor.docset / "Contents/Resources/optimizedIndex.dsidx"
                    )
                    extractor.tarix_archive = (
                        extractor.docset / "Contents/Resources/tarix.tgz"
                    )
                    extractor.tarix_index = (
                        extractor.docset / "Contents/Resources/tarixIndex.db"
                    )
                    # Cache for extracted HTML content
                    extractor.html_cache = {}

                # Check if docset exists
                if not extractor.docset.exists():
                    continue

                extractors[docset_type] = extractor

            except Exception as e:
                # Debug: print what went wrong
                print(f"Warning: Failed to initialize {docset_type}: {e}")
                pass

    except Exception:
        # If config system fails, extractors will be empty
        # This is handled gracefully by the tool functions
        pass
