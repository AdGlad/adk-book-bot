# book_agent/__init__.py
"""
Package that contains the root ADK agent for the Kindle book generator.

For now this just exposes `root_agent`. You will later add:
- tools (quote search, GCS upload, etc.)
- sub-agents or more advanced orchestration.
"""
from .agent import root_agent  # noqa: F401

