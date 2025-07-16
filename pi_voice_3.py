import base64
import json
import os
import threading
import time
import sounddevice as sd
import websocket

# Configuration
API_KEY = os.environ.get("OPENAI_API_KEY")
WEBSOCKET_URI = "wss://api.openai.com/v1/realtime/voice"
SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"

# Global state
ws_connected = threading.Event()
audio_playing = threading.Event()

def on_message(ws, message):
    """Callback function to handle incoming messages."""
    response_data = json.loads(message)
    if "audio.delta" in response_data:
        audio_delta = base64.b64decode(response_data["audio.delta"])
        sd.play(audio_delta, samplerate=SAMPLE_RATE)
    if "text.delta" in response_data:
        print(f"Text: {response_data['text.delta']}", end="", flush=True)
    if "audio.done" in response_data and response_data["audio.done"]:
        print("\nAudio stream finished.")
        audio_playing.set()
    if "text.done" in response_data and response_data["text.done"]:
        print("\nText stream finished.")

def on_error(ws, error):
    """Callback function to handle errors."""
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    """Callback function to handle connection close."""
    print("### closed ###")
    ws_connected.clear()

def on_open(ws):
    """Callback function to handle connection open."""
    print("WebSocket connection established.")
    ws.send(
        json.dumps(
            {
                "session.update": {
                    "voice": "shimmer",
                    "input": {"sample_rate": SAMPLE_RATE, "format": "pcm"},
                    "output": {"sample_rate": SAMPLE_RATE, "format": "pcm"},
                }
            }
        )
    )
    print("Session configured.")
    ws_connected.set()

def audio_input_stream(ws):
    """Function to stream audio from the microphone."""
    def callback(indata, frames, time, status):
        if status:
            print(status)
        if ws_connected.is_set():
            ws.send(bytes(indata), websocket.ABNF.OPCODE_BINARY)

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype=DTYPE, callback=callback):
        while ws_connected.is_set():
            time.sleep(0.1)

def main():
    """Main function to run the voice assistant."""
    websocket.enableTrace(True)
    ws = websocket.WebSocketApp(
        WEBSOCKET_URI,
        header={"Authorization": f"Bearer {API_KEY}"},
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )
    ws.on_open = on_open

    wst = threading.Thread(target=ws.run_forever)
    wst.daemon = True
    wst.start()

    ws_connected.wait()  # Wait for connection to be established

    audio_thread = threading.Thread(target=audio_input_stream, args=(ws,))
    audio_thread.daemon = True
    audio_thread.start()

    try:
        while ws_connected.is_set():
            time.sleep(0.1)
    except KeyboardInterrupt:
        ws.close()

if __name__ == "__main__":
    main()
