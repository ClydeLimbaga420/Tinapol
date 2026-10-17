
# Voice Assistant (Tinapol)

A lightweight, locally running Python voice assistant for Windows. Control your computer using your microphone to open applications, launch websites, and search Google.

The project uses offline speech recognition and local text-to-speech. No cloud AI API key is required.

## Features

- Offline speech recognition using Vosk
- Local text-to-speech using pyttsx3
- Microphone input using sounddevice
- Floating on-screen orb overlay with live listening/speaking feedback
- Grammar-constrained command recognition for high accuracy
- Fuzzy command matching using RapidFuzz
- Misrecognition aliases for words the assistant commonly hears wrong
- Launch supported Windows applications
- Open websites using voice commands
- Open Facebook Reels by voice
- Scroll the window under the pointer with voice commands
- Search Google using spoken queries
- Automatic startup when you log in to Windows
- Simple Windows batch launcher (runs without a console window)
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
asst/
├── assistant.py
├── requirements.txt
├── start_assistant.bat
├── README.md
├── AGENTS.md
├── model/
│   └── vosk-model-small-en-us-0.15/
│       ├── am/
│       ├── conf/
│       ├── graph/
│       └── ...
└── .venv/          (created during setup)
```

The `.venv` folder is created during setup. A Vosk model must be present under `model/` (the small English model is already included).

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
mkdir asst
cd asst
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

The third-party dependencies are listed in `requirements.txt`:

```text
vosk
sounddevice
pyttsx3
rapidfuzz
pillow
```

Install the libraries:

```bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

> `tkinter` (used for the orb overlay) ships with Python, so no extra install is needed.

### 5. Download the Vosk Speech Model

A small English model is already included in this repository under:

```text
model/vosk-model-small-en-us-0.15/
```

If you need to re-download or want a more accurate model, see **Improving Recognition Accuracy** below. Official downloads:

- Small English: https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
- All models: https://alphacephei.com/vosk/models

Extract the ZIP so the folder sits directly under `model/`, and make sure it contains the model files, not just the archive.

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

Wait for the model to load. A floating **orb** appears near the bottom-right of your screen:

- **Cyan, slowly pulsing** — listening.
- **Green, quickly pulsing** — speaking.

Drag the orb to move it. To stop the assistant, say:

```text
Stop listening
```

You can also **right-click the orb → Quit**. Because the overlay runs its own GUI event loop, `Ctrl+C` in the terminal won't stop it.

## Automatic Startup on Windows

You can configure the assistant to start automatically when you sign in to Windows.

### 1. Check the Startup Launcher

The project already includes `start_assistant.bat` beside `assistant.py`, containing:

```bat
@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
start "" pythonw assistant.py
```

- `%~dp0` automatically locates the project folder containing the batch file.
- `pythonw` runs the assistant **without a console window** — only the orb is shown.
- If you prefer to see the console (useful for debugging), change `pythonw` to `python` and remove `start ""`.

### 2. Test the Launcher

Double-click `start_assistant.bat`.

Confirm that the orb appears and recognizes voice commands.

If it does not work, fix the problem before configuring automatic startup. For debugging, run `python assistant.py` directly so you can read the console output.

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

1. Open the project folder.
2. Right-click `start_assistant.bat`.
3. Select **Create shortcut**.
4. Copy the shortcut into the Windows Startup folder.

Keep the original batch file inside the project folder. Only the shortcut needs to be in Startup.

### 5. Test Automatic Startup

Sign out and sign back in, or restart the computer.

After logging in, Windows should launch the shortcut and start the assistant.

> **Important:** This starts the assistant when you sign in, not before the Windows login screen. The project folder, Python environment, and speech model must remain accessible.

### Disable Automatic Startup

To prevent the assistant from starting automatically:

1. Press `Win + R`.
2. Enter `shell:startup`.
3. Delete the assistant shortcut.

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
| Open Brave | Launch Brave if found |
| Open Spotify | Launch Spotify |
| Open VS Code | Launch Visual Studio Code if found |
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
| Open Canva | Open Canva |
| Open Claude | Open Claude |
| Open Reels | Open Facebook Reels |
| Open Portfolio | Open the author's portfolio |

### Scrolling

These commands scroll whatever window is **under the mouse cursor**, so keep the pointer over the page (e.g. the Facebook feed or Reels) when you speak:

| Voice Command | Action |
|---|---|
| Scroll / Scroll down | Scroll down |
| Scroll up | Scroll up |
| Page down | Scroll down one page |
| Page up | Scroll up one page |

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

Open `assistant.py` and locate the module-level `WEBSITES` dictionary. Add an entry:

```python
WEBSITES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "my website": "https://example.com",
}
```

Replace the example URL with your actual website address. The command vocabulary is read automatically, so the voice command and the recognition grammar update themselves on the next launch.

## Adding Applications

Adding an app takes **two edits**:

1. The `apps` dictionary inside `open_app()` (maps the name to the executable):

```python
apps = {
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "paint": ["mspaint.exe"],
    "my app": [r"C:\Path\To\MyApp.exe"],
}
```

2. The module-level `APPS` list (lets fuzzy matching and the grammar recognize the command):

```python
APPS = [
    "notepad",
    "calculator",
    # ...
    "my app",
]
```

If you skip step 2, the command will never reach `open_app()`.

Apps installed to user-specific locations (Chrome, Brave, Spotify, VS Code) are handled specially in `open_app()` with a list of candidate paths plus a fallback, rather than being added to the `apps` dictionary.

