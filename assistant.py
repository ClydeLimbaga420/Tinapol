
import json
import math
import os
import queue
import re
import subprocess
import sys
import tkinter as tk
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

# When launched without a console (pythonw), stdout/stderr are None and every
# print() would crash. Redirect them to a null stream so the orb runs cleanly.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "model" / "vosk-model-small-en-us-0.15"
SAMPLE_RATE = 16000

audio_queue = queue.Queue()
recognizer = None
constrained_recognizer = None
orb = None

# Set to a device index from sounddevice.query_devices() to force a microphone.
MIC_DEVICE = None

# Offline text-to-speech using Windows voices
speaker = pyttsx3.init()
speaker.setProperty("rate", 175)


def speak(message):
    print(f"Assistant: {message}")
    if orb is not None:
        orb.set_state("speaking")
    try:
        speaker.say(message)
        speaker.runAndWait()
    except Exception as error:
        print("Speech output error:", error)
    finally:
        if orb is not None:
            orb.set_state("listening")


def audio_callback(indata, frames, time_info, status):
    if status:
        print("Audio status:", status, file=sys.stderr)

    audio_queue.put(bytes(indata))


# ==========================================
# COMMAND VOCABULARY (shared by routing and the recognition grammar)
# ==========================================

WEBSITES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "facebook": "https://www.facebook.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "chatgpt": "https://chatgpt.com",
    "reddit": "https://www.reddit.com",
    "stackoverflow": "https://stackoverflow.com",
    "portfolio": "https://clydelimbaga.netlify.app",
    "canva": "https://www.canva.com",
}

APPS = [
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
    "brave",
    "brave browser",
    "spotify",
]

# Common misrecognitions and shorthand mapped to a canonical target.
ALIASES = {
    "yt": "youtube",
    "you tube": "youtube",
    "mail": "gmail",
    "g mail": "gmail",
    "chat gpt": "chatgpt",
    "gpt": "chatgpt",
    "stack overflow": "stackoverflow",
    "note pad": "notepad",
    "notice pad": "notepad",
    "note book": "notepad",
    "calculater": "calculator",
    "kalk": "calculator",
    "ms paint": "paint",
    "file manager": "file explorer",
    "my computer": "file explorer",
    "terminal": "command prompt",
    "console": "command prompt",
    "taskmanager": "task manager",
    "taskmgr": "task manager",
    "get help": "github",
    "can ba": "canva",
}

EXIT_PHRASES = [
    "stop listening",
    "exit assistant",
    "quit assistant",
    "goodbye",
]

