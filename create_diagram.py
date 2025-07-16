import os

diagram_content = """
```mermaid
sequenceDiagram
    participant User
    participant VoiceAssistant
    participant SoundDevice
    participant WhisperAPI as OpenAI Whisper API
    participant GptAPI as OpenAI GPT API
    participant TtsAPI as OpenAI TTS API

    VoiceAssistant->>User: "Listening for your command..."
    User->>SoundDevice: Speaks command
    SoundDevice-->>VoiceAssistant: Returns recorded audio
    VoiceAssistant->>WhisperAPI: Transcribe audio
    WhisperAPI-->>VoiceAssistant: Returns transcribed text
    VoiceAssistant->>GptAPI: Get GPT response
    GptAPI-->>VoiceAssistant: Returns generated text
    VoiceAssistant->>TtsAPI: Synthesize speech
    TtsAPI-->>VoiceAssistant: Returns audio data
    VoiceAssistant->>SoundDevice: Play audio response
    SoundDevice-->>User: Plays audio
```
"""

file_path = os.path.join(os.path.dirname(__file__), 'sequence_diagram.md')

with open(file_path, 'w') as f:
    f.write(diagram_content)

print(f"Sequence diagram created at {file_path}")
