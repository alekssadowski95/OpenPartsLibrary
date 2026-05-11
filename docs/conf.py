"""Sphinx configuration for OpenPartsLibrary documentation."""

from pathlib import Path
import os
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
os.environ["OPENPARTSLIBRARY_SKIP_APP_INIT"] = "1"
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent / "_ext"))

project = "OpenPartsLibrary"
author = "OpenPartsLibrary contributors"
copyright = "2026, OpenPartsLibrary contributors"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "simple_markdown",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "alabaster"
html_static_path = []
html_title = "OpenPartsLibrary Documentation"

autodoc_typehints = "description"
autodoc_member_order = "bysource"
