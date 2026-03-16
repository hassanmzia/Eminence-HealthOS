import httpx

class MCPClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.api_key = api_key

    async def call(self, tool_name, args):
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.base_url}/tools/{tool_name}",
                json=args,
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            return r.json()
