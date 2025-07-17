import base64
import json
import os
import threading
import queue
import sounddevice as sd
import websocket
import argparse
import numpy as np # Ensure numpy is imported

# --- Configuration ---
API_KEY = os.environ.get("OPENAI_API_KEY")
if not API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable not set.")

# --- Device Configuration ---
MIC_ID = os.environ.get("MIC_ID")
PLAYBACK_ID = os.environ.get("PLAYBACK_ID")

# --- Audio Settings ---
# --- FIX #1: Unify sample rates to prevent hardware conflict ---
INPUT_SAMPLE_RATE = 16000 
PLAYBACK_SAMPLERATE = 16000
CHANNELS = 1
DTYPE = "int16"

# --- Global State ---
ws_connected = threading.Event()
audio_out_queue = queue.Queue()

# --- WebSocket Callbacks ---
def on_message(ws, message):
    try:
        response_data = json.loads(message)
        event_type = response_data.get("type")

        if event_type == "text.delta":
            print(f"Transcript: {response_data.get('delta', '')}", end='\r', flush=True)
        elif event_type == "response.audio.delta":
            audio_delta_b64 = response_data.get("delta", "")
            if audio_delta_b64:
                audio_chunk = base64.b64decode(audio_delta_b64)
                audio_out_queue.put(audio_chunk)
        elif event_type == "session.created":
             print("\nSession configured. You can start speaking now.")
             
    except Exception as e:
        print(f"Error processing message: {e}")

def on_error(ws, error):
    print(f"WebSocket Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("\n### WebSocket Closed ###")
    ws_connected.clear()

def on_open(ws):
    print("### WebSocket Opened ### Configuring session...")
    ws.send(json.dumps({
        "type": "session.update",
        "session": { "voice": "shimmer", "instructions": "You are a friendly and helpful assistant." }
    }))
    ws_connected.set()

# --- Audio Handling Threads ---
def audio_input_thread(ws):
    def callback(indata, frames, time, status):
        if ws_connected.is_set():
            try:
                audio_base64 = base64.b64encode(indata).decode('utf-8')
                json_payload = json.dumps({
                    "type": "input_audio_buffer.append",
                    "audio": audio_base64
                })
                ws.send(json_payload)
            except Exception as e:
                print(f"Error sending audio: {e}")

    with sd.InputStream(
        samplerate=INPUT_SAMPLE_RATE, channels=CHANNELS, dtype=DTYPE,
        device=MIC_ID, callback=callback
    ) as stream:
        while ws_connected.is_set():
            sd.sleep(100)

def audio_output_thread():
    with sd.OutputStream(
        samplerate=PLAYBACK_SAMPLERATE, channels=CHANNELS, dtype=DTYPE,
        device=PLAYBACK_ID
    ) as stream:
        while ws_connected.is_set() or not audio_out_queue.empty():
            try:
                audio_chunk_bytes = audio_out_queue.get(timeout=0.1)
                
                # --- FIX #2: Convert raw bytes to a NumPy array before playing ---
                audio_chunk_np = np.frombuffer(audio_chunk_bytes, dtype=np.int16)
                stream.write(audio_chunk_np)

            except queue.Empty:
                continue

# --- Main Execution ---
def main():
    mic_device = MIC_ID or "default"
    playback_device = PLAYBACK_ID or "default"
    print(f"🎙️ Using Mic: '{mic_device}' | 🔈 Using Speaker: '{playback_device}'")

    ws_url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"
    ws_headers = [
        "Authorization: Bearer " + API_KEY,
        "OpenAI-Beta: realtime=v1"
    ]

    ws = websocket.WebSocketApp(
        ws_url,
        header=ws_headers,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open
    )

    ws_thread = threading.Thread(target=ws.run_forever)
    ws_thread.daemon = True
    ws_thread.start()

    if not ws_connected.wait(timeout=10):
        print("Failed to connect to WebSocket. Please check your API key and headers.")
        return

    in_thread = threading.Thread(target=audio_input_thread, args=(ws,))
    out_thread = threading.Thread(target=audio_output_thread)
    in_thread.daemon = True
    out_thread.daemon = True
    in_thread.start()
    out_thread.start()

    try:
        while ws_thread.is_alive():
            ws_thread.join(timeout=0.1)
    except KeyboardInterrupt:
        print("\nClosing connection...")
    finally:
        if ws.sock and ws.sock.connected:
            ws.close()
        print("Main thread finished.")

def list_audio_devices():
    """Lists available audio devices."""
    print("Available audio devices:")
    print(sd.query_devices())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Real-time voice assistant with OpenAI.")
    parser.add_argument(
        '--list-devices', action='store_true', help='List available audio devices and exit.'
    )
    args = parser.parse_args()

    if args.list_devices:
        list_audio_devices()
    else:
        try:
            import websocket
        except ImportError:
            print("Please install the required library: pip install websocket-client")
        else:
            main()