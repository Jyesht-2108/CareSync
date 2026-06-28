import os
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv(r"c:\Users\Dell\IEEE-Dataport-Hacks\CareSync\backend\.env")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
print(f"Key loaded: {'Yes' if OPENAI_API_KEY else 'No'}")

async def test_session():
    async with httpx.AsyncClient() as client:
        # Try /v1/realtime/sessions
        print("Trying /v1/realtime/sessions...")
        res = await client.post(
            "https://api.openai.com/v1/realtime/sessions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={"model": "gpt-4o-realtime-preview-2024-12-17"}
        )
        print("Status:", res.status_code)
        print("Response:", res.text)
        
        # Try /v1/realtime/client_secrets
        print("\nTrying /v1/realtime/client_secrets...")
        res2 = await client.post(
            "https://api.openai.com/v1/realtime/client_secrets",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": "gpt-4o-realtime-preview-2024-12-17",
                "session": {
                    "instructions": "test instructions",
                    "voice": "alloy"
                }
            }
        )
        print("Status:", res2.status_code)
        print("Response:", res2.text)

if __name__ == "__main__":
    asyncio.run(test_session())
