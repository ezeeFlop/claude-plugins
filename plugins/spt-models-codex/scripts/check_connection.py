"""Test MCP initialization, tools and catalogue without printing credentials or payloads."""
import asyncio
from pathlib import Path
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def check():
    params = StdioServerParameters(command=sys.executable, args=[str(Path(__file__).with_name("launch.py"))])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            expected = {"list_models", "get_model_info", "load_model", "unload_model",
                        "refresh_prompting_guide", "chat", "complete", "embed",
                        "generate_image", "generate_video", "generate_music", "tts",
                        "transcribe", "rerank"}
            if not expected <= names:
                raise RuntimeError("Missing tools")
            result = await session.call_tool("list_models", {})
            if getattr(result, "is_error", getattr(result, "isError", False)):
                raise RuntimeError("Catalogue failed")
            print("MCP initialization OK; 14 expected tools present; catalogue call OK.")


if __name__ == "__main__":
    try:
        asyncio.run(asyncio.wait_for(check(), timeout=60))
    except Exception:
        sys.exit("SPT Models MCP check failed. Verify setup, gateway availability and dependencies.")
