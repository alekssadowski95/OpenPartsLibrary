"""Small Markdown source parser for the project documentation.

It supports the subset used by this repository's docs: headings, paragraphs,
bullets, numbered lists, fenced code blocks, and inline code literals.
"""

from __future__ import annotations

import re

from docutils import nodes
from docutils.parsers import Parser
from docutils.statemachine import StringList


class SimpleMarkdownParser(Parser):
    """Parse lightweight Markdown into docutils nodes for Sphinx.

    The parser intentionally stays small so the docs can be built without
    external Markdown parser dependencies in constrained environments.
    """

    supported = ("markdown", "md")

    def parse(self, inputstring, document):
        """Parse Markdown text into a docutils document tree."""

        self.document = document
        self.section_stack = [(0, document)]
        lines = inputstring.splitlines()
        index = 0
        while index < len(lines):
            line = lines[index]
            stripped = line.strip()

            if not stripped:
                index += 1
                continue

            if stripped.startswith("```"):
                language = stripped[3:].strip()
                code_lines = []
                index += 1
                while index < len(lines) and not lines[index].strip().startswith("```"):
                    code_lines.append(lines[index])
                    index += 1
                literal = nodes.literal_block("\n".join(code_lines), "\n".join(code_lines))
                if language:
                    literal["language"] = language
                parent = self._current_parent()
                parent += literal
                index += 1
                continue

            heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
            if heading_match:
                self._add_section(len(heading_match.group(1)), heading_match.group(2).strip())
                index += 1
                continue

            if re.match(r"^[-*]\s+", stripped):
                bullet_list = nodes.bullet_list()
                while index < len(lines) and re.match(r"^[-*]\s+", lines[index].strip()):
                    text = re.sub(r"^[-*]\s+", "", lines[index].strip())
                    item = nodes.list_item()
                    item += self._paragraph(text)
                    bullet_list += item
                    index += 1
                parent = self._current_parent()
                parent += bullet_list
                continue

            if re.match(r"^\d+\.\s+", stripped):
                enumerated = nodes.enumerated_list(enumtype="arabic")
                while index < len(lines) and re.match(r"^\d+\.\s+", lines[index].strip()):
                    text = re.sub(r"^\d+\.\s+", "", lines[index].strip())
                    item = nodes.list_item()
                    item += self._paragraph(text)
                    enumerated += item
                    index += 1
                parent = self._current_parent()
                parent += enumerated
                continue

            paragraph_lines = [stripped]
            index += 1
            while index < len(lines) and lines[index].strip():
                next_line = lines[index].strip()
                if next_line.startswith("```") or re.match(r"^(#{1,6})\s+|^[-*]\s+|^\d+\.\s+", next_line):
                    break
                paragraph_lines.append(next_line)
                index += 1
            parent = self._current_parent()
            parent += self._paragraph(" ".join(paragraph_lines))

    def _current_parent(self):
        """Return the current document or section node."""

        return self.section_stack[-1][1]

    def _add_section(self, level, title_text):
        """Add a heading section and make it the current parent."""

        while self.section_stack and self.section_stack[-1][0] >= level:
            self.section_stack.pop()

        section = nodes.section(ids=[nodes.make_id(title_text)])
        section += nodes.title(title_text, title_text)
        parent = self.section_stack[-1][1]
        parent += section
        self.section_stack.append((level, section))

    def _paragraph(self, text):
        """Create a paragraph node with basic inline code handling."""

        paragraph = nodes.paragraph()
        parts = re.split(r"(`[^`]+`)", text)
        for part in parts:
            if part.startswith("`") and part.endswith("`"):
                paragraph += nodes.literal(part[1:-1], part[1:-1])
            else:
                paragraph += nodes.Text(part)
        return paragraph


def setup(app):
    """Register the parser with Sphinx."""

    app.add_source_parser(SimpleMarkdownParser)
    app.add_source_suffix(".md", "markdown")
    return {"version": "1.0", "parallel_read_safe": True}