OPEN_VERBS = ("open", "launch", "start", "go to")


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

    if app_name in ("brave", "brave browser"):
        candidates = [
            Path(r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"),
            Path(r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe"),
            Path.home() / r"AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe",
        ]

        for candidate in candidates:
            if candidate.exists():
                subprocess.Popen([str(candidate)])
                speak("Opening Brave")
                return

        speak("Brave was not found. Opening your default browser.")
        webbrowser.open("https://www.google.com")
        return

    if app_name == "spotify":
        candidates = [
            Path.home() / r"AppData\Roaming\Spotify\Spotify.exe",
            Path(r"C:\Program Files\Spotify\Spotify.exe"),
            Path(r"C:\Program Files (x86)\Spotify\Spotify.exe"),
        ]

        for candidate in candidates:
            if candidate.exists():
                subprocess.Popen([str(candidate)])
                speak("Opening Spotify")
                return

        # Fall back to the spotify: URI protocol (also handles the Store app).
        webbrowser.open("spotify:")
        speak("Opening Spotify")
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


def strip_open_prefix(text):
    return re.sub(r"^(open|launch|start|go to)\s+", "", text).strip()


def resolve_target(text):
    """Map recognized text to a canonical website key or app name, or None."""
    text = text.strip()
    targets = list(WEBSITES.keys()) + APPS + list(ALIASES.keys())
    target = text if text in targets else match_command(text, targets, 78)
    if target in ALIASES:
        target = ALIASES[target]
    return target


def build_grammar():
    """Phrases the recognizer is allowed to consider for commands.

    Constraining the vocabulary to exactly these phrases makes command
    recognition dramatically more accurate than open-vocabulary listening.
    """
    phrases = set(EXIT_PHRASES)
    phrases.update(["search for", "search google for"])
    for verb in OPEN_VERBS:
        for target in list(WEBSITES.keys()) + APPS + list(ALIASES.keys()):
            phrases.add(f"{verb} {target}")
    return json.dumps(sorted(phrases))


def recognize_constrained(pcm_bytes):
    """Second-pass recognition of one utterance using the command grammar."""
    if constrained_recognizer is None or not pcm_bytes:
        return ""
    if constrained_recognizer.AcceptWaveform(pcm_bytes):
        return json.loads(constrained_recognizer.Result()).get("text", "").strip()
    return json.loads(constrained_recognizer.FinalResult()).get("text", "").strip()


def find_model_dir():
    """Prefer a larger/more accurate Vosk model if one is installed."""
    model_root = BASE_DIR / "model"
    preferred = [
        "vosk-model-en-us-0.22",
        "vosk-model-en-us-0.22-lgraph",
        "vosk-model-small-en-us-0.22",
        "vosk-model-small-en-us-0.15",
    ]
    for name in preferred:
        candidate = model_root / name
        if candidate.exists():
            return candidate
    if model_root.exists():
        subdirs = sorted(p for p in model_root.iterdir() if p.is_dir())
        if subdirs:
            return subdirs[0]
    return MODEL_DIR


def handle_command(command, pcm=b""):
    command = normalize_command(command)

    if not command:
        return True

    print(f"\nYou said: {command}")

    if match_command(command, EXIT_PHRASES, 85):
        speak("Goodbye")
        return False

    cleaned = strip_open_prefix(command)
    target = resolve_target(cleaned)

    # Second pass: re-run the SAME utterance against the constrained grammar.
    # This recovers commands the open-vocabulary pass misheard.
    if target is None and pcm:
        constrained = normalize_command(recognize_constrained(pcm))

        if constrained:
            print(f"  (constrained: {constrained})")

            if match_command(constrained, EXIT_PHRASES, 85):
                speak("Goodbye")
                return False

            target = resolve_target(strip_open_prefix(constrained))

    if target:
        if target in WEBSITES:
            webbrowser.open(WEBSITES[target])
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



class Orb:
    """A small always-on-top circular overlay that reflects the listening state.

    Audio and speech run on the tkinter main thread: the microphone callback
    only enqueues bytes, and ``_poll`` drains the queue from the event loop.
    Keeping pyttsx3 on a single thread avoids Windows COM threading problems.
    """

    SIZE = 150
    TRANSPARENT = "#010203"
    COLORS = {
        "listening": {"core": "#00d4ff", "glow": "#0a6f8f"},
        "speaking": {"core": "#7cfc00", "glow": "#2e7d32"},
    }

    def __init__(self):
        self.state = "listening"
        self.phase = 0.0
        self.stream = None
        self.closed = False
        self._drag_offset = (0, 0)
        self._buffer = []

        self.window = tk.Tk()
        self.window.title("Assistant")
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.configure(bg=self.TRANSPARENT)
        try:
            self.window.attributes("-transparentcolor", self.TRANSPARENT)
        except tk.TclError:
            pass

        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()
        x = screen_w - self.SIZE - 40
        y = screen_h - self.SIZE - 80
        self.window.geometry(f"{self.SIZE}x{self.SIZE}+{x}+{y}")

        self.canvas = tk.Canvas(
            self.window,
            width=self.SIZE,
            height=self.SIZE,
            bg=self.TRANSPARENT,
            highlightthickness=0,
        )
        self.canvas.pack()

        self.outer = self.canvas.create_oval(0, 0, 0, 0, outline="")
        self.mid = self.canvas.create_oval(0, 0, 0, 0, outline="")
        self.core = self.canvas.create_oval(0, 0, 0, 0, outline="")

        self.menu = tk.Menu(self.window, tearoff=0)
        self.menu.add_command(label="Quit", command=self.quit)

        self.canvas.bind("<ButtonPress-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<Button-3>", self._popup)

    def set_state(self, state):
        if state in self.COLORS:
            self.state = state

    def _circle(self, item, radius):
        center = self.SIZE / 2
        self.canvas.coords(
            item,
            center - radius,
            center - radius,
            center + radius,
            center + radius,
        )

    def _draw(self):
        colors = self.COLORS[self.state]
        self.phase += 0.35 if self.state == "speaking" else 0.16
        pulse = (math.sin(self.phase) + 1) / 2

        if self.state == "speaking":
            core_r = 32 + pulse * 6
            mid_r = 46 + pulse * 9
            outer_r = 60 + pulse * 12
        else:
            core_r = 30 + pulse * 2
            mid_r = 42 + pulse * 4
            outer_r = 54 + pulse * 7

        self._circle(self.outer, outer_r)
        self._circle(self.mid, mid_r)
        self._circle(self.core, core_r)

        self.canvas.itemconfig(self.outer, fill=colors["glow"], stipple="gray12")
        self.canvas.itemconfig(self.mid, fill=colors["glow"], stipple="gray50")
        self.canvas.itemconfig(self.core, fill=colors["core"])

        if not self.closed:
            self.window.after(40, self._draw)

    def _start_drag(self, event):
        self._drag_offset = (event.x, event.y)

    def _drag(self, event):
        x = self.window.winfo_x() + event.x - self._drag_offset[0]
        y = self.window.winfo_y() + event.y - self._drag_offset[1]
        self.window.geometry(f"+{x}+{y}")

    def _popup(self, event):
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def _poll(self):
        processed = 0
        try:
            while processed < 4:
                audio_data = audio_queue.get_nowait()
                processed += 1
                self._buffer.append(audio_data)

                if recognizer.AcceptWaveform(audio_data):
                    result = json.loads(recognizer.Result())
                    text = result.get("text", "").strip()
                    pcm = b"".join(self._buffer)
                    self._buffer = []

                    if text or pcm:
                        if not handle_command(text, pcm):
                            self.quit()
                            return
        except queue.Empty:
            pass
        except Exception as error:
            print("Recognizer error:", error)

        if not self.closed:
            self.window.after(40, self._poll)

    def run(self):
        try:
            self.stream = sd.RawInputStream(
                samplerate=SAMPLE_RATE,
                blocksize=8000,
                dtype="int16",
                channels=1,
                device=MIC_DEVICE,
                callback=audio_callback,
            )
            self.stream.start()
        except Exception as error:
            print("ERROR:", error)
            print("Check your microphone and installed libraries.")
            try:
                print("Available input devices:")
                for index, device in enumerate(sd.query_devices()):
                    if device.get("max_input_channels", 0) > 0:
                        print(f"  {index}: {device['name']}")
            except Exception:
                pass
            print("Set MIC_DEVICE in assistant.py to your microphone's index.")
            self.quit()
            return

        print("Voice assistant is ready.")
        print("Say 'open Notepad', 'open YouTube', or 'stop listening'.")

        self._draw()
        self.window.after(40, self._poll)
        self.window.mainloop()

    def quit(self):
        self.closed = True
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
        try:
            self.window.destroy()
        except tk.TclError:
            pass


def main():
    global recognizer, constrained_recognizer, orb

    model_dir = find_model_dir()

    if not model_dir.exists():
        print("ERROR: Speech model not found.")
        print("Expected model folder:", model_dir)
        print("Download and extract the Vosk English model first.")
        return

    print("Loading offline speech model from:", model_dir)
    model = Model(str(model_dir))
    recognizer = KaldiRecognizer(model, SAMPLE_RATE)
    constrained_recognizer = KaldiRecognizer(model, SAMPLE_RATE, build_grammar())

    orb = Orb()
    orb.run()


if __name__ == "__main__":
    main()