## Fixing Misrecognitions with Aliases

When the assistant consistently hears a word wrong, add it to the module-level `ALIASES` dictionary — it maps the misheard word to a command that already exists. Aliases can also be friendly nicknames, for example mapping "friend" to Claude and "workplace" to VS Code:

```python
ALIASES = {
    "kalk": "calculator",
    "note pad": "notepad",
    "can ba": "canva",
    "friend": "claude",
    "workplace": "vs code",
}
```

Alias values must be a canonical key that already exists in `WEBSITES` or `APPS`. This is usually the fastest way to fix accuracy for your own voice and microphone.

> Security: Only add trusted applications. Never execute arbitrary microphone-recognized text as a system command.

## Improving Recognition Accuracy

The assistant uses two passes: an open-vocabulary pass, then a grammar-constrained pass that only considers the known commands. If it still mishears you:

1. **Add aliases.** Run `python assistant.py`, watch the `You said:` and `(constrained: ...)` lines, then add each mishearing to `ALIASES`.
2. **Install a larger Vosk model.** Accuracy increases significantly with model size. Unzip any model into the `model/` folder; the assistant detects it automatically on the next launch. Suggested order:
   - `vosk-model-small-en-us-0.22` (~40 MB) — quick upgrade
   - `vosk-model-en-us-0.22` (~1.8 GB) — most accurate
3. **Select the correct microphone.** If the wrong device is used, the console prints the available input indices on startup failure. Set `MIC_DEVICE` near the top of `assistant.py` to your microphone's index:

```python
MIC_DEVICE = 1  # or None to use the system default
```

## How It Works

| Component | Purpose |
|---|---|
| Python | Main programming language |
| Vosk | Offline speech recognition (free + grammar-constrained recognizers) |
| sounddevice | Captures microphone audio |
| pyttsx3 | Generates spoken responses locally |
| RapidFuzz | Matches commands despite minor transcription errors |
| Pillow | Renders the glossy, anti-aliased orb sprite |
| tkinter | Draws the floating orb overlay and runs the event loop |
| webbrowser | Opens websites and search results |
| subprocess | Launches approved desktop applications |
| ctypes | Sends synthetic mouse-wheel events for scrolling |
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

Verify at least one model folder exists under `model/`, for example:

```text
model/vosk-model-small-en-us-0.15/
```

Ensure the model has been extracted correctly (the folder should contain `am/`, `conf/`, `graph/`, not just a ZIP).

### Microphone Not Working

List available audio devices and their indices:

```bat
python -c "import sounddevice as sd; print(sd.query_devices())"
```

Then set `MIC_DEVICE` near the top of `assistant.py` to the index of your microphone (use `None` for the system default). Also check Windows microphone permissions and ensure the device supports 16 kHz input.

### Commands Are Misrecognized

Try the following:

- Add the exact misheard words to the `ALIASES` dictionary (see **Improving Recognition Accuracy**).
- Install a larger Vosk model for better general accuracy.
- Set `MIC_DEVICE` to the correct input device.
- Speak clearly and pause briefly before and after each command.
- Reduce background noise and move closer to the microphone.

The grammar-constrained pass and fuzzy matching handle minor transcription errors, but cannot guarantee perfect recognition.

### Chrome or Brave Does Not Open

Check whether the browser is installed in one of the paths configured in `assistant.py`.

Alternatively, use:

```text
Open browser
```

This opens the default browser.

### Text-to-Speech Does Not Work

Verify that Windows audio output is working and that an installed speech voice is available.

### Assistant Does Not Start Automatically

The launcher runs without a console window (`pythonw`), so if something fails you won't see an error. Check the following:

1. Run `start_assistant.bat` manually and confirm the orb appears.
2. If you see nothing, run `python assistant.py` from a terminal to read the error output.
3. Confirm that `.venv\Scripts\activate.bat` exists.
4. Confirm that `assistant.py` and the Vosk model are in the expected locations.
5. Confirm that the shortcut is inside the folder opened by `shell:startup`.
6. Check whether Windows security software is blocking the script.

## Security and Privacy

- Speech recognition runs locally using Vosk.
- The assistant listens while the program is running.
- The current version does not include wake-word detection.
- Websites and searches use an internet connection.
- Only configured applications should be launchable through voice commands.
- No API keys or credentials are required.

## Development Roadmap

- [ ] Add wake-word activation, such as "Hey Clyde".
- [x] Improve speech recognition accuracy (grammar-constrained pass + aliases).
- [ ] Add custom application paths.
- [ ] Store commands in a configuration file.
- [ ] Improve Cebuano-English mixed-language support.
- [x] Add a graphical user interface (floating orb overlay).
- [ ] Improve startup and error handling.
- [ ] Explore local language models for more flexible commands.

## License

This project is currently a personal development project.

Before distributing it publicly, choose a license and review the licenses of third-party libraries and the speech model.

## Author

**Clyde Beloira Limbaga**

Python | Windows Automation | Offline Speech Recognition

## Quick Start

After completing the initial installation and model setup (the model is already included):

```bat
.venv\Scripts\activate.bat
python assistant.py
```

A floating orb appears; say "open Notepad", "open YouTube", or "stop listening".

To launch it automatically at sign-in, add a shortcut to `start_assistant.bat` inside the folder opened by `shell:startup` — it runs with no console window.
