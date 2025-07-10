import os
import speech_recognition as sr
import openai
import time
import subprocess

# --- OpenAI API Setup ---
# Load the API key from an environment variable for security
try:
    openai.api_key = os.environ["OPENAI_API_KEY"]
except KeyError:
    print("ERROR: OPENAI_API_KEY environment variable not set.")
    print("Please set the key using 'export OPENAI_API_KEY=your_key_here'")
    exit()

def get_openai_response(prompt):
    """
    Get a response from OpenAI's API.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error getting response from OpenAI: {e}")
        return "I'm sorry, I encountered an error."

def listen_for_command():
    """
    Listens for a command from the user via the microphone and returns the
    recognized text.
    """
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        # Adjust for ambient noise to improve accuracy
        recognizer.adjust_for_ambient_noise(source, duration=1)
        # Set timeout and phrase_time_limit for better control
        audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)

    try:
        print("Recognizing...")
        command = recognizer.recognize_google(audio)
        print(f"You said: {command}\n")
        return command.lower()
    except sr.UnknownValueError:
        print("Could not understand audio")
        return None
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")
        return None
    except Exception as e:
        print(f"Error during speech recognition: {e}")
        return None

def speak(text):
    """
    Uses espeak to convert text to speech.
    Optimized for Raspberry Pi with reduced voice speed for better clarity.
    """
    try:
        # Using espeak with reduced speed (-s 150) and pitch (-p 50) for better clarity
        subprocess.run(['espeak', '-s', '150', '-p', '50', text])
    except Exception as e:
        print(f"An error occurred during text-to-speech: {e}")

def check_dependencies():
    """
    Check if all required dependencies are installed.
    """
    try:
        # Check if espeak is installed
        subprocess.run(['which', 'espeak'], check=True, capture_output=True)
        print("✓ espeak is installed")
    except subprocess.CalledProcessError:
        print("✗ espeak is not installed. Installing...")
        subprocess.run(['sudo', 'apt-get', 'install', 'espeak', '-y'])
    
    try:
        # Check if portaudio is installed
        subprocess.run(['which', 'python3-pyaudio'], check=True, capture_output=True)
        print("✓ portaudio is installed")
    except subprocess.CalledProcessError:
        print("✗ portaudio is not installed. Installing...")
        subprocess.run(['sudo', 'apt-get', 'install', 'portaudio19-dev', 'python3-pyaudio', '-y'])

# --- Main Loop ---
if __name__ == "__main__":
    print("Checking dependencies...")
    check_dependencies()
    
    print("\nVoice Assistant Activated. Say 'goodbye' to exit.")
    speak("Hello, I am online and ready to assist.")

    while True:
        try:
            # Listen for the command
            command = listen_for_command()

            if command:
                # Check for the exit command
                if "goodbye" in command:
                    speak("Goodbye!")
                    break

                # Process the command with OpenAI
                response = get_openai_response(command)
                print(f"Assistant: {response}")

                # Speak the response
                speak(response)

            # A small delay to prevent high CPU usage in a tight loop
            time.sleep(0.1)
            
        except KeyboardInterrupt:
            print("\nExiting...")
            speak("Goodbye!")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(1)  # Wait a bit before retrying 