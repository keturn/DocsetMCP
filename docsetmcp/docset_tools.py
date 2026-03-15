import sqlite3
from typing import Union

from docsetmcp.server import MatchedDocsetInfo, extractors, mcp
from docsetmcp.types import DocsetInfo


@mcp.tool()
def search_docs(
    query: str,
    docset: str,
    language: str | None = None,
    max_results: int = 3,
) -> str:
    """
    Search and extract documentation from Dash docsets by EXACT NAME MATCHING.

    IMPORTANT: This tool searches for EXACT NAMES of documentation entries, NOT keyword search.
    Only use this when you know the specific name of a class, function, framework, or API.
    For discovery, use list_types and list_entries tools first.

    Search behavior:
    - Exact matches first (e.g., 'CarPlay' → CarPlay framework)
    - Prefix matches second (e.g., 'CarPlay' → 'carPlaySetting')
    - Substring matches last (e.g., 'CarPlay' → 'allowInCarPlay')

    Args:
        query: EXACT NAME of the documentation entry to find
               Examples: 'CarPlay', 'UIViewController', 'readFile', 'ModelContext'
               NOT keywords like 'file handling' or 'image processing'
        docset: Docset to search in (e.g., 'apple_api_reference', 'nodejs', 'bash')
        language: Programming language variant (optional, varies by docset)
                  For Apple docs: 'swift' or 'objc'
        max_results: Maximum number of results to return (1-10, default: 3)

    For discovery/exploration:
    - Use list_types(docset, language) to see available types (Class, Protocol, etc.)
    - Use list_entries(docset, type_name, language, name_filter) to browse entries by type
    - Use list_frameworks(docset, filter) to find frameworks containing keywords

    Returns:
        Formatted Markdown documentation with exact matches prioritized.
        Container types (frameworks, classes) include drilldown notes for exploring members.
    """
    if docset not in extractors:
        available = list(extractors.keys())
        return f"Error: docset '{docset}' not available. Available: {available}"

    extractor = extractors[docset]

    if not 1 <= max_results <= 10:
        return "Error: max_results must be between 1 and 10"

    # Use docset-specific default language if none provided
    if language is None:
        # Get the first configured language as default
        config = extractor.config
        if "languages" in config and config["languages"]:
            language = next(iter(config["languages"]))
        else:
            language = "swift"  # Fallback for compatibility

    return extractor.search(query, language, max_results)


@mcp.tool()
def list_available_docsets() -> str:
    """
    List all available docsets with detailed information for easy querying.

    This tool provides a comprehensive list of all installed docsets including:
    - Docset identifier (use this for the 'docset' parameter)
    - Full name and description
    - Supported languages
    - Example query command

    Returns:
        Formatted list of available docsets with usage examples
    """
    if not extractors:
        return (
            "No docsets are currently available. Please check your Dash installation."
        )

    lines = ["# Available Dash Docsets\n"]
    lines.append("Use these docset identifiers with the `search_docs` tool:\n")

    for docset_id, extractor in sorted(extractors.items()):
        config = extractor.config
        languages = list(config.get("languages", {}).keys())
        lang_str = (
            ", ".join(f"`{lang}`" for lang in languages)
            if languages
            else "no languages"
        )

        lines.append(f"## {config.get('name', docset_id)}")

        if "description" in config:
            lines.append(f"*{config['description']}*\n")

        lines.append(f"- **Docset ID:** `{docset_id}`")
        lines.append(f"- **Languages:** {lang_str}")

        # Add example query
        default_lang = languages[0] if languages else None
        if default_lang:
            lines.append(
                f'- **Example:** `search_docs("YourQuery", docset="{docset_id}", language="{default_lang}")`'
            )
        else:
            lines.append(
                f'- **Example:** `search_docs("YourQuery", docset="{docset_id}")`'
            )

        lines.append("")  # Empty line between docsets

    return "\n".join(lines)


@mcp.tool()
def list_frameworks(docset: str, filter: str | None = None) -> str:
    """
    List available frameworks/types in a specific docset.

    Args:
        docset: Docset to list from (e.g., 'nodejs', 'python_3', 'bash')
        filter: Optional filter for framework/type names

    Returns:
        List of available frameworks or types
    """
    if docset not in extractors:
        available = list(extractors.keys())
        return f"Error: docset '{docset}' not available. Available: {available}"

    return extractors[docset].list_frameworks(filter)


