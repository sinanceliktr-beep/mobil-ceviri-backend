import os
import json
import asyncio
import websockets
from fastapi import FastAPI, WebSocket

# API Key Render'dan gelecek
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") 

SYSTEM_INSTRUCTION = """
You are a real-time translator app backend.
Task: Translate Turkish to English and English to Turkish instantly.
Rules:
1. Output ONLY the translated audio. No chit-chat.
2. If the user speaks Turkish, reply in English.
3. If the user speaks English, reply in Turkish.
4. Keep translations short and professional.
"""

VOICE = "shimmer" 
app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Call Center AI Backend Calisiyor!"}

@app.websocket("/mobile-stream")
async def handle_mobile_stream(websocket: WebSocket):
    await websocket.accept()
    print(">>> Mobil Uygulama Baglandi!")

    if not OPENAI_API_KEY:
        print("HATA: API Key yok!")
        await websocket.close()
        return

    url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "realtime=v1",
    }

    async with websockets.connect(url, additional_headers=headers) as openai_ws:
        print(">>> OpenAI Baglandi!")
        
        session_update = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": SYSTEM_INSTRUCTION,
                "voice": VOICE,
                "input_audio_format": "pcm16", # Mobil icin HD
                "output_audio_format": "pcm16",
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500
                }
            }
        }
        await openai_ws.send(json.dumps(session_update))

        async def receive_from_app():
            try:
                while True:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    if message['type'] == 'audio':
                        await openai_ws.send(json.dumps({
                            "type": "input_audio_buffer.append",
                            "audio": message['payload']
                        }))
            except:
                pass

        async def receive_from_openai():
            try:
                async for message in openai_ws:
                    response = json.loads(message)
                    if response['type'] == 'response.audio.delta' and response.get('delta'):
                        await websocket.send_json({
                            "type": "audio",
                            "payload": response['delta']
                        })
            except:
                pass

        await asyncio.gather(receive_from_app(), receive_from_openai())