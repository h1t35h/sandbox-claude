#!/usr/bin/env python3
"""
MCP Server for Playwright browser automation.
Provides browser automation capabilities to Claude through the Model Context Protocol.
"""

import asyncio
import json
import logging
from typing import Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from playwright.async_api import async_playwright, Browser, Page, BrowserContext

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-playwright")

# Global browser instance
browser: Optional[Browser] = None
context: Optional[BrowserContext] = None
page: Optional[Page] = None


async def initialize_browser(headless: bool = True) -> None:
    """Initialize Playwright browser."""
    global browser, context, page

    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()
        logger.info("Browser initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize browser: {e}")
        raise


async def cleanup_browser() -> None:
    """Cleanup browser resources."""
    global browser, context, page

    try:
        if page:
            await page.close()
        if context:
            await context.close()
        if browser:
            await browser.close()
        logger.info("Browser cleaned up successfully")
    except Exception as e:
        logger.error(f"Failed to cleanup browser: {e}")


# Create MCP server
app = Server("playwright-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available Playwright tools."""
    return [
        Tool(
            name="navigate",
            description="Navigate to a URL",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to navigate to"
                    }
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="screenshot",
            description="Take a screenshot of the current page",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to save the screenshot"
                    },
                    "full_page": {
                        "type": "boolean",
                        "description": "Capture full page screenshot",
                        "default": False
                    }
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="click",
            description="Click an element on the page",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "CSS selector for the element to click"
                    }
                },
                "required": ["selector"]
            }
        ),
        Tool(
            name="fill",
            description="Fill a form input field",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "CSS selector for the input field"
                    },
                    "value": {
                        "type": "string",
                        "description": "Value to fill in the field"
                    }
                },
                "required": ["selector", "value"]
            }
        ),
        Tool(
            name="get_text",
            description="Get text content from an element",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "CSS selector for the element"
                    }
                },
                "required": ["selector"]
            }
        ),
        Tool(
            name="get_html",
            description="Get the HTML content of the page",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "Optional CSS selector to get HTML of specific element",
                        "default": None
                    }
                }
            }
        ),
        Tool(
            name="wait_for_selector",
            description="Wait for an element to appear on the page",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "CSS selector to wait for"
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Timeout in milliseconds",
                        "default": 30000
                    }
                },
                "required": ["selector"]
            }
        ),
        Tool(
            name="evaluate",
            description="Execute JavaScript in the page context",
            inputSchema={
                "type": "object",
                "properties": {
                    "script": {
                        "type": "string",
                        "description": "JavaScript code to execute"
                    }
                },
                "required": ["script"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    global page

    if not page:
        await initialize_browser()

    try:
        if name == "navigate":
            url = arguments["url"]
            await page.goto(url)
            return [TextContent(type="text", text=f"Navigated to {url}")]

        elif name == "screenshot":
            path = arguments["path"]
            full_page = arguments.get("full_page", False)
            await page.screenshot(path=path, full_page=full_page)
            return [TextContent(type="text", text=f"Screenshot saved to {path}")]

        elif name == "click":
            selector = arguments["selector"]
            await page.click(selector)
            return [TextContent(type="text", text=f"Clicked element: {selector}")]

        elif name == "fill":
            selector = arguments["selector"]
            value = arguments["value"]
            await page.fill(selector, value)
            return [TextContent(type="text", text=f"Filled {selector} with value")]

        elif name == "get_text":
            selector = arguments["selector"]
            text = await page.text_content(selector)
            return [TextContent(type="text", text=text or "")]

        elif name == "get_html":
            selector = arguments.get("selector")
            if selector:
                element = await page.query_selector(selector)
                html = await element.inner_html() if element else ""
            else:
                html = await page.content()
            return [TextContent(type="text", text=html)]

        elif name == "wait_for_selector":
            selector = arguments["selector"]
            timeout = arguments.get("timeout", 30000)
            await page.wait_for_selector(selector, timeout=timeout)
            return [TextContent(type="text", text=f"Element appeared: {selector}")]

        elif name == "evaluate":
            script = arguments["script"]
            result = await page.evaluate(script)
            return [TextContent(type="text", text=json.dumps(result))]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Main entry point for the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        asyncio.run(cleanup_browser())