@mcp.tool()
def list_languages() -> str:
    """
    List all programming languages with available documentation and descriptions.

    This tool provides a comprehensive overview of all supported languages,
    their associated docsets, and descriptions to help you find the right documentation.

    Returns:
        Detailed list of languages with docsets, descriptions, and usage examples
    """
    if not extractors:
        return (
            "No docsets are currently available. Please check your Dash installation."
        )

    # Group docsets by language
    language_map: dict[str, list[DocsetInfo]] = {}

    for docset_type, extractor in extractors.items():
        config = extractor.config

        # Get the primary language(s) for this docset
        primary_lang = config.get("primary_language")
        if primary_lang is not None:
            lang = primary_lang
            if lang not in language_map:
                language_map[lang] = []
            language_map[lang].append(
                {
                    "docset": docset_type,
                    "name": config["name"],
                    "languages": list(config["languages"].keys()),
                    "description": config.get("description"),
                }
            )
        else:
            # Infer from docset name or type
            name = config["name"].lower()
            if "javascript" in name or "js" in name:
                lang = "JavaScript"
            elif "typescript" in name:
                lang = "TypeScript"
            elif "python" in name:
                lang = "Python"
            elif "ruby" in name:
                lang = "Ruby"
            elif "java" in name and "javascript" not in name:
                lang = "Java"
            elif "bash" in name or "shell" in name:
                lang = "Shell"
            elif "sql" in name:
                lang = "SQL"
            elif name in ["c", "c++"]:
                lang = name.upper()
            elif "swift" in name or "apple" in name:
                lang = "Swift"
            elif "html" in name:
                lang = "HTML"
            elif "css" in name:
                lang = "CSS"
            elif "docker" in name:
                lang = "Docker"
            elif "react" in name:
                lang = "React"
            elif "vue" in name:
                lang = "Vue"
            else:
                # Use the docset name as language
                lang = config["name"]

            if lang not in language_map:
                language_map[lang] = []
            language_map[lang].append(
                {
                    "docset": docset_type,
                    "name": config["name"],
                    "languages": (
                        list(config["languages"].keys())
                        if "languages" in config
                        else []
                    ),
                    "description": config.get("description"),
                }
            )

    # Format output
    lines = ["# Available Languages and Their Documentation\n"]
    lines.append(
        "Explore documentation by language, then drill down into specific docsets and types.\n"
    )

    for lang in sorted(language_map.keys()):
        docsets = language_map[lang]
        lines.append(f"## {lang}")
        lines.append(f"*{len(docsets)} docset(s) available*\n")

        for ds in docsets:
            lines.append(f"### {ds['name']}")

            # Add description if available
            if ds.get("description"):
                lines.append(f"*{ds['description']}*\n")

            lines.append(f"- **Docset ID:** `{ds['docset']}`")

            # Show language variants if available
            if ds["languages"]:
                lang_str = ", ".join(f"`{l}`" for l in ds["languages"])
                lines.append(f"- **Language variants:** {lang_str}")

            # Add example commands
            lines.append("\n**Quick start commands:**")
            lines.append(f"```")
            lines.append(f"# List all types in this docset")
            lines.append(f"list_types(\"{ds['docset']}\")")
            if ds["languages"]:
                lines.append(f"\n# List types for specific language")
                lines.append(
                    f"list_types(\"{ds['docset']}\", language=\"{ds['languages'][0]}\")"
                )
            lines.append(f"\n# Search for specific documentation")
            lines.append(f"search_docs(\"YourQuery\", docset=\"{ds['docset']}\")")
            lines.append(f"```")
            lines.append("")

        lines.append("---\n")

    lines.append(
        f"**Summary:** {len(language_map)} languages, {len(extractors)} docsets total"
    )
    lines.append("\n**Next steps:**")
    lines.append('1. Use `list_types("docset_id")` to explore documentation types')
    lines.append(
        '2. Use `list_entries("docset_id", type="TypeName")` to browse entries'
    )
    lines.append("3. Use `search_docs()` to find specific documentation")

    return "\n".join(lines)


