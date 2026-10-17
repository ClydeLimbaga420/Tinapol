
import json
import queue
import re
import subprocess
import sys
import urllib.parse
import webbrowser
from pathlib import Path
from rapidfuzz import process, fuzz

import sounddevice as sd
import pyttsx3
from vosk import Model, KaldiRecognizer

# ==========================================
# LOCAL WINDOWS VOICE ASSISTANT
# ==========================================

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "model" / "vosk-model-small-en-us-0.15"
SAMPLE_RATE = 16000

audio_queue = queue.Queue()
recognizer = None

# Offline text-to-speech using Windows voices
speaker = pyttsx3.init()
speaker.setProperty("rate", 175)


def speak(message):
    print(f"Assistant: {message}")
    try:
        speaker.say(message)
        speaker.runAndWait()
    except Exception as error:
        print("Speech output error:", error)


def audio_callback(indata, frames, time_info, status):
    if status:
        print("Audio status:", status, file=sys.stderr)

    audio_queue.put(bytes(indata))


def open_app(app_name):
    """Launch only applications explicitly listed here."""
    apps = {
        "notepad": ["notepad.exe"],
        "calculator": ["calc.exe"],
        "calc": ["calc.exe"],
        "paint": ["mspaint.exe"],
        "file explorer": ["explorer.exe"],
        "explorer": ["explorer.exe"],
        "command prompt": ["cmd.exe"],
        "cmd": ["cmd.exe"],
        "task manager": ["taskmgr.exe"],
    }

    if app_name in apps:
        try:
            subprocess.Popen(apps[app_name])
            speak(f"Opening {app_name}")
        except OSError as error:
            speak(f"Could not open {app_name}")
            print(error)
        return

    # Open common browsers by their installed executable.
    if app_name in ("chrome", "google chrome"):
        candidates = [
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
            Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe",
        ]

        for candidate in candidates:
            if candidate.exists():
                subprocess.Popen([str(candidate)])
                speak("Opening Google Chrome")
                return

        speak("Chrome was not found. Opening your default browser.")
        webbrowser.open("https://www.google.com")
        return

    if app_name in ("browser", "web browser", "default browser"):
        webbrowser.open("https://www.google.com")
        speak("Opening your browser")
        return

    speak(f"I don't know how to open {app_name} yet")


def normalize_command(command):
    command = command.lower().strip()

    # Remove common filler words and punctuation.
    command = re.sub(r"[^\w\s]", "", command)
    command = re.sub(
        r"\b(please|uh|um|hey|okay|ok)\b",
        "",
        command
    )

    return " ".join(command.split())


def match_command(command, choices, threshold=75):
    result = process.extractOne(
        command,
        choices,
        scorer=fuzz.ratio
    )

    if result and result[1] >= threshold:
        return result[0]

    return None


def handle_command(command):
    command = normalize_command(command)

    if not command:
        return True

    print(f"\nYou said: {command}")

    # Exit commands
    exit_phrases = [
        "stop listening",
        "exit assistant",
        "quit assistant",
        "goodbye",
    ]

    if match_command(command, exit_phrases, 85):
        speak("Goodbye")
        return False

    # Remove common ways of saying "open"
    cleaned = re.sub(
        r"^(open|launch|start|go to)\s+",
        "",
        command
    ).strip()

    # Websites and applications
    websites = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "facebook": "https://www.facebook.com",
        "github": "https://github.com",
        "gmail": "https://mail.google.com",
        "chatgpt": "https://chatgpt.com",
        "reddit": "https://www.reddit.com",
        "stackoverflow": "https://stackoverflow.com",
        "portfolio": "https://clydelimbaga.netlify.app",
    }

    apps = [
        "notepad",
        "calculator",
        "calc",
        "paint",
        "file explorer",
        "explorer",
        "command prompt",
        "cmd",
        "task manager",
        "chrome",
        "google chrome",
        "browser",
    ]

    targets = list(websites.keys()) + apps

    # Try exact matching first, then fuzzy matching.
    target = cleaned if cleaned in targets else None

    if target is None:
        target = match_command(cleaned, targets, 78)

    if target:
        if target in websites:
            webbrowser.open(websites[target])
            speak(f"Opening {target}")
        else:
            open_app(target)
        return True

    # Search Google when the user explicitly requests a search.
    for phrase in ("search for ", "search google for ", "google "):
        if command.startswith(phrase):
            query = command[len(phrase):].strip()

            if query:
                url = (
                    "https://www.google.com/search?q="
                    + urllib.parse.quote_plus(query)
                )
                webbrowser.open(url)
                speak(f"Searching for {query}")
            return True

    speak("Sorry, I didn't understand. Please try again.")
    return True



def main():
    global recognizer

    if not MODEL_DIR.exists():
        print("ERROR: Speech model not found.")
        print("Expected model folder:", MODEL_DIR)
        print("Download and extract the Vosk English model first.")
        return

    print("Loading offline speech model...")
    model = Model(str(MODEL_DIR))
    recognizer = KaldiRecognizer(model, SAMPLE_RATE)

    print("Voice assistant is ready.")
    print("Recognition runs locally on your computer.")
    print("Say 'open Notepad', 'open YouTube', or 'stop listening'.")
    print("Listening for commands...\n")

    try:
        with sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=8000,
            dtype="int16",
            channels=1,
            callback=audio_callback,
        ):
            running = True

            while running:
                audio_data = audio_queue.get()

                if recognizer.AcceptWaveform(audio_data):
                    result = json.loads(recognizer.Result())
                    command = result.get("text", "").strip()

                    if command:
                        running = handle_command(command)

    except KeyboardInterrupt:
        print("\nAssistant stopped.")
    except Exception as error:
        print("\nERROR:", error)
        print("Check your microphone and installed libraries.")


if __name__ == "__main__":
    main()
