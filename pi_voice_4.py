import asyncio
import os
import json
import base64
import websockets
import sounddevice as sd
import threading

API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise RuntimeError("Set OPENAI_API_KEY")

SAMPLE_RATE = 24000  # As recommended
CHANNELS = 1

# VAD and session config based on OpenAI's Realtime API guide
SESSION_CONFIG = {
    "type": "session.update",
    "session": {
        "modalities": ["audio", "text"],
        "voice": "alloy",
        "input_audio_format": "pcm16",
        "output_audio_format": "pcm16",
        "turn_detection": {
            "type": "server_vad",
            "threshold": 0.5,
            "prefix_padding_ms": 300,
            "silence_duration_ms": 600
        },
        "input_audio_transcription": {"model": "whisper-1"},
        "temperature": 0.7
    }
}

async def consumer_handler(ws):
    audio_buf = b""
    async for msg in ws:
        event = json.loads(msg)
        t = event.get("type")
        if t == "response.text.delta":
            print(event.get("delta"), end="", flush=True)
        elif t == "response.audio.delta":
            audio_buf += base64.b64decode(event["delta"])
        elif t == "response.audio.done":
            # Play the buffered audio
            sd.play(audio_buf, samplerate=SAMPLE_RATE)
            sd.wait()
            audio_buf = b""
        elif t == "response.done":
            print("\n[Response done]\n")

async def producer_handler(ws):
    # Start sending audio: opens mic input, sends raw PCM
    def callback(indata, frames, time, status):
        if status:
            print("Mic status:", status)
        ws.send(indata.tobytes())
    
    stream = sd.InputStream(
        samplerate=SAMPLE_RATE, channels=CHANNELS, dtype='int16',
        callback=callback, blocksize=1024
    )
    with stream:
        await asyncio.sleep(3600)  # run until websocket closes

async def main():
    uri = "wss://api.openai.com/v1/realtime"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "OpenAI-Beta": "realtime=v1"
    }

    async with websockets.connect(uri, additional_headers=headers) as ws:
        # Initialize session
        await ws.send(json.dumps(SESSION_CONFIG))
        await ws.send(json.dumps({"type": "response.create"}))
        print("Session started, say something!")

        consumer = asyncio.create_task(consumer_handler(ws))
        producer = asyncio.create_task(producer_handler(ws))
        done, pending = await asyncio.wait(
            [consumer, producer],
            return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()

if __name__ == "__main__":
    asyncio.run(main())