@mcp.tool()
def list_docsets_by_language(language: str) -> str:
    """
    Find all docsets that provide documentation for a specific programming language.

    This tool helps you find relevant documentation for a specific language,
    returning ready-to-use examples for querying.

    Args:
        language: The programming language to search for (e.g., 'python', 'javascript', 'swift')

    Returns:
        Formatted list of docsets with usage examples for the specified language
    """
    if not extractors:
        return (
            "No docsets are currently available. Please check your Dash installation."
        )

    language_lower = language.lower()
    matching_docsets: list[tuple[str, MatchedDocsetInfo]] = []

    for docset_type, extractor in extractors.items():
        config = extractor.config
        name_lower = config["name"].lower()

        # Check various ways a docset might be related to the language
        matches = False
        matched_lang = None

        # Direct name match
        if language_lower in name_lower:
            matches = True
            # Get the first available language variant
            if "languages" in config:
                matched_lang = next(iter(config["languages"].keys()))

        # Check language variants
        elif "languages" in config:
            for lang_key in config["languages"].keys():
                if language_lower in lang_key.lower():
                    matches = True
                    matched_lang = lang_key
                    break

        # Special cases
        elif language_lower in ["js", "javascript"] and (
            "javascript" in name_lower or "js" in name_lower or "node" in name_lower
        ):
            matches = True
        elif language_lower in ["ts", "typescript"] and "typescript" in name_lower:
            matches = True
        elif language_lower == "shell" and (
            "bash" in name_lower or "shell" in name_lower
        ):
            matches = True
        elif language_lower == "objective-c" and "apple" in name_lower:
            matches = True
        elif language_lower in ["swift", "swiftui"] and "apple" in name_lower:
            matches = True

        if matches:
            matched_info: MatchedDocsetInfo = {
                "config": config,
                "matched_lang": matched_lang,
            }
            matching_docsets.append((docset_type, matched_info))

    if not matching_docsets:
        return f"No docsets found for language '{language}'. Try 'list_languages' to see available options."

    # Format output
    lines = [f"# Docsets for {language.title()}\n"]
    lines.append("Use these with the `search_docs` tool:\n")

    for docset_id, info in matching_docsets:
        config = info["config"]
        matched_lang = info["matched_lang"]

        lines.append(f"## {config['name']}")

        if config.get("description"):
            lines.append(f"*{config['description']}*\n")

        lines.append(f"- **Docset ID:** `{docset_id}`")

        if "languages" in config:
            lang_str = ", ".join(f"`{lang}`" for lang in config["languages"].keys())
            lines.append(f"- **Languages:** {lang_str}")

        # Show the example with the matched language if available
        if matched_lang:
            lines.append(
                f'- **Example:** `search_docs("YourQuery", docset="{docset_id}", language="{matched_lang}")`'
            )
        elif "languages" in config and config["languages"]:
            default_lang = next(iter(config["languages"].keys()))
            lines.append(
                f'- **Example:** `search_docs("YourQuery", docset="{docset_id}", language="{default_lang}")`'
            )
        else:
            lines.append(
                f'- **Example:** `search_docs("YourQuery", docset="{docset_id}")`'
            )

        lines.append("")

    lines.append(f"Found {len(matching_docsets)} docset(s) for {language}")

    return "\n".join(lines)


@mcp.tool()
def list_types(docset: str, language: str | None = None) -> str:
    """
    List all documentation types available in a docset with examples.

    This shows the hierarchy of documentation types (e.g., Class, Method, Function)
    available in a docset, with example entries for each type.

    Args:
        docset: Docset identifier (e.g., 'apple_api_reference', 'nodejs')
        language: Optional language filter (e.g., 'swift', 'objc')

    Returns:
        List of types with example entries and counts
    """
    if docset not in extractors:
        available = list(extractors.keys())
        return f"Error: docset '{docset}' not available. Available: {available}"

    extractor = extractors[docset]
    config = extractor.config

    # Get the database connection
    conn = sqlite3.connect(extractor.optimized_db)
    cursor = conn.cursor()

    # Build language filter if specified
    lang_filter = ""
    if language:
        if language not in config.get("languages", {}):
            return f"Error: language '{language}' not available for {config['name']}. Available: {list(config.get('languages', {}).keys())}"
        lang_filter = config["languages"][language]["filter"]

    # Get type counts and examples
    lines = [f"# Documentation Types in {config['name']}"]
    if language:
        lines.append(f"*Filtered by language: {language}*\n")
    else:
        lines.append("")

    # Query for types with counts
    if lang_filter:
        cursor.execute(
            """
            SELECT type, COUNT(*) as count
            FROM searchIndex
            WHERE path LIKE ?
            GROUP BY type
            ORDER BY count DESC
        """,
            (f"%{lang_filter}%",),
        )
    else:
        cursor.execute("""
            SELECT type, COUNT(*) as count
            FROM searchIndex
            GROUP BY type
            ORDER BY count DESC
        """)

    type_counts = cursor.fetchall()

    if not type_counts:
        conn.close()
        return f"No types found in {config['name']}" + (
            f" for language {language}" if language else ""
        )

    for doc_type, count in type_counts:
        lines.append(f"## {doc_type} ({count:,} entries)")

        # Get 3 examples for this type
        if lang_filter:
            cursor.execute(
                """
                SELECT name
                FROM searchIndex
                WHERE type = ? AND path LIKE ?
                ORDER BY LENGTH(name), name
                LIMIT 3
            """,
                (doc_type, f"%{lang_filter}%"),
            )
        else:
            cursor.execute(
                """
                SELECT name
                FROM searchIndex
                WHERE type = ?
                ORDER BY LENGTH(name), name
                LIMIT 3
            """,
                (doc_type,),
            )

        examples = cursor.fetchall()
        if examples:
            lines.append("Examples:")
            for (name,) in examples:
                lines.append(f"- `{name}`")
        lines.append("")

    # Add usage hint
    lines.append("---")
    usage_hint = f'Use `list_entries(docset="{docset}", type="TypeName"'
    if language:
        usage_hint += f', language="{language}"'
    usage_hint += ")` to see all entries of a specific type."
    lines.append(usage_hint)

    conn.close()
    return "\n".join(lines)


