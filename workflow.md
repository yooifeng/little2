workflow:

1) Establish WebSocket Connection: Connect to wss://api.openai.com/v1/realtime with your API key and appropriate headers. 

2) Session Setup: Send a session.update event to define input/output formats (PCM, sample rates), voice(use shimmer), etc. 

3)Stream Audio: Capture mic input (e.g. via sounddevice or pyaudio) and stream chunks to the API.

4) Receive Events: The API responds with intermediate & final audio/text segments:

	response.audio.delta and response.text.delta

	response.audio.done, response.text.done to mark finalization 

5) Playback & Interaction: Decode audio deltas and play back in real-time, or display transcription for GPT response.
