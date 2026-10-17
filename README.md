
# Voice Assistant (Tinapol)

A lightweight, locally running Python voice assistant for Windows. Control your computer using your microphone to open applications, launch websites, and search Google.

The project uses offline speech recognition and local text-to-speech. No cloud AI API key is required.

## Features

- Offline speech recognition using Vosk
- Local text-to-speech using pyttsx3
- Microphone input using sounddevice
- Fuzzy command matching using RapidFuzz
- Launch supported Windows applications
- Open websites using voice commands
- Search Google using spoken queries
- Automatic startup when you log in to Windows
- Simple Windows batch launcher
- No cloud-based speech recognition required

## Requirements

- Windows 10 or Windows 11
- Python 3.10 or newer recommended
- A working microphone
- Internet connection for initial downloads and online websites
- Disk space for dependencies and the speech recognition model

> Python 3.14 may work, but if a dependency fails to install, try Python 3.12 or 3.13.

## Project Structure

```text
ClydeVoiceAssistant/
├── assistant.py
├── start_assistant.bat
├── requirements.txt
├── README.md
├── .gitignore
├── .venv/
└── model/
    └── vosk-model-small-en-us-0.15/
        ├── am/
        ├── conf/
        ├── graph/
        └── ...
```

The `.venv` folder is created during setup. The Vosk model must be downloaded separately.

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

If creating a new project:

```bat
mkdir ClydeVoiceAssistant
cd ClydeVoiceAssistant
```

If the project already exists, navigate to its directory instead.

### 3. Create a Virtual Environment

A virtual environment keeps the project's dependencies separate from other Python projects.

```bat
python -m venv .venv
```

Activate it:

```bat
.venv\Scripts\activate.bat
```

### 4. Install Dependencies

Create a file named `requirements.txt` with the following contents:

```text
vosk
sounddevice
pyttsx3
rapidfuzz
```

Install the libraries:

```bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 5. Download the Vosk Speech Model

Download the small English speech recognition model:

https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip

Official model directory:

https://alphacephei.com/vosk/models

Extract the ZIP archive into the project's `model` directory.

The resulting directory should be:

```text
model/vosk-model-small-en-us-0.15/
```

Ensure that the extracted folder contains the model files, not just the ZIP archive.

### 6. Configure Your Microphone

1. Open Windows Settings.
2. Navigate to **System → Sound**.
3. Select your preferred input device.
4. Test the microphone.
5. Open **Privacy & security → Microphone** and allow desktop applications to access it.

## Running the Assistant Manually

Activate the virtual environment:

```bat
.venv\Scripts\activate.bat
```

Run the assistant:

```bat
python assistant.py
```

Wait for the model to load, then speak into your microphone.

To stop the assistant, say:

```text
Stop listening
```

You can also press `Ctrl+C` in the terminal.

## Automatic Startup on Windows

You can configure Clyde Voice Assistant to start automatically when you sign in to Windows.

### 1. Create the Startup Launcher

Create a file named `start_assistant.bat` in the main project folder, beside `assistant.py`.

Paste the following code:

```bat
@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python assistant.py
pause
```

The `%~dp0` variable automatically locates the project folder containing the batch file.

The launcher activates the virtual environment and starts the assistant. The `pause` command keeps the terminal open if the program exits, allowing you to inspect errors.

### 2. Test the Launcher

Double-click `start_assistant.bat`.

Confirm that the assistant starts correctly and recognizes voice commands.

If it does not work, fix the problem before configuring automatic startup.

### 3. Open the Windows Startup Folder

Press:

```text
Win + R
```

Enter:

```text
shell:startup
```

Press Enter.

Windows opens your personal Startup folder.

### 4. Add the Launcher Shortcut

1. Open the `ClydeVoiceAssistant` project folder.
2. Right-click `start_assistant.bat`.
3. Select **Create shortcut**.
4. Copy the shortcut into the Windows Startup folder.

Keep the original batch file inside the project folder. Only the shortcut needs to be in Startup.

### 5. Test Automatic Startup

Sign out and sign back in, or restart the computer.

After logging in, Windows should launch the shortcut and start Clyde Voice Assistant.

> **Important:** This starts the assistant when you sign in, not before the Windows login screen. The project folder, Python environment, and speech model must remain accessible.

### Disable Automatic Startup

To prevent the assistant from starting automatically:

1. Press `Win + R`.
2. Enter `shell:startup`.
3. Delete the Clyde Voice Assistant shortcut.

This does not delete your project or its dependencies.

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
| Open Chrome | Launch Chrome if found |
| Open Browser | Open the default browser |

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

The assistant opens Google search results for the recognized query.

### Exit Commands

```text
Stop listening
Exit assistant
Quit assistant
Goodbye
```

## Adding Websites

Open `assistant.py` and locate the `websites` dictionary inside `handle_command()`.

Add a website:

```python
websites = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "my website": "https://example.com",
}
```

Replace the example URL with your actual website address.

## Adding Applications

Locate the `apps` dictionary inside `open_app()`.

Add an application:

```python
apps = {
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "paint": ["mspaint.exe"],
    "my app": [r"C:\Path\To\MyApp.exe"],
}
```

Replace the example path with the actual executable path.

> Security: Only add trusted applications. Never execute arbitrary microphone-recognized text as a system command.

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
| Windows Startup | Launches the assistant after user sign-in |

## Offline Support

The assistant can recognize speech and launch supported applications without an internet connection after installing the dependencies and downloading the model.

However:

- Opening websites requires internet access.
- Google searches require internet access.
- Initial installation and model downloads require internet access.
- Recognition accuracy depends on the microphone, background noise, language, and model.

The current implementation is a command-based assistant, not a full conversational AI.

## Troubleshooting

### ModuleNotFoundError

Install the dependencies:

```bat
python -m pip install -r requirements.txt
```

Make sure you use the same Python interpreter for installation and execution.

### Speech Model Not Found

Verify this directory exists:

```text
model/vosk-model-small-en-us-0.15/
```

Ensure the model has been extracted correctly.

### Microphone Not Working

List available audio devices:

```bat
python -c "import sounddevice as sd; print(sd.query_devices())"
```

Check Windows microphone permissions and ensure the selected input device supports the configured sample rate.

### Commands Are Misrecognized

Try the following:

- Speak clearly and pause briefly before and after each command.
- Reduce background noise.
- Move closer to the microphone.
- Check the selected input device.
- Use the RapidFuzz-enabled version of the script.
- Adjust the matching threshold carefully to avoid incorrect matches.

Fuzzy matching can help with minor transcription errors but cannot guarantee accurate recognition.

### Chrome Does Not Open

Check whether Chrome is installed in one of the paths configured in `assistant.py`.

Alternatively, use:

```text
Open browser
```

This opens the default browser.

### Text-to-Speech Does Not Work

Verify that Windows audio output is working and that an installed speech voice is available.

### Assistant Does Not Start Automatically

Check the following:

1. Run `start_assistant.bat` manually.
2. Confirm that `.venv\Scripts\activate.bat` exists.
3. Confirm that `assistant.py` and the Vosk model are in the expected locations.
4. Confirm that the shortcut is inside the folder opened by `shell:startup`.
5. Check whether Windows security software is blocking the script.

## Security and Privacy

- Speech recognition runs locally using Vosk.
- The assistant listens while the program is running.
- The current version does not include wake-word detection.
- Websites and searches use an internet connection.
- Only configured applications should be launchable through voice commands.
- No API keys or credentials are required.

## Development Roadmap

- [ ] Add wake-word activation, such as "Hey Clyde".
- [ ] Improve speech recognition accuracy.
- [ ] Add custom application paths.
- [ ] Store commands in a configuration file.
- [ ] Improve Cebuano-English mixed-language support.
- [ ] Add a graphical user interface.
- [ ] Improve startup and error handling.
- [ ] Explore local language models for more flexible commands.

## License

This project is currently a personal development project.

Before distributing it publicly, choose a license and review the licenses of third-party libraries and the speech model.

## Author

**Clyde Beloira Limbaga**

Python | Windows Automation | Offline Speech Recognition

## Quick Start

After completing the initial installation and model setup:

```bat
.venv\Scripts\activate.bat
python assistant.py
```

To launch it automatically at sign-in, create `start_assistant.bat`, test it, and add a shortcut to the folder opened by `shell:startup`.
