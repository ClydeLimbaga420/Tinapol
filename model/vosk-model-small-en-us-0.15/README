
# Voice Assistant (Tinapol)

A lightweight, locally running Python voice assistant for Windows. Control your computer using your microphone to open applications, launch websites, and search Google.

The project uses offline speech recognition and local text-to-speech, so it does not require a cloud AI API or API key.

## Features

- Offline speech recognition using Vosk
- Local text-to-speech using pyttsx3
- Microphone input using sounddevice
- Fuzzy command matching using RapidFuzz
- Launch supported Windows applications
- Open websites using voice commands
- Search Google using spoken queries
- No cloud-based speech recognition required
- Designed for local development and future expansion

## Requirements

- Windows 10 or Windows 11
- Python 3.10 or newer recommended
- A working microphone
- Internet connection for downloading dependencies and opening websites
- Disk space for Python packages and the speech recognition model

> Python 3.14 may work, but if a dependency fails to install, try Python 3.12 or 3.13.

## Project Structure

```text
ClydeVoiceAssistant/
├── assistant.py
├── README.md
├── requirements.txt
├── .gitignore
└── model/
    └── vosk-model-small-en-us-0.15/
        ├── am/
        ├── conf/
        ├── graph/
        └── ...
```

## Installation

### 1. Install Python

Download Python from the official website:

https://www.python.org/downloads/windows/

Verify the installation:

```bat
python --version
python -m pip --version
```

### 2. Open the Project Folder

Open Command Prompt in your project directory.

If you are creating a new project:

```bat
mkdir ClydeVoiceAssistant
cd ClydeVoiceAssistant
```

If the project already exists, navigate to its directory instead.

### 3. Create a Virtual Environment

A virtual environment keeps project dependencies separate from other Python projects.

```bat
python -m venv .venv
```

Activate it in Command Prompt:

```bat
.venv\Scripts\activate.bat
```

### 4. Install Dependencies

Create a file named `requirements.txt` containing:

```text
vosk
sounddevice
pyttsx3
rapidfuzz
```

Install the required libraries:

```bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 5. Download the Vosk Speech Model

Download the small English speech recognition model:

https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip

Official model directory:

https://alphacephei.com/vosk/models

Extract the downloaded ZIP file into the project's `model` directory.

Ensure that the final path is:

```text
model/vosk-model-small-en-us-0.15/
```

The folder must contain the extracted model files, not just the ZIP archive.

### 6. Configure Your Microphone

1. Open Windows Settings.
2. Navigate to **System → Sound**.
3. Select your preferred input device.
4. Test the microphone.
5. Ensure desktop applications have microphone permission under **Privacy & security → Microphone**.

## Running the Assistant

Activate the virtual environment if it is not already active:

```bat
.venv\Scripts\activate.bat
```

Start the application:

```bat
python assistant.py
```

Wait for the speech model to load, then speak a command into your microphone.

To stop the assistant, say:

```text
Stop listening
```

You can also press `Ctrl+C` in the terminal.

## Voice Commands

### Applications

| Voice Command | Action |
|---|---|
| Open Notepad | Launch Notepad |
| Open Calculator | Launch Calculator |
| Open Paint | Launch Paint |
| Open File Explorer | Open File Explorer |
| Open Command Prompt | Launch Command Prompt |
| Open Task Manager | Launch Task Manager |
| Open Chrome | Launch Google Chrome if found |
| Open Browser | Open your default browser |

### Websites

| Voice Command | Action |
|---|---|
| Open YouTube | Open YouTube |
| Open Google | Open Google |
| Open Facebook | Open Facebook |
| Open GitHub | Open GitHub |
| Open Gmail | Open Gmail |
| Open ChatGPT | Open ChatGPT |
| Open Reddit | Open Reddit |
| Open Stack Overflow | Open Stack Overflow |

### Google Search

Example commands:

```text
Search for Python tutorials
Search Google for Windows commands
```

The assistant opens a Google results page for the recognized search query.

### Exit Commands

```text
Stop listening
Exit assistant
Quit assistant
Goodbye
```

## Adding Websites

Open `assistant.py` and locate the `websites` dictionary inside `handle_command()`.

Add your website:

```python
websites = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "my website": "https://example.com",
}
```

Replace `https://example.com` with the actual website address.

## Adding Applications

Locate the `apps` dictionary inside `open_app()`.

Add a supported Windows application:

```python
apps = {
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "paint": ["mspaint.exe"],
    "my app": [r"C:\Path\To\MyApp.exe"],
}
```

Replace the example executable path with the actual application path.

> Security: Only add trusted applications. Do not execute arbitrary microphone-recognized text as a system command.

## How It Works

| Component | Purpose |
|---|---|
| Python | Main programming language |
| Vosk | Offline speech recognition |
| sounddevice | Captures microphone audio |
| pyttsx3 | Generates spoken responses locally |
| RapidFuzz | Matches commands despite minor transcription errors |
| webbrowser | Opens websites and search results |
| subprocess | Launches approved desktop applications |

## Offline Support

The assistant can recognize speech and launch installed applications without an internet connection once the required packages and model are installed.

However:

- Opening websites requires internet access.
- Google searches require internet access.
- Initial installation and model downloads require internet access.
- Speech recognition accuracy depends on the microphone, environment, language, and model.

The current implementation is a command-based assistant, not a full conversational AI.

## Troubleshooting

### ModuleNotFoundError

Install the dependencies:

```bat
python -m pip install -r requirements.txt
```

Make sure you use the same Python interpreter to install dependencies and run the assistant.

### Speech Model Not Found

Verify that this directory exists:

```text
model/vosk-model-small-en-us-0.15/
```

Ensure the model has been extracted correctly.

### Microphone Not Working

List available audio devices:

```bat
python -c "import sounddevice as sd; print(sd.query_devices())"
```

Check Windows microphone permissions and ensure the selected device supports the configured sample rate.

### Commands Are Misrecognized

Try the following:

- Speak clearly and pause briefly before giving a command.
- Reduce background noise.
- Move closer to the microphone.
- Check the selected input device.
- Use the RapidFuzz-enabled version of the script.
- Adjust the matching threshold carefully to avoid incorrect matches.

Fuzzy matching helps with minor transcription errors but cannot guarantee correct recognition.

### Chrome Does Not Open

Check whether Chrome is installed in one of the paths configured in `assistant.py`.

Alternatively, say:

```text
Open browser
```

This opens the default browser.

### Text-to-Speech Does Not Work

Verify that Windows audio output is working and that an installed Windows speech voice is available.

## Security and Privacy

- Speech recognition runs locally using Vosk.
- Microphone listening continues while the assistant is running.
- The current version does not include wake-word detection.
- Websites and searches use an internet connection.
- The application allowlist restricts which applications can be launched.
- No API keys or credentials are required.

## Development Roadmap

- [ ] Add wake-word activation, such as "Hey Clyde".
- [ ] Improve speech recognition accuracy.
- [ ] Add support for custom application paths.
- [ ] Store commands in a configuration file.
- [ ] Improve Cebuano-English mixed-language support.
- [ ] Add a graphical user interface.
- [ ] Create a portable Windows launcher.
- [ ] Explore local language models for more flexible commands.

## License

This project is currently a personal development project.

Before distributing it publicly, choose a license and review the licenses of the third-party libraries and speech model.

## Author

**Clyde Beloira Limbaga**

Python | Windows Automation | Offline Speech Recognition

---

**Quick Start**

```bat
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python assistant.py
```

Before running the final command, download and extract the Vosk speech model into the required `model` directory.
