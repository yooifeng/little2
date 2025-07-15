# Makefile for the Voice Assistant Project

# Use the python3 interpreter
PYTHON = python3

.PHONY: install run clean

#init project
init:
	$(PYTHON) -m venv venv
	source venv/bin/activate

# Target to install dependencies ⚙️
install:
	$(PYTHON) -m pip install -r requirements.txt

# Target to run the main application ▶️
run:
	$(PYTHON) pi_voice_assistant.py

# Target to clean up temporary files 🧹
clean:
	rm -f temp_command.wav
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +
