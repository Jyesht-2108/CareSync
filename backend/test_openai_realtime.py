import os
import httpx
import asyncio
from dotenv import load_dotenv

# Try to find .env file
env_path = r"c:\Users\Dell\IEEE-Dataport-Hacks\CareSync\backend\.env"
load_dotenv(env_path)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

async def test_session():
    if not OPENAI_API_KEY or OPENAI_API_KEY == "your_openai_api_key_here":
        print("NO VALID API KEY FOUND in .env!")
        return

    async with httpx.AsyncClient() as client:
        # What we currently send:
        payload = {
            "session": {
                "type": "realtime",
                "model": "gpt-4o-realtime-preview-2024-12-17",
                "instructions": "test instructions",
                "voice": "alloy",
                "turn_detection": {"type": "server_vad"},
                "input_audio_transcription": {"model": "whisper-1"}
            }
        }
        
        print("Sending payload:", payload)
        res = await client.post(
            "https://api.openai.com/v1/realtime/client_secrets",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json=payload
        )
        print("Status:", res.status_code)
        print("Response:", res.text)
        
        if res.status_code == 400:
            print("\nTrying with model at the root level instead...")
            payload2 = {
                "model": "gpt-4o-realtime-preview-2024-12-17",
                "session": {
                    "type": "realtime",
                    "instructions": "test instructions",
                    "voice": "alloy"
                }
            }
            print("Sending payload2:", payload2)
            res2 = await client.post(
                "https://api.openai.com/v1/realtime/client_secrets",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json=payload2
            )
            print("Status2:", res2.status_code)
            print("Response2:", res2.text)

if __name__ == "__main__":
    asyncio.run(test_session())
