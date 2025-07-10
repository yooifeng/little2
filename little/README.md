# Voice Assistant

A simple voice assistant that uses speech recognition and OpenAI's GPT model to provide responses.

## Prerequisites

- Python 3.7 or higher
- A microphone
- Speakers
- OpenAI API key

## Installation

1. Install system dependencies:
```bash
sudo apt-get install portaudio19-dev python3-pyaudio espeak
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your OpenAI API key:
```bash
export OPENAI_API_KEY='your-api-key-here'
```

## Usage

Run the voice assistant:
```bash
python voice_assistant.py
```

- The assistant will start listening for your voice commands
- Speak clearly into your microphone
- Say "goodbye" to exit the program

## Features

- Speech recognition using Google's Speech Recognition API
- Text-to-speech using espeak
- Natural language processing using OpenAI's GPT model
- Simple command interface

## Troubleshooting

If you encounter any issues:

1. Make sure your microphone is properly connected and working
2. Check that your speakers are working
3. Verify that your OpenAI API key is correctly set
4. Ensure all dependencies are properly installed 