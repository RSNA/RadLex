# Development Guidelines

This document contains critical information about working with this codebase. Follow these guidelines precisely.

## Project overview
This is a proof of concept work to parse RADLEX ontologies into a knowledge graph, and use that knowledge graph to extract elements out of reports and propose potential new ones.

It requires a data processing OWL->duckdb accessible on-disk storage, and skill harnesses for the pi agent framework to do the processing.
## Design references

@docs/
## Core Development Rules

1. Package Management
   - ONLY use uv, NEVER pip
   - Installation: `uv add package`
   - Running tools: `uv run tool`
   - Upgrading: `uv add --dev package --upgrade-package package`
   - FORBIDDEN: `uv pip install`, `@latest` syntax

2. Code Quality
   - Type hints required for all code
   - Public APIs must have docstrings
   - Functions must be focused and small
   - Follow existing patterns exactly
   - Line length: 120 chars maximum
   - Doc strings must be written for each function using the Google style guide


3. Testing Requirements
   - Framework: `uv run --frozen pytest`

## Python Tools

## Code Formatting

1. Ruff
   - Format: `uv run --frozen ruff format .`
   - Check: `uv run --frozen ruff check .`
   - Fix: `uv run --frozen ruff check . --fix`
   - Critical issues:
     - Line length (88 chars)
     - Import sorting (I001)
     - Unused imports
   - Line wrapping:
     - Strings: use parentheses
     - Function calls: multi-line with proper indent
     - Imports: split into multiple lines

# Error Resolution

2. Common Issues
   - Line length:
     - Break strings with parentheses
     - Multi-line function calls
     - Split imports

3. Best Practices
   - Check git status before commits
   - Run formatters
   - Keep changes minimal
   - Follow existing patterns
   - Document public APIs

## Exception Handling

- **Always use `logger.exception()` instead of `logger.error()` when catching exceptions**
  - Don't include the exception in the message: `logger.exception("Failed")` not `logger.exception(f"Failed: {e}")`
- **Catch specific exceptions** where possible:
  - File ops: `except (OSError, PermissionError):`
  - JSON: `except json.JSONDecodeError:`
  - Network: `except (ConnectionError, TimeoutError):`
- **Only catch `Exception` for**:
  - Top-level handlers that must not crash
  - Cleanup blocks (log at debug level)
