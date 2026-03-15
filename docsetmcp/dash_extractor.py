from docsetmcp.types import AppleDocumentation, ContentItem, ProcessedDocsetConfig


import brotli


import base64
import hashlib
import os
import sqlite3
import tarfile
from pathlib import Path


class DashExtractor:
    config: ProcessedDocsetConfig

    def __init__(self, docset_type: str, docsets_base_path: str | None = None):
        # Load docset configuration using new config loader
        from docsetmcp.config_loader import ConfigLoader

        loader = ConfigLoader()

        try:
            self.config = loader.load_config(docset_type)
        except FileNotFoundError:
            raise ValueError(f"Unsupported docset type: {docset_type}")

        # Build list of paths to search for docsets
        search_paths: list[str] = []

        # Use custom docset location if provided, otherwise use configured paths
        if docsets_base_path:
            search_paths.append(os.path.expanduser(docsets_base_path))
        else:
            # Check environment variable for custom location
            env_path = os.getenv("DOCSET_PATH")
            if env_path:
                search_paths.append(os.path.expanduser(env_path))

            # Add additional paths from global config
            from docsetmcp.server import docsetmcp_config

            if docsetmcp_config.additional_docset_paths:
                additional_paths = docsetmcp_config.parse_path_list(
                    docsetmcp_config.additional_docset_paths
                )
                search_paths.extend(additional_paths)

            # If no custom paths specified, use default Dash location
            if not search_paths:
                search_paths.append(
                    os.path.expanduser("~/Library/Application Support/Dash/DocSets")
                )

        # Find the docset in the search paths
        self.docset: Path | None = None
        for search_path in search_paths:
            potential_docset = Path(search_path) / self.config["docset_path"]
            if potential_docset.exists():
                self.docset = potential_docset
                break

        # If not found, default to first search path for error reporting
        if self.docset is None:
            self.docset = Path(search_paths[0]) / self.config["docset_path"]
        # Set up paths based on docset format
        if self.config["format"] == "apple":
            self.fs_dir = self.docset / "Contents/Resources/Documents/fs"
            self.optimized_db = self.docset / "Contents/Resources/optimizedIndex.dsidx"
            self.cache_db = self.docset / "Contents/Resources/Documents/cache.db"
            # Cache for decompressed fs files
            self.fs_cache: dict[int, bytes] = {}
        elif self.config["format"] == "tarix":
            self.optimized_db = self.docset / "Contents/Resources/optimizedIndex.dsidx"
            self.tarix_archive = self.docset / "Contents/Resources/tarix.tgz"
            self.tarix_index = self.docset / "Contents/Resources/tarixIndex.db"
            # Cache for extracted HTML content
            self.html_cache: dict[str, str] = {}

        # Check if docset exists
        if not self.docset.exists():
            raise FileNotFoundError(
                f"{self.config['name']} docset not found at {self.docset}. "
                "Please ensure the docset is available at the configured location."
            )

    def _normalize_query(self, query: str) -> list[str]:
        """Normalize query for better matching"""
        # Remove extra spaces and convert to consistent format
        normalized = " ".join(query.split())
        # Also create a no-space version for cases like "App Intent" -> "AppIntent"
        no_spaces = normalized.replace(" ", "")
        # Return unique variations
        variations = [query]
        if normalized != query:
            variations.append(normalized)
        if no_spaces != query and no_spaces != normalized:
            variations.append(no_spaces)
        return variations

    def _get_type_order_clause(self) -> str:
        """Generate SQL CASE clause for type ordering based on config"""
        if "types" not in self.config or not self.config["types"]:
            return "0"  # No ordering if types not configured

        case_parts = ["CASE type"]
        # types is a dict mapping type_name -> priority_index
        for type_name, priority in self.config["types"].items():
            case_parts.append(f"    WHEN '{type_name}' THEN {priority}")
        case_parts.append(f"    ELSE {len(self.config['types'])}")
        case_parts.append("END")
        return "\n".join(case_parts)

    def search(self, query: str, language: str = "swift", max_results: int = 3) -> str:
        """Search for Apple API documentation"""
        # Search the optimized index
        conn = sqlite3.connect(self.optimized_db)
        cursor = conn.cursor()

        # Filter by language using config
        if language not in self.config["languages"]:
            return f"Error: language must be one of {list(self.config['languages'].keys())}"

        lang_config = self.config["languages"][language]
        lang_filter = lang_config["filter"]

        db_results = []
        query_variations = self._normalize_query(query)

        # Get dynamic type ordering
        type_order = self._get_type_order_clause()

        # Get top-level types from configuration
        if "types" in self.config and self.config["types"]:
            # Sort types by their priority value and take the first few
            sorted_types = sorted(self.config["types"].items(), key=lambda x: x[1])
            top_types = [type_name for type_name, _ in sorted_types[:5]]
        else:
            # If no types configured, we can't filter by type
            top_types = []

        type_list = ", ".join(f"'{t}'" for t in top_types) if top_types else "''"

        # Collect all results, not just from first successful query
        all_results: list[tuple[str, str, str]] = []
        seen_entries: set[tuple[str, str]] = (
            set()
        )  # Track (name, type) to avoid duplicates

        # Try exact match with all query variations (case-insensitive)
        for q in query_variations:
            cursor.execute(
                f"""
                SELECT name, type, path
                FROM searchIndex
                WHERE name = ? COLLATE NOCASE AND path LIKE ?
                ORDER BY {type_order}
                LIMIT ?
            """,
                (q, f"%{lang_filter}%", max_results),
            )
            for row in cursor.fetchall():
                key = (row[0], row[1])
                if key not in seen_entries:
                    all_results.append(row)
                    seen_entries.add(key)
            if len(all_results) >= max_results:
                break

        # If we need more results, try framework-level entries without language filter
        if len(all_results) < max_results:
            for q in query_variations:
                cursor.execute(
                    f"""
                    SELECT name, type, path
                    FROM searchIndex
                    WHERE name = ? COLLATE NOCASE
                    AND type IN ({type_list})
                    AND (path LIKE '%/documentation/%' OR path LIKE '%request_key=%')
                    ORDER BY {type_order}
                    LIMIT ?
                """,
                    (q, max_results - len(all_results)),
                )
                for row in cursor.fetchall():
                    key = (row[0], row[1])
                    if key not in seen_entries:
                        all_results.append(row)
                        seen_entries.add(key)
                if len(all_results) >= max_results:
                    break

        # Check if we found an exact match in the results
        found_exact_match: bool = False
        exact_match_name: str | None = None
        exact_match_path: str | None = None
        exact_match_type: str | None = None

        for row in all_results:
            if len(row) >= 3 and row[0].lower() == query.lower():
                found_exact_match = True
                exact_match_name = row[0]
                exact_match_type = row[1]
                exact_match_path = row[2]
                break

        # Track additional members count
        additional_members = 0

        # Count total members for exact matches to show in the note
        if found_exact_match and exact_match_name and exact_match_path:
            # Extract the documentation path pattern
            doc_path_pattern = ""
            if "/documentation/" in exact_match_path:
                doc_path = (
                    exact_match_path.split("/documentation/")[1]
                    .split("?")[0]
                    .split("#")[0]
                )
                doc_path_pattern = f"%/documentation/{doc_path}/%"

            if doc_path_pattern:
                # Count total members for the note (but don't include them in results)
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM searchIndex
                    WHERE path LIKE ?
                    AND path LIKE ?
                    AND name != ?
                """,
                    (doc_path_pattern, f"%{lang_filter}%", exact_match_name),
                )
                total_count = cursor.fetchone()
                if total_count:
                    additional_members = total_count[0]

        # If we still need more results, try broader search
        if len(all_results) < max_results:
            cursor.execute(
                f"""
                SELECT name, type, path,
                    CASE
                        WHEN name = ? COLLATE NOCASE THEN 0
                        WHEN type IN ({type_list}) AND name = ? COLLATE NOCASE THEN 1
                        WHEN name LIKE ? COLLATE NOCASE THEN 2
                        WHEN type IN ({type_list}) AND name LIKE ? COLLATE NOCASE THEN 3
                        ELSE 4
                    END as rank
                FROM searchIndex
                WHERE name LIKE ? COLLATE NOCASE
                AND (
                    (path LIKE ? AND path LIKE ?)  -- Has language filter
                    OR (type IN ({type_list}) AND (path LIKE '%/documentation/%' OR path LIKE '%request_key=%'))  -- Or is framework without language
                )
                ORDER BY rank, {type_order}, LENGTH(name)
                LIMIT ?
            """,
                (
                    query,
                    query,
                    f"{query}%",
                    f"{query}%",
                    f"%{query}%",
                    f"%{lang_filter}%",
                    f"%{lang_filter}%",
                    max_results * 2,
                ),
            )
            for row in cursor.fetchall():
                if len(all_results) >= max_results:
                    break
                key = (row[0], row[1])
                if key not in seen_entries:
                    all_results.append(row)
                    seen_entries.add(key)

        conn.close()

        # Use all_results instead of db_results
        db_results: list[tuple[str, str, str]] = all_results[:max_results]

        if not db_results:
            return f"No matches found for '{query}' in {language} documentation"

        # Extract documentation for each result
        results: list[str] = []
        for row in db_results[:max_results]:
            name, doc_type, path, *_ = row
            if self.config["format"] == "apple":
                if "request_key=" in path:
                    request_key: str = path.split("request_key=")[1].split("#")[0]
                    # Remove any language parameter from request_key
                    if "&" in request_key:
                        request_key = request_key.split("&")[0]

                    # If path contains language parameter, use that instead
                    path_language: str = language
                    if "&language=" in path:
                        path_language = (
                            path.split("&language=")[1].split("&")[0].split("#")[0]
                        )

                    doc = self._extract_by_request_key(request_key, path_language)

                    if doc:
                        markdown = self._format_as_markdown(doc, name, doc_type)

                        # Add member note if this is the exact match and has members
                        if (
                            found_exact_match
                            and name == exact_match_name
                            and doc_type == exact_match_type
                            and additional_members > 0
                        ):
                            type_note = f"\n\n**Note:** The {exact_match_name} {doc_type.lower()} contains {additional_members} additional members not shown. Use `search_docs('{exact_match_name}', language='{language}', max_results=50)` to see all {exact_match_name} members."
                            markdown += type_note

                        results.append(markdown)
            elif self.config["format"] == "tarix":
                # Extract HTML content from tarix archive
                html_content = self._extract_from_tarix(path)
                if html_content:
                    markdown = self._format_html_as_markdown(
                        html_content, name, doc_type, path
                    )

                    # Add member note if this is the exact match and has members
                    if (
                        found_exact_match
                        and name == exact_match_name
                        and doc_type == exact_match_type
                        and additional_members > 0
                    ):
                        type_note = f"\n\n**Note:** The {exact_match_name} {doc_type.lower()} contains {additional_members} additional members not shown. Use `search_docs('{exact_match_name}', language='{language}', max_results=50)` to see all {exact_match_name} members."
                        markdown += type_note

                    results.append(markdown)

        # Handle different result counts appropriately
        if results:
            if len(results) == 1:
                # Single result: return full content
                return results[0]
            elif 2 <= len(results) <= 5:
                # 2-5 results: return summaries with option to search individually
                summaries: list[str] = []
                for i, full_content in enumerate(results, 1):
                    lines = full_content.split("\n")
                    # Get title and key info
                    title = lines[0] if lines else f"Result {i}"
                    summary_lines = [f"{i}. {title}"]

                    # Add type and framework info
                    for line in lines[1:10]:
                        if line.startswith("**Type:**") or line.startswith(
                            "**Framework:**"
                        ):
                            summary_lines.append(f"   {line}")

                    # Add first line of summary if available
                    for j, line in enumerate(lines):
                        if line == "## Summary" and j + 2 < len(lines):
                            summary_text = lines[j + 2]
                            if len(summary_text) > 100:
                                summary_text = summary_text[:100] + "..."
                            summary_lines.append(f"   {summary_text}")
                            break

                    summaries.append("\n".join(summary_lines))

                header = f"Found {len(results)} results for '{query}':\n\n"
                footer = (
                    "\n\nSearch for each item individually to see full documentation."
                )
                return header + "\n\n".join(summaries) + footer
            elif len(results) <= 100:
                # 6-100 results: return full content with separators
                return "\n\n---\n\n".join(results)
            else:
                # More than 100: show count and suggest refinement
                # In future, could implement pagination here
                entry_list: list[str] = []
                for full_content in results[:100]:
                    lines = full_content.split("\n")
                    title = lines[0].replace("# ", "") if lines else "Unknown"
                    doc_type = "Unknown"
                    framework = ""
                    for line in lines[1:5]:
                        if line.startswith("**Type:**"):
                            doc_type = line.replace("**Type:** ", "")
                        elif line.startswith("**Framework:**"):
                            framework = f" - {line.replace('**Framework:** ', '')}"
                    entry_list.append(f"- {title} ({doc_type}{framework})")

                header = f"Found {len(results)} results for '{query}' (showing first 100):\n\n"
                footer = f"\n\nToo many results ({len(results)}). Consider refining your search or using list_entries() with filters."
                return header + "\n".join(entry_list) + footer

        # No results extracted
        if not db_results:
            return f"No matches found for '{query}' in {language} documentation"

        # Found entries but couldn't extract
        entries_info: list[str] = []
        for name, doc_type, *_ in db_results[:10]:  # Show up to 10 entries found
            entries_info.append(f"- {name} ({doc_type})")

        return f"""Found entries for '{query}' but couldn't extract documentation. The content may not be in the offline cache.

