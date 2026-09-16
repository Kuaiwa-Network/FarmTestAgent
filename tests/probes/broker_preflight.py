import asyncio
import json
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    env = dict(os.environ)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    params = StdioServerParameters(command=sys.executable, args=['/Users/elendil/WorkSpaces/Farm/Farm-Client/tools/device-mcp/server.py'], env=env)
    async with asyncio.timeout(15):
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as session:
                init = await session.initialize()
                listing = await session.list_tools()
                status = await session.call_tool('device_status', {})
                print(json.dumps({'server': init.serverInfo.model_dump(), 'tools': [t.name for t in listing.tools], 'status': status.model_dump()}, indent=2))

asyncio.run(main())
