import asyncio
import os
import numpy as np
import sounddevice as sd
from openai import AsyncOpenAI
import soundfile as sf
import websockets

# --- Configuration ---
API_KEY = os.environ.get("OPENAI_API_KEY")
if not API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable not set.")

client = AsyncOpenAI(api_key=API_KEY)

# Audio settings
SAMPLE_RATE = 16000  # OpenAI's recommended sample rate for their STT
CHANNELS = 1
FORMAT = np.int16
CHUNK_LENGTH_S = 0.5  # 500ms
RECORDING_THRESHOLD = 0.02  # Adjust as needed
SILENCE_THRESHOLD_S = 2.0  # Seconds of silence to end recording
PLAYBACK_SAMPLERATE = 24000 # OpenAI TTS playback sample rate

# --- Device Configuration ---
CARD_ID = os.environ.get("CARD_ID")
MIC_ID = os.environ.get("MIC_ID")
PLAYBACK_ID = os.environ.get("PLAYBACK_ID")

# --- Core Components ---

async def play_tts_stream(text_stream):
    """Plays back a stream of text using WebSocket-based streaming TTS."""
    uri = "wss://api.openai.com/v1/audio/speech"  # This is a placeholder URI

    try:
        async with websockets.connect(uri) as websocket:
            await websocket.send(f'{{"model": "tts-1-hd", "voice": "shimmer", "input": "{await text_stream.__anext__()}"}}')

            with sd.OutputStream(samplerate=PLAYBACK_SAMPLERATE, channels=CHANNELS, dtype='int16', device=PLAYBACK_ID) as stream:
                async for message in websocket:
                    # Assuming the message is raw audio data
                    audio_data = np.frombuffer(message, dtype=np.int16)
                    stream.write(audio_data)

    except Exception as e:
        print(f"Error during TTS playback: {e}")


async def get_gpt_response_stream(text: str):
    """Gets a streaming response from GPT-4o-mini."""
    if not text:
        return
    try:
        response_stream = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Speak softly and cutely, adding gentle laughter..."},
                {"role": "user", "content": text},
            ],
            temperature=0.8,
            stream=True
        )
        async for chunk in response_stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content
    except Exception as e:
        print(f"Error getting GPT response: {e}")
        yield "I'm sorry, I had a problem processing that."

# --- Main Application Logic ---

async def listen_and_process():
    """Listens for voice, processes it, and responds."""
    print("Starting voice assistant. Press Ctrl+C to exit.")
    
    while True:
        print("\nListening for your command...")
        
        recorded_frames = []
        is_recording = False
        silence_counter = 0
        recording_finished = asyncio.Event()
        
        def callback(indata, frames, time, status):
            nonlocal is_recording, silence_counter, recorded_frames
            if status:
                print(f"Stream status: {status}")

            volume_norm = np.linalg.norm(indata) * 10
            
            if volume_norm > RECORDING_THRESHOLD:
                if not is_recording:
                    print("Recording started...")
                    is_recording = True
                recorded_frames.append(indata.copy())
                silence_counter = 0
            elif is_recording:
                silence_counter += 1
                num_silent_chunks = int(SILENCE_THRESHOLD_S / CHUNK_LENGTH_S)
                if silence_counter > num_silent_chunks:
                    loop = asyncio.get_running_loop()
                    loop.call_soon_threadsafe(recording_finished.set)
                    raise sd.CallbackStop

        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype=FORMAT,
                blocksize=int(SAMPLE_RATE * CHUNK_LENGTH_S),
                callback=callback,
                device=MIC_ID
            ):
                await recording_finished.wait()
        except Exception as e:
            print(f"An error occurred during recording: {e}")

        print("Recording stopped due to silence.")

        if not recorded_frames:
            print("No audio recorded.")
            continue

        audio_data = np.concatenate(recorded_frames, axis=0)
        
        temp_file_path = "temp_recording.wav"
        sf.write(temp_file_path, audio_data, SAMPLE_RATE)

        with open(temp_file_path, "rb") as audio_file:
            transcription = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
            )
        os.remove(temp_file_path)
        
        print(f"You said: {transcription.text}")

        if transcription.text:
            gpt_response_stream = get_gpt_response_stream(transcription.text)
            await play_tts_stream(gpt_response_stream)

def list_audio_devices():
    """Lists available audio devices."""
    print("Available audio devices:")
    print(sd.query_devices())

async def main():
    # Check for necessary dependencies
    try:
        import sounddevice
        import soundfile
        import websockets
    except ImportError:
        print("Please install the required libraries: pip install sounddevice soundfile websockets")
        return

    list_audio_devices()

    if CARD_ID:
        try:
            sd.default.device = int(CARD_ID)
            print(f"Using sound card ID: {CARD_ID}")
        except ValueError:
            print(f"Invalid CARD_ID: {CARD_ID}. Using default device.")


    await listen_and_process()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Voice Assistant")
    parser.add_argument('--list-devices', action='store_true', help='List available audio devices and exit.')
    args = parser.parse_args()

    if args.list_devices:
        list_audio_devices()
    else:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("\nExiting voice assistant.")