Found but couldn't extract:
{chr(10).join(entries_info)}

Try opening Dash and ensuring the '{self.config['name']}' docset is fully downloaded."""

    def list_frameworks(self, filter_text: str | None = None) -> str:
        """List available frameworks/modules"""
        conn = sqlite3.connect(self.optimized_db)
        cursor = conn.cursor()

        if self.config["format"] == "apple" and self.config.get("framework_pattern"):
            framework_pattern = self.config["framework_pattern"]

            if "documentation/" in framework_pattern:
                query = """
                    SELECT DISTINCT
                        SUBSTR(path,
                            INSTR(path, 'documentation/') + 14,
                            INSTR(SUBSTR(path, INSTR(path, 'documentation/') + 14), '/') - 1
                        ) as framework
                    FROM searchIndex
                    WHERE path LIKE '%documentation/%'
                """
            else:
                # Fallback to generic pattern matching
                query = f"""
                    SELECT DISTINCT path
                    FROM searchIndex
                    WHERE path LIKE '%{framework_pattern}%'
                    LIMIT 100
                """

            if filter_text:
                query = query.replace(
                    "WHERE", f"WHERE framework LIKE '%{filter_text}%' AND"
                )

            cursor.execute(query)

            if "documentation/" in framework_pattern:
                frameworks = [row[0] for row in cursor.fetchall() if row[0]]
            else:
                # Extract framework names from paths manually
                paths = [row[0] for row in cursor.fetchall()]
                frameworks: list[str] = []
                import re

                pattern_regex = framework_pattern.replace("([^/]+)", "([^/]+)")
                for path in paths:
                    match = re.search(pattern_regex, path)
                    if match and match.group(1):
                        frameworks.append(match.group(1))

            # Remove duplicates and empty strings
            frameworks = sorted(set(f for f in frameworks if f))

            label = "frameworks"
        else:
            # For other docsets, just list available types
            query = "SELECT DISTINCT type FROM searchIndex ORDER BY type"
            cursor.execute(query)
            frameworks = [row[0] for row in cursor.fetchall() if row[0]]
            label = "types"

        conn.close()

        if filter_text:
            return f"{label.title()} matching '{filter_text}':\n" + "\n".join(
                f"- {f}" for f in frameworks if filter_text.lower() in f.lower()
            )
        else:
            return f"Available {label} ({len(frameworks)} total):\n" + "\n".join(
                f"- {f}" for f in frameworks
            )

    def _extract_by_request_key(
        self, request_key: str, language: str = "swift"
    ) -> AppleDocumentation | None:
        """Extract documentation using request key and SHA-1 encoding"""
        # Convert request_key to canonical path
        if request_key.startswith("ls/"):
            canonical_path = "/" + request_key[3:]
        else:
            canonical_path = "/" + request_key

        # Calculate UUID using SHA-1
        sha1_hash = hashlib.sha1(canonical_path.encode("utf-8")).digest()
        truncated = sha1_hash[:6]
        suffix = base64.urlsafe_b64encode(truncated).decode().rstrip("=")

        # Language prefix from config
        lang_config = self.config["languages"][language]
        prefix = lang_config["prefix"]
        uuid = prefix + suffix

        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT data_id, offset, length
            FROM refs
            WHERE uuid = ?
        """,
            (uuid,),
        )

        result = cursor.fetchone()
        conn.close()

        if result:
            data_id, offset, length = result
            return self._extract_from_fs(data_id, offset, length)

        return None

    def _extract_from_fs(
        self, data_id: int, offset: int, length: int
    ) -> AppleDocumentation | None:
        """Extract JSON from fs file at specific offset"""
        fs_file = self.fs_dir / str(data_id)

        if not fs_file.exists():
            return None

        try:
            # Load and cache decompressed data
            if data_id not in self.fs_cache:
                with open(fs_file, "rb") as f:
                    compressed = f.read()
                self.fs_cache[data_id] = brotli.decompress(compressed)

            decompressed = self.fs_cache[data_id]

            # Extract JSON at offset
            json_data = decompressed[offset : offset + length]
            import json

            doc = json.loads(json_data)

            if "metadata" in doc:
                return doc

        except Exception:
            pass

        return None

    def _format_as_markdown(
        self, doc: AppleDocumentation, name: str, doc_type: str
    ) -> str:
        """Format documentation as Markdown"""
        lines: list[str] = []
        metadata = doc.get("metadata", {})

        # Title
        title = metadata.get("title", name)
        lines.append(f"# {title}")

        # Type
        lines.append(f"\n**Type:** {doc_type}")

        # Framework
        modules = metadata.get("modules", [])
        if modules:
            names = [m.get("name", "") for m in modules]
            lines.append(f"**Framework:** {', '.join(names)}")

        # Availability
        platforms = metadata.get("platforms", [])
        if platforms:
            avail: list[str] = []
            for p in platforms:
                platform_name = p.get("name", "")
                ver = p.get("introducedAt", "")
                if ver:
                    avail.append(f"{platform_name} {ver}+")
                else:
                    avail.append(platform_name)
            if avail:
                lines.append(f"**Available on:** {', '.join(avail)}")

        # Abstract/Summary
        abstract = doc.get("abstract", [])
        if abstract:
            text = self._extract_text(abstract)
            if text:
                lines.append(f"\n## Summary\n\n{text}")

        # Primary Content Sections
        sections = doc.get("primaryContentSections", [])
        for section in sections:
            kind = section.get("kind", "")

            if kind == "declarations":
                decls = section.get("declarations", [])
                if decls and decls[0].get("tokens"):
                    lines.append("\n## Declaration\n")
                    tokens = decls[0].get("tokens", [])
                    code = "".join(t.get("text", "") for t in tokens)
                    lang = decls[0].get("languages", ["swift"])[0]
                    lines.append(f"```{lang}\n{code}\n```")

            elif kind == "parameters":
                params = section.get("parameters", [])
                if params:
                    lines.append("\n## Parameters\n")
                    for param in params:
                        param_name = param.get("name", "")
                        param_content = param.get("content", [])
                        param_text = self._extract_text(param_content)
                        if param_name and param_text:
                            lines.append(f"- **{param_name}**: {param_text}")

            elif kind == "content":
                content = section.get("content", [])
                text = self._extract_text(content)
                if text:
                    lines.append(f"\n{text}")

            # Handle other section types as generic content
            elif "content" in section:
                content = section.get("content", [])
                text = self._extract_text(content)
                if text:
                    section_title = kind.replace("_", " ").title()
                    lines.append(f"\n## {section_title}\n\n{text}")

        # Discussion
        discussion = doc.get("discussionSections", [])
        if discussion:
            lines.append("\n## Discussion")
            for section in discussion:  # Get all discussion sections
                content = section.get("content", [])
                text = self._extract_text(content)
                if text:
                    lines.append(f"\n{text}")

        return "\n".join(lines)

    def _extract_text(self, content: list[ContentItem]) -> str:
        """Extract plain text from content"""
        parts: list[str] = []
        for item in content:
            t = item.get("type", "")
            if t == "text":
                parts.append(item.get("text", ""))
            elif t == "codeVoice":
                parts.append(f"`{item.get('code', '')}`")
            elif t == "paragraph":
                inline = item.get("inlineContent", [])
                parts.append(self._extract_text(inline))
            elif t == "reference":
                title = item.get("title", item.get("identifier", ""))
                parts.append(f"`{title}`")
        return " ".join(parts)

    def _extract_from_tarix(self, search_path: str) -> str | None:
        """Extract HTML content from tarix archive"""
        # Remove anchor from path
        clean_path = search_path.split("#")[0]

        # Handle special Dash metadata paths (like in C docset)
        if clean_path.startswith("<dash_entry_"):
            # Extract the actual file path from the end of the path
            # Format: <dash_entry_...>actual/file/path.html
            parts = clean_path.split(">")
            if len(parts) > 1:
                clean_path = parts[-1]  # Get the actual file path after the last >

        # Build full docset path
        # Extract docset folder name from docset_path (e.g., "NodeJS/NodeJS.docset" -> "NodeJS.docset")
        docset_folder = self.config["docset_path"].split("/")[-1]
        full_path = f"{docset_folder}/Contents/Resources/Documents/{clean_path}"

        # Check cache first
        if full_path in self.html_cache:
            return self.html_cache[full_path]

        try:
            # Query tarix index for file location
            conn = sqlite3.connect(self.tarix_index)
            cursor = conn.cursor()

            cursor.execute("SELECT hash FROM tarindex WHERE path = ?", (full_path,))
            result = cursor.fetchone()
            conn.close()

            if not result:
                return None

            # Validate hash format: "entry_number offset size"
            hash_parts = result[0].split()
            if len(hash_parts) != 3:
                return None

            # Extract file from tar archive
            with tarfile.open(self.tarix_archive, "r:gz") as tar:
                # Find the file by path name (entry_number doesn't seem to be sequential index)
                try:
                    target_member = tar.getmember(full_path)
                    extracted_file = tar.extractfile(target_member)
                    if extracted_file:
                        content = extracted_file.read().decode("utf-8", errors="ignore")
                        self.html_cache[full_path] = content
                        return content
                except KeyError:
                    # If exact path fails, try to find by name
                    target_file = full_path.split("/")[-1]  # Get just the filename
                    for member in tar.getmembers():
                        if (
                            member.name.endswith(target_file)
                            and clean_path in member.name
                        ):
                            extracted_file = tar.extractfile(member)
                            if extracted_file:
                                content = extracted_file.read().decode(
                                    "utf-8", errors="ignore"
                                )
                                self.html_cache[full_path] = content
                                return content

        except Exception:
            pass

        return None

    def _format_html_as_markdown(
        self, html_content: str, name: str, doc_type: str, path: str
    ) -> str:
        """Convert HTML documentation to Markdown"""
        lines: list[str] = []

        # Title
        lines.append(f"# {name}")

        # Type
        lines.append(f"\n**Type:** {doc_type}")

        # Path info
        lines.append(f"**Path:** {path}")

        # Try to extract key content from HTML
        # This is a simple text extraction - could be enhanced with proper HTML parsing
        import re

        # Remove HTML tags and extract text content
        text_content = re.sub(r"<[^>]+>", "", html_content)

        # Clean up whitespace
        text_content = re.sub(r"\s+", " ", text_content).strip()

        # Limit content length
        if len(text_content) > 2000:
            text_content = text_content[:2000] + "..."

        if text_content:
            lines.append(f"\n## Content\n\n{text_content}")

        return "\n".join(lines)
