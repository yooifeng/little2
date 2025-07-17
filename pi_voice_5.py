import asyncio
import os
import numpy as np
import sounddevice as sd
from openai import AsyncOpenAI
import soundfile as sf
import argparse

# --- Configuration ---
API_KEY = os.environ.get("OPENAI_API_KEY")
if not API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable not set.")

client = AsyncOpenAI(api_key=API_KEY)

# --- Device Configuration ---
# Set these environment variables to a device name (string) or index (integer)
MIC_ID = os.environ.get("MIC_ID")
PLAYBACK_ID = os.environ.get("PLAYBACK_ID")


# Audio settings
SAMPLE_RATE = 16000
CHANNELS = 1
FORMAT = np.int16

#Fine-tune the RECORDING_THRESHOLD:
#If recording doesn't start when you speak, make the number smaller (e.g., 0.009).
#If recording doesn't stop after you finish speaking, make the number larger (e.g., 0.015).
RECORDING_THRESHOLD = 0.015 

SILENCE_THRESHOLD_S = 1.5
PLAYBACK_SAMPLERATE = 24000

# --- Core Components ---

async def play_tts_stream(text_stream):
    """Synthesizes and plays audio using the gpt-4o-mini-tts model."""
    print("🤖 Assistant speaking...", end="", flush=True)
    try:
        full_response = "".join([chunk async for chunk in text_stream])
        print(f" \"{full_response}\"")

        if not full_response.strip():
            return

        # --- UPDATED MODEL ---
        response = await client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="shimmer",
            input=full_response,
            response_format="pcm"
        )

        with sd.OutputStream(
            samplerate=PLAYBACK_SAMPLERATE,
            channels=CHANNELS,
            dtype=FORMAT,
            device=PLAYBACK_ID
        ) as stream:
            async for chunk in response.iter_bytes(chunk_size=1024):
                stream.write(np.frombuffer(chunk, dtype=FORMAT))

    except Exception as e:
        print(f"\nError during TTS playback: {e}")

async def get_gpt_response_stream(text: str):
    """Gets a streaming response from the gpt-4o-mini chat model."""
    if not text:
        return
    try:
        response_stream = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a friendly and helpful assistant."},
                {"role": "user", "content": text},
            ],
            stream=True
        )
        async for chunk in response_stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content
    except Exception as e:
        print(f"Error getting GPT response: {e}")
        yield "I'm sorry, I had a problem processing that."

# Replace the original function with this one
async def listen_and_process():
    """Listens for voice, processes it, and responds."""
    mic_device = MIC_ID or "default"
    playback_device = PLAYBACK_ID or "default"
    print(f"🎙️ Using Mic: '{mic_device}' | 🔈 Using Speaker: '{playback_device}'")
    print("Starting voice assistant...")

    # --- MODIFIED: Get the loop in the main async context ---
    loop = asyncio.get_running_loop()

    while True:
        print("\nListening for your command...")
        recorded_frames = []
        is_recording = False
        silence_counter = 0
        recording_finished = asyncio.Event()

        def callback(indata, frames, time, status):
            nonlocal is_recording, silence_counter
            volume_norm = np.sqrt(np.mean((indata.astype(np.float32) / 32768.0)**2))
            
            print(f"Volume: {volume_norm:.4f}", end='\r')

            if volume_norm > RECORDING_THRESHOLD:
                if not is_recording:
                    print(" " * 30, end='\r')
                    print("Recording started...")
                is_recording = True
                recorded_frames.append(indata.copy())
                silence_counter = 0
            elif is_recording:
                silence_counter += 1
                num_silent_chunks = int(SILENCE_THRESHOLD_S / (frames / SAMPLE_RATE))
                if silence_counter > num_silent_chunks:
                    # --- MODIFIED: Use the 'loop' variable from the outer scope ---
                    # This is now thread-safe
                    loop.call_soon_threadsafe(recording_finished.set)
                    raise sd.CallbackStop

        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE, channels=CHANNELS, dtype=FORMAT, callback=callback, device=MIC_ID
            ):
                await recording_finished.wait()
        except Exception as e:
            print(f"\n❌ An error occurred during recording: {e}")
            break

        print(" " * 30, end='\r') # Clear the volume line
        print("Recording stopped.")
        if not recorded_frames:
            continue

        audio_data = np.concatenate(recorded_frames, axis=0)
        temp_file_path = "temp_recording.wav"
        sf.write(temp_file_path, audio_data, SAMPLE_RATE)

        try:
            with open(temp_file_path, "rb") as audio_file:
                transcription = await client.audio.transcriptions.create(
                    model="gpt-4o-mini-transcribe", file=audio_file
                )
            print(f"👤 You said: {transcription.text}")

            if transcription.text:
                gpt_response_stream = get_gpt_response_stream(transcription.text)
                await play_tts_stream(gpt_response_stream)
        except Exception as e:
            print(f"Error during OpenAI processing: {e}")
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

def list_audio_devices():
    """Lists available audio devices."""
    print("Available audio devices:")
    print(sd.query_devices())

async def main():
    await listen_and_process()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Voice assistant using specific gpt-4o-mini models.")
    parser.add_argument(
        '--list-devices', action='store_true', help='List available audio devices and exit.'
    )
    args = parser.parse_args()

    if args.list_devices:
        list_audio_devices()
    else:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("\nExiting voice assistant.")