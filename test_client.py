"""Test client for Advanced MCP Server"""

import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def run_demo():
    """Run demo tests of the MCP server"""
    
    # Setup server parameters
    server_params = StdioServerParameters(
        command="python",
        args=[os.path.join(os.path.dirname(__file__), "src", "server.py")]
    )
    
    print("🚀 Advanced MCP Server - Test Client")
    print("=" * 60)
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                print("✓ Connecting to server...")
                await session.initialize()
                print("✓ Connection established!\n")
                
                # List tools
                tools_response = await session.list_tools()
                print(f"📋 Available Tools ({len(tools_response.tools)}):")
                for tool in tools_response.tools:
                    print(f"   • {tool.name}: {tool.description}")
                
                print()
                
                # Test analyze_text tool
                print("🔍 Testing Text Analysis Tool...")
                text = "This is a great piece of text that demonstrates the excellent capabilities of our advanced MCP server system."
                result = await session.call_tool("analyze_text", {
                    "text": text,
                    "analyze_sentiment": True,
                    "extract_keywords": True
                })
                print(f"   Result: {result.content[0].text}\n")
                
                # Test code analysis
                print("📊 Testing Code Analysis Tool...")
                code = """
def fibonacci(n):
    '''Calculate fibonacci number'''
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

class DataProcessor:
    def __init__(self, data):
        self.data = data
    
    def process(self):
        return [x * 2 for x in self.data]
"""
                result = await session.call_tool("analyze_code", {
                    "code": code,
                    "language": "python"
                })
                print(f"   Result: {result.content[0].text}\n")
                
                # Test data processing with progress
                print("⚙️  Testing Data Processing with Progress...")
                result = await session.call_tool("process_data", {
                    "data_size": 1000,
                    "operation": "transform"
                })
                print(f"   Result: {result.content[0].text}\n")
                
                # Test database query
                print("🗄️  Testing Database Query Tool...")
                result = await session.call_tool("execute_database_query", {
                    "query": "SELECT * FROM users WHERE id > 100",
                    "transaction": False
                })
                print(f"   Result: {result.content[0].text}\n")
                
                # List resources
                resources_response = await session.list_resources()
                print(f"📚 Available Resources ({len(resources_response.resources)}):")
                for resource in resources_response.resources:
                    print(f"   • {resource.uri}: {resource.description}")
                
                print()
                
                # Read a resource
                print("📖 Reading Configuration Resource...")
                from pydantic import AnyUrl
                resource = await session.read_resource(AnyUrl("config://settings/features"))
                if resource.contents:
                    print(f"   Content: {resource.contents[0].text}\n")
                
                # List prompts
                prompts_response = await session.list_prompts()
                print(f"📝 Available Prompts ({len(prompts_response.prompts)}):")
                for prompt in prompts_response.prompts:
                    print(f"   • {prompt.name}: {prompt.description}")
                
                print("\n✅ All tests completed successfully!")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_demo())
