import sys, os, asyncio

sys.path.insert(0, 'app')
from dotenv import load_dotenv

load_dotenv()

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test():
    token = os.getenv('GITHUB_TOKEN', '')
    print(f"Token starts with: {token[:10]}...")

    params = StdioServerParameters(
        command='npx',
        args=['-y', '@modelcontextprotocol/server-github'],
        env={
            'GITHUB_PERSONAL_ACCESS_TOKEN': token,
            'PATH': os.environ.get('PATH', ''),
        }
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("MCP connected!")

            tools = await session.list_tools()
            print("Available tools:", [t.name for t in tools.tools])

            result = await session.call_tool('get_file_contents', {
                'owner': 'NotHarshhaa',
                'repo': 'DevOps-Projects',
                'path': 'DevOps-Project-01'
            })
            print("Result:", result.content[0].text)


asyncio.run(test())