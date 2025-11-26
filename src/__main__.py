#!/usr/bin/env python3
"""
Entry point for running the MCP server as a module.

This allows the server to be run with: python -m src
or: uv run -m src
"""

from .server import mcp

if __name__ == "__main__":
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    logger.info("Starting Database Management MCP Server")
    mcp.run()

