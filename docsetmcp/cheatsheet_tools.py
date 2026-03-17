import os
from pathlib import Path

from fastmcp.tools.function_tool import tool  # https://github.com/PrefectHQ/fastmcp/issues/3530

from docsetmcp.cheatsheet_extractor import CheatsheetExtractor
from docsetmcp.server import cheatsheet_extractors, docsetmcp_config


@tool()
def list_available_cheatsheets() -> str:
    """
    List all available Dash cheatsheets.

    Returns:
        List of available cheatsheets
    """
    # Use configured cheatsheet path or default
    if docsetmcp_config.cheatsheet_path:
        cheatsheets_path = Path(os.path.expanduser(docsetmcp_config.cheatsheet_path))
    else:
        # Check environment variable
        env_path = os.getenv("CHEATSHEET_PATH")
        if env_path:
            cheatsheets_path = Path(os.path.expanduser(env_path))
        else:
            cheatsheets_path = Path(
                os.path.expanduser("~/Library/Application Support/Dash/Cheat Sheets")
            )

    if not cheatsheets_path.exists():
        return f"Cheatsheets directory not found at {cheatsheets_path}."

    cheatsheets: list[str] = []
    for path in sorted(cheatsheets_path.iterdir()):
        if path.is_dir() and list(path.glob("*.docset")):
            # Extract simple name from directory
            name = path.name
            # Try to make it more command-friendly
            simple_name = name.lower().replace(" ", "-")
            cheatsheets.append(f"- **{simple_name}**: {name}")

    if not cheatsheets:
        return "No cheatsheets found. Please download some from Dash."

    lines = ["Available cheatsheets:"] + cheatsheets
    lines.append(
        "\nUse the simplified name (e.g., 'git' instead of 'Git') when searching."
    )

    return "\n".join(lines)


@tool()
def search_cheatsheet(
    cheatsheet: str, query: str = "", category: str = "", max_results: int = 10
) -> str:
    """
    Search a Dash cheatsheet for quick reference information.

    Args:
        cheatsheet: Name of the cheatsheet (e.g., 'git', 'vim', 'docker')
        query: Optional search query within the cheatsheet
        category: Optional category to filter results
        max_results: Maximum number of results (1-50)

    Returns:
        Formatted cheatsheet entries
    """
    if not 1 <= max_results <= 50:
        return "Error: max_results must be between 1 and 50"

    # Try to get or create the cheatsheet extractor
    if cheatsheet not in cheatsheet_extractors:
        try:
            cheatsheet_extractors[cheatsheet] = CheatsheetExtractor(
                cheatsheet, docsetmcp_config.cheatsheet_path
            )
        except FileNotFoundError:
            available = list_available_cheatsheets()
            return f"Error: Cheatsheet '{cheatsheet}' not found.\n\n{available}"

    return cheatsheet_extractors[cheatsheet].search(query, category, max_results)


@tool()
def list_cheatsheet_categories(cheatsheet: str) -> str:
    """
    List all categories in a specific cheatsheet.

    Args:
        cheatsheet: Name of the cheatsheet (e.g., 'git', 'macports', 'docker')

    Returns:
        List of categories in the cheatsheet
    """
    # Try to get or create the cheatsheet extractor
    if cheatsheet not in cheatsheet_extractors:
        try:
            cheatsheet_extractors[cheatsheet] = CheatsheetExtractor(
                cheatsheet, docsetmcp_config.cheatsheet_path
            )
        except FileNotFoundError:
            return f"Error: Cheatsheet '{cheatsheet}' not found."

    extractor = cheatsheet_extractors[cheatsheet]
    categories = extractor.get_categories()

    if not categories:
        return f"No categories found in {cheatsheet} cheatsheet."

    lines = [f"# {cheatsheet.title()} Cheatsheet Categories\n"]
    for cat in categories:
        lines.append(f"- {cat}")

    lines.append(
        f"\n\nUse these category names with search_cheatsheet to filter results."
    )

    return "\n".join(lines)


@tool()
def fetch_cheatsheet(cheatsheet: str) -> str:
    """
    Fetch the entire content of a Dash cheatsheet.

    This is the recommended way to access cheatsheet data when you need
    comprehensive information or want to browse all available commands.

    Args:
        cheatsheet: Name of the cheatsheet (e.g., 'git', 'vim', 'docker')

    Returns:
        Complete cheatsheet content formatted as Markdown
    """
    # Try to get or create the cheatsheet extractor
    if cheatsheet not in cheatsheet_extractors:
        try:
            cheatsheet_extractors[cheatsheet] = CheatsheetExtractor(
                cheatsheet, docsetmcp_config.cheatsheet_path
            )
        except FileNotFoundError:
            available = list_available_cheatsheets()
            return f"Error: Cheatsheet '{cheatsheet}' not found.\n\n{available}"

    return cheatsheet_extractors[cheatsheet].get_full_content()