@mcp.tool()
def list_entries(
    docset: str,
    type: str | None = None,
    language: str | None = None,
    starts_with: str | None = None,
    contains: str | None = None,
    max_results: int = 50,
) -> str:
    """
    List documentation entries with flexible filtering options.

    This tool allows you to browse documentation entries with various filters
    to find exactly what you're looking for.

    Args:
        docset: Docset identifier (e.g., 'apple_api_reference', 'nodejs')
        type: Filter by documentation type (e.g., 'Class', 'Method', 'Function')
        language: Filter by language (e.g., 'swift', 'objc')
        starts_with: Filter entries starting with this prefix (e.g., 'UI', 'NS')
        contains: Filter entries containing this substring
        max_results: Maximum results to return (1-200, default 50)

    Returns:
        List of matching documentation entries
    """
    if docset not in extractors:
        available = list(extractors.keys())
        return f"Error: docset '{docset}' not available. Available: {available}"

    if not 1 <= max_results <= 200:
        return "Error: max_results must be between 1 and 200"

    extractor = extractors[docset]
    config = extractor.config

    # Build query conditions
    conditions: list[str] = []
    params: list[Union[str, int]] = []

    if type:
        conditions.append("type = ?")
        params.append(type)

    if language and language in config.get("languages", {}):
        lang_filter = config["languages"][language]["filter"]
        conditions.append("path LIKE ?")
        params.append(f"%{lang_filter}%")

    if starts_with:
        conditions.append("name LIKE ?")
        params.append(f"{starts_with}%")

    if contains:
        conditions.append("name LIKE ?")
        params.append(f"%{contains}%")

    # Build the query
    where_clause = " AND ".join(conditions) if conditions else "1=1"

    conn = sqlite3.connect(extractor.optimized_db)
    cursor = conn.cursor()

    cursor.execute(
        f"""
        SELECT name, type
        FROM searchIndex
        WHERE {where_clause}
        ORDER BY name
        LIMIT ?
    """,
        params + [max_results],
    )

    results = cursor.fetchall()
    conn.close()

    if not results:
        filters: list[str] = []
        if type:
            filters.append(f"type={type}")
        if language:
            filters.append(f"language={language}")
        if starts_with:
            filters.append(f"starts_with={starts_with}")
        if contains:
            filters.append(f"contains={contains}")
        return (
            f"No entries found in {config['name']} with filters: {', '.join(filters)}"
        )

    # Format output
    lines = [f"# Documentation Entries in {config['name']}"]

    # Show active filters
    if type or language or starts_with or contains:
        lines.append("\nActive filters:")
        if type:
            lines.append(f"- Type: {type}")
        if language:
            lines.append(f"- Language: {language}")
        if starts_with:
            lines.append(f"- Starts with: {starts_with}")
        if contains:
            lines.append(f"- Contains: {contains}")
        lines.append("")

    # Group by type if not filtering by type
    if not type:
        from collections import defaultdict

        by_type: defaultdict[str, list[str]] = defaultdict(list)
        for name, doc_type in results:
            by_type[doc_type].append(name)

        for doc_type, names in sorted(by_type.items()):
            lines.append(f"## {doc_type} ({len(names)})")
            for name in names[:10]:  # Show first 10 of each type
                lines.append(f"- `{name}`")
            if len(names) > 10:
                lines.append(f"- ... and {len(names) - 10} more")
            lines.append("")
    else:
        # Just list all entries
        lines.append(f"## {type} entries ({len(results)})\n")
        for name, _ in results:
            lines.append(f"- `{name}`")

    lines.append("\n---")
    lines.append(f"Showing {len(results)} of {max_results} max results.")
    search_hint = f'Use `search_docs("{results[0][0]}", docset="{docset}"'
    if language:
        search_hint += f', language="{language}"'
    search_hint += ")` to see full documentation."
    lines.append(search_hint)

    return "\n".join(lines)
