import asyncio
import httpx
from main import app

async def run_test():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        res = await c.get("/api/health")
        print("Health status code:", res.status_code)
        print("Health response:", res.json())
        assert res.status_code == 200

        # Test web route
        r_home = await c.get("/")
        print("Home page status code:", r_home.status_code)
        assert r_home.status_code == 200

        # Test legal chat
        r_chat = await c.post("/api/chat", json={
            "message": "What is Section 27 of Indian Contract Act?"
        })
        print("Chat status code:", r_chat.status_code)
        print("Chat response preview:", r_chat.json()["answer"][:200])
        assert r_chat.status_code == 200

if __name__ == "__main__":
    asyncio.run(run_test())
