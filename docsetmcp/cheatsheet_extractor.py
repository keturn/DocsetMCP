import os
import sqlite3
from pathlib import Path


class CheatsheetExtractor:
    """Extract content from Dash cheatsheets"""

    def __init__(self, name: str, cheatsheets_base_path: str | None = None):
        self.name = name

        # Build list of paths to search for cheatsheets
        search_paths: list[Path] = []

        # Use custom cheatsheet location if provided, otherwise use configured paths
        if cheatsheets_base_path:
            search_paths.append(Path(os.path.expanduser(cheatsheets_base_path)))
        else:
            # Check environment variable for custom location
            env_path = os.getenv("CHEATSHEET_PATH")
            if env_path:
                search_paths.append(Path(os.path.expanduser(env_path)))

            # Add additional paths from global config
            from docsetmcp.server import docsetmcp_config

            if docsetmcp_config.additional_cheatsheet_paths:
                additional_paths = docsetmcp_config.parse_path_list(
                    docsetmcp_config.additional_cheatsheet_paths
                )
                search_paths.extend([Path(p) for p in additional_paths])

            # If no custom paths specified, use default Dash location
            if not search_paths:
                search_paths.append(
                    Path(os.path.expanduser("~/Library/Application Support/Dash/Cheat Sheets"))
                )

        # Find the cheatsheet in the search paths
        self.cheatsheet_dir: Path | None = None
        for search_path in search_paths:
            self.cheatsheets_path = search_path  # Set for _find_cheatsheet_dir
            found_dir = self._find_cheatsheet_dir(name)
            if found_dir:
                self.cheatsheet_dir = found_dir
                break

        # If not found, default to first search path for error reporting
        if self.cheatsheet_dir is None:
            self.cheatsheets_path = search_paths[0]
            raise FileNotFoundError(f"Cheatsheet '{name}' not found")

        # Find the .docset within the directory
        docset_files = list(self.cheatsheet_dir.glob("*.docset"))
        if not docset_files:
            raise FileNotFoundError(f"No .docset found in {self.cheatsheet_dir}")

        self.docset = docset_files[0]
        self.db_path = self.docset / "Contents/Resources/docSet.dsidx"
        self.documents_path = self.docset / "Contents/Resources/Documents"

    def _find_cheatsheet_dir(self, name: str) -> Path | None:
        """Find cheatsheet directory using smart heuristics"""
        # Direct match
        direct_path = self.cheatsheets_path / name
        if direct_path.exists():
            return direct_path

        # Case-insensitive match
        for path in self.cheatsheets_path.iterdir():
            if path.is_dir() and path.name.lower() == name.lower():
                return path

        # Fuzzy match - contains the name
        for path in self.cheatsheets_path.iterdir():
            if path.is_dir() and name.lower() in path.name.lower():
                return path

        # Replace common separators and try again
        variations = [
            name.replace("-", " "),
            name.replace("_", " "),
            name.replace("-", ""),
            name.replace("_", ""),
            name.title(),
            name.upper(),
        ]

        for variant in variations:
            for path in self.cheatsheets_path.iterdir():
                if path.is_dir() and (
                    path.name.lower() == variant.lower() or variant.lower() in path.name.lower()
                ):
                    return path

        return None

    def get_categories(self) -> list[str]:
        """Get all categories from the cheatsheet database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT name
            FROM searchIndex
            WHERE type = 'Category'
            ORDER BY name
        """)

        categories = [row[0] for row in cursor.fetchall()]
        conn.close()

        return categories

    def get_category_content(self, category_name: str) -> str:
        """Get all entries from a specific category"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all entries for this category
        # The category is referenced in the path for entries
        # Need to handle URL encoding in the path
        import urllib.parse

        encoded_category = urllib.parse.quote(category_name)

        cursor.execute(
            """
            SELECT name, type, path
            FROM searchIndex
            WHERE (path LIKE ? OR path LIKE ?) AND type = 'Entry'
            ORDER BY name
        """,
            (f"%dash_ref_{category_name}/%", f"%dash_ref_{encoded_category}/%"),
        )

        entries = cursor.fetchall()
        conn.close()

        if not entries:
            return f"No entries found in category '{category_name}'"

        # Now extract the content from HTML for each entry
        html_path = self.documents_path / "index.html"

        if not html_path.exists():
            return f"No content file found for {self.name} cheatsheet"

        try:
            with open(html_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Build the result
            result: list[str] = [f"# {self.name} - {category_name}\n"]

            # Debug: show how many entries we're processing
            # result.append(f"_Processing {len(entries)} entries..._\n")

            for entry_name, _, entry_path in entries:
                # Find the specific entry in the HTML
                # Look for the table row with this entry's ID from the path
                entry_id = entry_path.split("#")[-1] if "#" in entry_path else None

                if entry_id:
                    # URL decode the entry_id since HTML uses spaces, not %20
                    import urllib.parse

                    entry_id = urllib.parse.unquote(entry_id)

                    # Also create version with & replaced by &amp; for HTML
                    entry_id_html = entry_id.replace("&", "&amp;")
                    # Find the table row with this ID
                    import re

                    # Pattern to find the specific entry
                    # Try multiple patterns since HTML might vary
                    patterns = [
                        rf"<tr[^>]*id='{re.escape(entry_id)}'[^>]*>(.*?)</tr>",
                        rf'<tr[^>]*id="{re.escape(entry_id)}"[^>]*>(.*?)</tr>',
                        rf"<tr[^>]*id=['\"]?{re.escape(entry_id)}['\"]?[^>]*>(.*?)</tr>",
                        # Also try with HTML-encoded ampersand
                        rf"<tr[^>]*id='{re.escape(entry_id_html)}'[^>]*>(.*?)</tr>",
                        rf'<tr[^>]*id="{re.escape(entry_id_html)}"[^>]*>(.*?)</tr>',
                    ]

                    tr_match = None
                    for pattern in patterns:
                        tr_match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
                        if tr_match:
                            break

                    if tr_match:
                        tr_html = tr_match.group(1)

                        # Extract the content from this row
                        result.append(f"\n## {entry_name}")

                        # Extract notes/content
                        notes_pattern = r'<div class=[\'"]notes[\'"]>(.*?)</div>'
                        notes_matches = re.findall(
                            notes_pattern, tr_html, re.DOTALL | re.IGNORECASE
                        )

                        # Also check for command column (like in Xcode cheatsheet)
                        command_pattern = r'<td class=[\'"]command[\'"]>.*?<code>(.*?)</code>'
                        command_match = re.search(
                            command_pattern, tr_html, re.DOTALL | re.IGNORECASE
                        )

                        if command_match:
                            # This is a command-style entry (like Xcode)
                            command = command_match.group(1).strip()
                            # Clean up HTML entities
                            command = (
                                command.replace("&lt;", "<")
                                .replace("&gt;", ">")
                                .replace("&amp;", "&")
                                .replace("&#39;", "'")
                                .replace("&quot;", '"')
                            )
                            result.append(f"```\n{command}\n```")

                        # Check if we have any non-empty notes
                        # has_content = False
                        # for notes in notes_matches:
                        #     if notes.strip():
                        #         has_content = True
                        #         break

                        for notes in notes_matches:
                            if not notes.strip():
                                continue

                            # Extract code blocks
                            code_pattern = r"<pre[^>]*>(.*?)</pre>"
                            code_matches = re.findall(
                                code_pattern, notes, re.DOTALL | re.IGNORECASE
                            )

                            # Replace code blocks with placeholders
                            temp_notes = notes
                            for idx, code in enumerate(code_matches):
                                temp_notes = re.sub(
                                    rf"<pre[^>]*>{re.escape(code)}</pre>",
                                    f"__CODE_{idx}__",
                                    temp_notes,
                                )

                            # Extract inline code
                            inline_code_pattern = r"<code[^>]*>(.*?)</code>"
                            inline_codes = re.findall(
                                inline_code_pattern, temp_notes, re.IGNORECASE
                            )

                            # Replace inline code with placeholders
                            for idx, code in enumerate(inline_codes):
                                temp_notes = re.sub(
                                    f"<code[^>]*>{re.escape(code)}</code>",
                                    f"__INLINE_{idx}__",
                                    temp_notes,
                                )

                            # Remove all HTML tags
                            text = re.sub(r"<[^>]+>", " ", temp_notes)

                            # Restore code blocks
                            for idx, code in enumerate(code_matches):
                                # Clean up HTML entities in code
                                code = (
                                    code.replace("&lt;", "<")
                                    .replace("&gt;", ">")
                                    .replace("&amp;", "&")
                                )
                                text = text.replace(f"__CODE_{idx}__", f"\n```\n{code}\n```\n")

                            # Restore inline code
                            for idx, code in enumerate(inline_codes):
                                code = (
                                    code.replace("&lt;", "<")
                                    .replace("&gt;", ">")
                                    .replace("&amp;", "&")
                                )
                                text = text.replace(f"__INLINE_{idx}__", f"`{code}`")

                            # Clean up whitespace
                            text = re.sub(r"\s+", " ", text).strip()
                            text = re.sub(
                                r"\s*\n\s*```", "\n```", text
                            )  # Clean code block formatting
                            text = re.sub(r"```\s*\n\s*", "```\n", text)

                            # Clean up remaining HTML entities
                            text = (
                                text.replace("&lt;", "<")
                                .replace("&gt;", ">")
                                .replace("&amp;", "&")
                                .replace("&#39;", "'")
                                .replace("&quot;", '"')
                            )

                            if text:
                                result.append(text)

            return "\n".join(result)

        except Exception as e:
            return f"Error extracting category content: {str(e)}"

    def search(self, query: str = "", category: str = "", max_results: int = 10) -> str:
        """Search cheatsheet entries"""
        # If no query and no category, return the full content
        if not query and not category:
            return self.get_full_content()

        # If only category is specified, return that category's content
        if category and not query:
            return self.get_category_content(category)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Build search query
        if query and category:
            # Search within a specific category
            cursor.execute(
                """
                SELECT name, type, path
                FROM searchIndex
                WHERE (name LIKE ? OR name = ?)
                AND path LIKE ?
                ORDER BY
                    CASE
                        WHEN name = ? THEN 0
                        WHEN name LIKE ? THEN 1
                        ELSE 2
                    END,
                    CASE type
                        WHEN 'Category' THEN 0
                        ELSE 1
                    END
                LIMIT ?
            """,
                (f"%{query}%", query, f"%{category}%", query, f"{query}%", max_results),
            )
        elif query:
            # General search
            cursor.execute(
                """
                SELECT name, type, path
                FROM searchIndex
                WHERE name LIKE ? OR name = ?
                ORDER BY
                    CASE
                        WHEN name = ? THEN 0
                        WHEN name LIKE ? THEN 1
                        ELSE 2
                    END,
                    CASE type
                        WHEN 'Category' THEN 0
                        ELSE 1
                    END
                LIMIT ?
            """,
                (f"%{query}%", query, query, f"{query}%", max_results),
            )
        else:
            # List all categories
            cursor.execute(
                """
                SELECT name, type, path
                FROM searchIndex
                WHERE type = 'Category'
                ORDER BY name
                LIMIT ?
            """,
                (max_results,),
            )

        results = cursor.fetchall()
        conn.close()

        if not results:
            return f"No results found in {self.name} cheatsheet"

        # Format results
        lines: list[str] = [f"# {self.name} Cheatsheet\n"]

        for name, entry_type, path in results:
            if entry_type == "Category":
                lines.append(f"\n## {name}")
            else:
                # Extract the actual content from HTML
                content = self._extract_entry_content(path, name)
                if content:
                    lines.append(f"\n### {name}")
                    lines.append(content)

        return "\n".join(lines)

    def _extract_entry_content(self, _path: str, name: str) -> str | None:
        """Extract entry content from HTML"""
        # For cheatsheets, the path is usually index.html with anchors
        html_path = self.documents_path / "index.html"

        if not html_path.exists():
            return None

        try:
            with open(html_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Simple extraction - find the entry and its associated code
            # This is a simplified approach; real implementation would use proper HTML parsing
            import re

            # Look for the entry in the HTML
            pattern = (
                rf'<td class="description">{re.escape(name)}</td>\s*<td class="command">(.*?)</td>'
            )
            match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)

            if match:
                command = match.group(1)
                # Clean up HTML tags
                command = re.sub(r"<[^>]+>", "", command)
                command = command.strip()
                return f"```\n{command}\n```"

            return None

        except Exception:
            return None

    def get_full_content(self) -> str:
        """Extract the full content of the cheatsheet"""
        html_path = self.documents_path / "index.html"

        if not html_path.exists():
            return f"No content found for {self.name} cheatsheet"

        try:
            with open(html_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Convert HTML to markdown-style text
            import re

            # Remove script and style elements
            html_content = re.sub(
                r"<(script|style)[^>]*>.*?</\1>",
                "",
                html_content,
                flags=re.DOTALL | re.IGNORECASE,
            )

            # Extract title
            title_match = re.search(r"<h1[^>]*>(.*?)</h1>", html_content, re.IGNORECASE)
            title = title_match.group(1) if title_match else self.name

            # Extract main description (from article > p)
            desc_match = re.search(
                r"<article>\s*<p>(.*?)</p>", html_content, re.DOTALL | re.IGNORECASE
            )
            description = ""
            if desc_match:
                description = desc_match.group(1)
                # Clean nested tags
                description = re.sub(r"<a[^>]*>(.*?)</a>", r"\1", description)
                description = re.sub(r"<[^>]+>", "", description)
                description = re.sub(r"\s+", " ", description).strip()

            # Process sections
            sections: list[str] = []

            # Find all section.category blocks
            section_pattern = r'<section class=[\'"]category[\'"]>(.*?)</section>'
            section_matches = re.findall(section_pattern, html_content, re.DOTALL | re.IGNORECASE)

            for section_html in section_matches:
                # Extract section title from h2
                h2_match = re.search(r"<h2[^>]*>\s*(.*?)\s*</h2>", section_html, re.IGNORECASE)
                if not h2_match:
                    continue

                section_title = h2_match.group(1).strip()

                # Extract all entries in this section
                entries: list[str] = []

                # Find all table rows with entries
                tr_pattern = r"<tr[^>]*>(.*?)</tr>"
                tr_matches = re.findall(tr_pattern, section_html, re.DOTALL | re.IGNORECASE)

                for tr_html in tr_matches:
                    # Extract entry name
                    name_match = re.search(
                        r'<div class=[\'"]name[\'"]>\s*<p>(.*?)</p>',
                        tr_html,
                        re.DOTALL | re.IGNORECASE,
                    )
                    if not name_match:
                        continue

                    entry_name = name_match.group(1).strip()

                    # Extract notes/content
                    notes_pattern = r'<div class=[\'"]notes[\'"]>(.*?)</div>'
                    notes_matches = re.findall(notes_pattern, tr_html, re.DOTALL | re.IGNORECASE)

                    entry_content: list[str] = []
                    for notes in notes_matches:
                        if not notes.strip():
                            continue

                        # Extract code blocks
                        code_pattern = r"<pre[^>]*>(.*?)</pre>"
                        code_matches = re.findall(code_pattern, notes, re.DOTALL | re.IGNORECASE)

                        # Replace code blocks with placeholders
                        temp_notes = notes
                        for idx, code in enumerate(code_matches):
                            temp_notes = temp_notes.replace(
                                f'<pre class="highlight plaintext">{code}</pre>',
                                f"__CODE_{idx}__",
                            )
                            temp_notes = temp_notes.replace(f"<pre>{code}</pre>", f"__CODE_{idx}__")

                        # Extract inline code
                        inline_code_pattern = r"<code[^>]*>(.*?)</code>"
                        inline_codes = re.findall(inline_code_pattern, temp_notes, re.IGNORECASE)

                        # Replace inline code with placeholders
                        for idx, code in enumerate(inline_codes):
                            temp_notes = re.sub(
                                f"<code[^>]*>{re.escape(code)}</code>",
                                f"__INLINE_{idx}__",
                                temp_notes,
                            )

                        # Remove all HTML tags
                        text = re.sub(r"<[^>]+>", " ", temp_notes)

                        # Restore code blocks
                        for idx, code in enumerate(code_matches):
                            # Clean up HTML entities in code
                            code = (
                                code.replace("&lt;", "<")
                                .replace("&gt;", ">")
                                .replace("&amp;", "&")
                                .replace("&#39;", "'")
                                .replace("&quot;", '"')
                            )
                            text = text.replace(f"__CODE_{idx}__", f"\\n```\\n{code}\\n```\\n")

                        # Restore inline code
                        for idx, code in enumerate(inline_codes):
                            code = (
                                code.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
                            )
                            text = text.replace(f"__INLINE_{idx}__", f"`{code}`")

                        # Clean up whitespace
                        text = re.sub(r"\\s+", " ", text).strip()
                        text = re.sub(
                            r"\\s*\\n\\s*```", "\\n```", text
                        )  # Clean code block formatting
                        text = re.sub(r"```\\s*\\n\\s*", "```\\n", text)

                        if text:
                            entry_content.append(text)

                    if entry_content:
                        entries.append(f"### {entry_name}\n" + "\n\n".join(entry_content))

                if entries:
                    sections.append(f"## {section_title}\n" + "\n\n".join(entries))

            # Extract footer/notes section
            notes_section_match = re.search(
                r'<section class=[\'"]notes[\'"]>(.*?)</section>',
                html_content,
                re.DOTALL | re.IGNORECASE,
            )
            if notes_section_match:
                notes_html = notes_section_match.group(1)
                # Extract h2
                h2_match = re.search(r"<h2[^>]*>(.*?)</h2>", notes_html, re.IGNORECASE)
                if h2_match:
                    notes_title = h2_match.group(1).strip()
                    # Extract content
                    notes_content = re.sub(r"<h2[^>]*>.*?</h2>", "", notes_html)
                    notes_content = re.sub(r"<a[^>]*>(.*?)</a>", r"\\1", notes_content)
                    notes_content = re.sub(r"<[^>]+>", " ", notes_content)
                    notes_content = re.sub(r"\\s+", " ", notes_content).strip()

                    if notes_content:
                        sections.append(f"## {notes_title}\\n{notes_content}")

            # Build the final output
            result: list[str] = [f"# {title}"]

            if description:
                result.append(f"\n{description}")

            if sections:
                result.append("\n" + "\n\n".join(sections))

            return "\n".join(result)

        except Exception as e:
            return f"Error extracting content from {self.name} cheatsheet: {str(e)}"
