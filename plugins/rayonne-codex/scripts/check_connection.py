"""Check the installed MCP adapter using one read-only call; print no payloads."""
import asyncio
import json
from pathlib import Path
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def check():
    params = StdioServerParameters(command=sys.executable, args=[str(Path(__file__).with_name("launch.py"))])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            names = {tool.name for tool in listed.tools}
            expected = {"rayonne_overview", "rayonne_list_workspaces", "rayonne_upload_product_asset", "rayonne_chat_storyboard"}
            if len(names) != 81 or not expected <= names:
                raise RuntimeError("Unexpected tool catalogue")
            result = await session.call_tool("rayonne_overview", {})
            if result.isError:
                raise RuntimeError("Overview failed")
            payload = json.loads(next(item.text for item in result.content if item.type == "text"))
            if not isinstance(payload, dict) or "error" in payload:
                raise RuntimeError("Overview failed")
            print("MCP initialization OK; 81 tools present; workspace overview OK.")


if __name__ == "__main__":
    try:
        asyncio.run(asyncio.wait_for(check(), timeout=60))
    except Exception:
        sys.exit("Rayonne MCP check failed. Verify setup, availability and dependencies.")
