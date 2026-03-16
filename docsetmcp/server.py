#!/usr/bin/env python3
"""
Dash MCP Server - Extract documentation from Dash docsets as Markdown
"""

import os
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
from docsetmcp.dash_extractor import DashExtractor, initialize_docsets

# Initialize extractors for available docsets (will be populated by initialize_extractors)
extractors: dict[str, DashExtractor] = {}

# Initialize cheatsheet extractors (will be populated as needed)
cheatsheet_extractors: dict[str, CheatsheetExtractor] = {}


def initialize_extractors():
    """Initialize extractors with current configuration"""
    extractors.clear()
    extractors.update(initialize_docsets(docsetmcp_config))

    # TODO: cheatsheets
