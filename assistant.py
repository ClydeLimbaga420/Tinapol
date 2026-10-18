
import ctypes
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
import winreg
from pathlib import Path
from rapidfuzz import process, fuzz

import sounddevice as sd
import pyttsx3
from vosk import Model, KaldiRecognizer
from PIL import Image, ImageDraw, ImageFilter, ImageTk

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
    "claude": "https://claude.ai",
    "reels": "https://www.facebook.com/reel/",
    "enma": "https://www.enma.lol/home",
    "netacad": "https://www.netacad.com/portal/dashboard",
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
    "vs code",
    "vscode",
    "word",
    "excel",
    "powerpoint",
    "outlook",
    "onenote",
    "access",
    "publisher",
]

CLOSEABLE_APPS = {
    "notepad": ["notepad.exe"],
    "calculator": ["CalculatorApp.exe", "calc.exe"],
    "calc": ["CalculatorApp.exe", "calc.exe"],
    "paint": ["mspaint.exe"],
    "command prompt": ["cmd.exe"],
    "cmd": ["cmd.exe"],
    "task manager": ["taskmgr.exe"],
    "chrome": ["chrome.exe"],
    "google chrome": ["chrome.exe"],
    "brave": ["brave.exe"],
    "brave browser": ["brave.exe"],
    "spotify": ["Spotify.exe"],
    "vs code": ["Code.exe"],
    "vscode": ["Code.exe"],
    "word": ["winword.exe"],
    "excel": ["excel.exe"],
    "powerpoint": ["powerpnt.exe"],
    "outlook": ["outlook.exe"],
    "onenote": ["onenote.exe"],
    "access": ["msaccess.exe"],
    "publisher": ["mspub.exe"],
}

EXPLORER_NAMES = ("file explorer", "explorer")

CLOSE_APP_TARGETS = list(CLOSEABLE_APPS) + list(EXPLORER_NAMES)

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
    "friend": "claude",
    "workplace": "vs code",
    "v s code": "vs code",
    "facebook reels": "reels",
    "reel": "reels",
    "watch": "enma",
    "net acad": "netacad",
    "net academy": "netacad",
    "netacadcom": "netacad",
    "cisco": "netacad",
    "skills for all": "netacad",
    "skillsforall": "netacad",
    "microsoft word": "word",
    "ms word": "word",
    "microsoft excel": "excel",
    "ms excel": "excel",
    "power point": "powerpoint",
    "ms powerpoint": "powerpoint",
    "microsoft powerpoint": "powerpoint",
    "one note": "onenote",
    "microsoft outlook": "outlook",
    "microsoft access": "access",
    "microsoft publisher": "publisher",
}

EXIT_PHRASES = [
    "stop listening",
    "exit assistant",
    "quit assistant",
    "goodbye",
]

# Scroll the window under the mouse cursor (works on Facebook feed, Reels, etc.).
SCROLL_COMMANDS = [
    "scroll",
    "scroll down",
    "scroll up",
    "page down",
    "page up",
]

# Close the focused tab (Ctrl+W) or the focused window (Alt+F4).
CLOSE_TAB_COMMANDS = [
    "close",
    "close tab",
    "close this tab",
    "close the tab",
    "close current tab",
    "close active tab",
    "close browser tab",
    "close that tab",
]

CLOSE_WINDOW_COMMANDS = [
    "close window",
    "close this window",
    "close the window",
    "close app",
    "close program",
    "close that window",
]

CLOSE_BLOCKED = {
    "",
    "tab",
    "window",
    "app",
    "program",
    "page",
    "browser tab",
    "current tab",
    "current window",
    "everything",
}

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

    if app_name in ("vs code", "vscode"):
        candidates = [
            Path.home() / r"AppData\Local\Programs\Microsoft VS Code\Code.exe",
            Path(r"C:\Program Files\Microsoft VS Code\Code.exe"),
            Path(r"C:\Program Files (x86)\Microsoft VS Code\Code.exe"),
        ]

        for candidate in candidates:
            if candidate.exists():
                subprocess.Popen([str(candidate)])
                speak("Opening Visual Studio Code")
                return

        speak("Visual Studio Code was not found. Opening the web editor.")
        webbrowser.open("https://vscode.dev")
        return

    office = {
        "word": "winword.exe",
        "excel": "excel.exe",
        "powerpoint": "powerpnt.exe",
        "outlook": "outlook.exe",
        "onenote": "onenote.exe",
        "access": "msaccess.exe",
        "publisher": "mspub.exe",
    }

    if app_name in office:
        exe = office[app_name]
        install_path = None

        for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                with winreg.OpenKey(
                    root,
                    rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe}",
                ) as key:
                    install_path = winreg.QueryValueEx(key, "")[0]
                break
            except OSError:
                continue

        if not install_path:
            speak(f"{app_name} is not installed")
            return

        try:
            subprocess.Popen([install_path.strip('"')])
            speak(f"Opening {app_name}")
        except OSError as error:
            print(error)
            speak(f"Could not open {app_name}")
        return

    speak(f"I don't know how to open {app_name} yet")


def scroll_window(command):
    """Scroll the window under the mouse cursor using synthetic wheel events.

    Uses only ctypes so no extra dependency is needed. Scrolling happens at the
    pointer location, so it works on whatever the user is looking at (e.g. the
    Facebook feed or Reels) without the assistant needing window focus.
    """
    mouseeventf_wheel = 0x0800
    wheel_delta = 120
    notches = -4  # negative wheel delta scrolls the content down

    if "up" in command:
        notches = -notches

    try:
        ctypes.windll.user32.mouse_event(
            mouseeventf_wheel, 0, 0, wheel_delta * notches, 0
        )
    except Exception as error:
        print("Scroll error:", error)


VK_CONTROL = 0x11
VK_MENU = 0x12
VK_W = 0x57
VK_F4 = 0x73
VK_TAB = 0x09
KEYEVENTF_KEYUP = 0x0002
WM_CLOSE = 0x0010


def send_key_chord(vk_codes):
    """Press and release a combination of virtual-key codes together.

    Uses ctypes only, matching scroll_window(), so no extra dependency is
    needed.
    """
    for vk in vk_codes:
        ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
    for vk in reversed(vk_codes):
        ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)


def close_browser_tab_by_name(name):
    """Find a browser window whose title matches the site name and close its tab."""
    name = (name or "").lower()
    browser_classes = ("Chrome_WidgetWin_1", "MozillaWindowClass", "YandexBrowser_WidgetWin_1", "msedge")

    user32 = ctypes.windll.user32
    found_hwnd = None

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def enum(hwnd, _):
        nonlocal found_hwnd
        if found_hwnd:
            return True
        if not user32.IsWindowVisible(hwnd):
            return True
        cname = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cname, 256)
        if cname.value not in browser_classes:
            return True
        tbuf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, tbuf, 512)
        title = tbuf.value.lower()
        if not title:
            return True
        if name in title or any(k in title for k in (name,)):
            found_hwnd = hwnd
            return False
        return True

    try:
        user32.EnumWindows(enum, 0)
    except Exception:
        found_hwnd = None

    if not found_hwnd:
        return False

    hwnd = found_hwnd
    try:
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.SetForegroundWindow(hwnd)
        ctypes.windll.kernel32.Sleep(100)
    except Exception:
        pass

    try:
        send_key_chord((VK_CONTROL, VK_W))
        return True
    except Exception as error:
        print("Close tab by name error:", error)
        return False


def close_focused(command):
    """Close the active tab (Ctrl+W) or the active window (Alt+F4)."""
    is_window = any(
        word in command
        for word in (
            "window",
            "app",
            "program",
            "entire window",
            "the window",
            "this window",
            "that window",
        )
    )
    is_tab = any(
        word in command
        for word in (
            "tab",
            "browser tab",
            "current tab",
            "active tab",
            "this tab",
            "that tab",
        )
    )

    try:
        if is_window and not is_tab:
            send_key_chord((VK_MENU, VK_F4))
        else:
            send_key_chord((VK_CONTROL, VK_W))
    except Exception as error:
        print("Close error:", error)
        speak("I could not close that")
        return

    speak("Closing the window" if (is_window and not is_tab) else "Closing the tab")


def close_explorer_windows():
    """Close File Explorer folder windows without killing the Windows shell.

    The taskbar and desktop are also explorer.exe, so taskkill would take down
    the whole shell. Each visible folder window is sent WM_CLOSE instead,
    which needs no focus and leaves the shell running.
    """
    user32 = ctypes.windll.user32
    folder_windows = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def collect(hwnd, _lparam):
        if user32.IsWindowVisible(hwnd):
            class_name = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, class_name, 256)
            if class_name.value in ("CabinetWClass", "ExploreWClass"):
                folder_windows.append(hwnd)
        return True

    user32.EnumWindows(collect, 0)

    for hwnd in folder_windows:
        user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)

    return len(folder_windows)


def close_app(app_name):
    """Close every window of a named app wherever it is, not just the focused one.

    Only allowlisted executables from CLOSEABLE_APPS are ever passed to
    taskkill; recognized text is never executed as a command.
    """
    if app_name in EXPLORER_NAMES:
        closed = close_explorer_windows()
        speak("Closing File Explorer" if closed else "File Explorer isn't open")
        return True

    exe_names = CLOSEABLE_APPS.get(app_name)
    if not exe_names:
        speak(f"I don't know how to close {app_name} yet")
        return True

    result = None
    try:
        for exe in exe_names:
            result = subprocess.run(
                ["taskkill", "/F", "/IM", exe],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                speak(f"Closing {app_name}")
                return True
    except Exception as error:
        print("Close error:", error)
        speak(f"I could not close {app_name}")
        return True

    stderr = (result.stderr or "") if result else ""
    if "not found" in stderr.lower() or "no running" in stderr.lower():
        speak(f"{app_name} isn't running")
    else:
        print("taskkill error:", stderr.strip())
        speak(f"I could not close {app_name}")
    return True


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


def resolve_close_app(command):
    """Map "close <app>" to a canonical closable app name, or None.

    Tab/window phrases (e.g. "close tab") fall through to the generic close
    commands, so this only fires when the name resolves to a closable app.
    """
    match = re.match(r"^close\s+(.*)$", command)
    if not match:
        return None

    name = re.sub(
        r"^(?:(?:the|this|app|program)\s+)+",
        "",
        match.group(1),
    ).strip()

    if name in CLOSE_BLOCKED:
        return None

    # If user says "close tab", "close browser tab" etc - don't treat as app name
    tab_words = ("tab", "browser tab", "current tab", "active tab", "this tab", "that tab")
    if any(w in name for w in tab_words):
        return None

    if name in ALIASES:
        name = ALIASES[name]

    if name in CLOSE_APP_TARGETS:
        return name

    return match_command(name, CLOSE_APP_TARGETS, 78)


def build_grammar():
    """Phrases the recognizer is allowed to consider for commands.

    Constraining the vocabulary to exactly these phrases makes command
    recognition dramatically more accurate than open-vocabulary listening.
    """
    phrases = set(EXIT_PHRASES)
    phrases.update(SCROLL_COMMANDS)
    phrases.update(CLOSE_TAB_COMMANDS)
    phrases.update(CLOSE_WINDOW_COMMANDS)
    phrases.add("close tab")
    phrases.add("close tabs")
    phrases.add("close browser tab")
    phrases.add("close browser tabs")
    # allow closing specific tabs by target name
    for target in list(WEBSITES.keys()) + APPS:
        phrases.add(f"close tab {target}")
        phrases.add(f"close browser tab {target}")
    for target in CLOSE_APP_TARGETS:
        phrases.add(f"close {target}")
    for alias, canonical in ALIASES.items():
        if canonical in CLOSE_APP_TARGETS:
            phrases.add(f"close {alias}")
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

    scroll = match_command(command, SCROLL_COMMANDS, 82)
    if scroll:
        scroll_window(scroll)
        return True

    close_target = resolve_close_app(command)
    if close_target:
        close_app(close_target)
        return True

    # Close specific browser tab by name/site (broader patterns)
    m = re.match(r"^close\s+(?:the\s+|this\s+|that\s+|a\s+)?(?:browser\s+)?tab(?:s)?\s+(?:for\s+|on\s+|in\s+|of\s+)?(.+)$", command)
    if not m:
        m = re.match(r"^close\s+(.+)\s+tab(?:s)?$", command)
    if m:
        site = m.group(1).strip()
        # skip generic words
        if site in ("current", "active", "this", "that", "the", "browser"):
            pass  # fall through to generic
        else:
            cleaned_site = strip_open_prefix(site)
            t = resolve_target(cleaned_site)
            if not t and cleaned_site:
                candidates = list(WEBSITES.keys()) + APPS + ["youtube", "facebook", "google", "gmail", "reddit", "chatgpt", "github", "stackoverflow"]
                t = match_command(cleaned_site, candidates, 75)
            if not t:
                t = cleaned_site
            if close_browser_tab_by_name(t):
                speak(f"Closing {t} tab")
                return True
            speak(f"Couldn't find {t} tab")
            return True

    # Check for "close tab" or "close browser tab" specifically (current)
    if re.search(r"^close\s+(?:browser\s+)?tab(?:s)?$", command) or command in ("close tab", "close the tab", "close current tab", "close active tab"):
        close_focused("close tab")
        return True

    close_cmd = match_command(
        command, CLOSE_TAB_COMMANDS + CLOSE_WINDOW_COMMANDS, 82
    )
    if close_cmd:
        close_focused(close_cmd)
        return True

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

            scroll = match_command(constrained, SCROLL_COMMANDS, 82)
            if scroll:
                scroll_window(scroll)
                return True

            close_target = resolve_close_app(constrained)
            if close_target:
                close_app(close_target)
                return True

            m = re.match(r"^close\s+(?:the\s+|this\s+|that\s+|a\s+)?(?:browser\s+)?tab(?:s)?\s+(?:for\s+|on\s+|in\s+|of\s+)?(.+)$", constrained)
            if not m:
                m = re.match(r"^close\s+(.+)\s+tab(?:s)?$", constrained)
            if m:
                site = m.group(1).strip()
                if site not in ("current", "active", "this", "that", "the", "browser"):
                    cleaned_site = strip_open_prefix(site)
                    t = resolve_target(cleaned_site)
                    if not t and cleaned_site:
                        candidates = list(WEBSITES.keys())
                        t = match_command(cleaned_site, candidates, 75)
                    if not t:
                        t = cleaned_site
                    if close_browser_tab_by_name(t):
                        speak(f"Closing {t} tab")
                        return True
                    speak(f"Couldn't find {t} tab")
                    return True

            if re.search(r"^close\s+(?:browser\s+)?tab(?:s)?$", constrained) or constrained in ("close tab", "close the tab", "close current tab", "close active tab"):
                close_focused("close tab")
                return True

            close_cmd = match_command(
                constrained, CLOSE_TAB_COMMANDS + CLOSE_WINDOW_COMMANDS, 82
            )
            if close_cmd:
                close_focused(close_cmd)
                return True

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



def render_orb_image(size, core_rgb):
    """Render a glossy anti-aliased orb sprite (RGBA) with a soft glow.

    Drawn at 2x and downscaled each frame, which is what gives the smooth
    web-style look that the old stippled tkinter ovals lacked.
    """
    res = size * 2
    center = res / 2
    radius = res * 0.30

    orb = Image.new("RGBA", (res, res), (0, 0, 0, 0))
    draw = ImageDraw.Draw(orb)

    # Radial shading: brighter toward the center, soft falloff only at the rim.
    steps = 240
    for i in range(steps):
        d = 1.0 - i / steps  # 1.0 at rim (drawn first) down to 0.0 at center
        r = radius * d
        if d < 0.72:
            alpha = 255
        else:
            alpha = int(255 * max(0.0, 1.0 - (d - 0.72) / 0.28))
        shade = 0.45 + 0.55 * (1.0 - d)
        color = tuple(int(c * shade) for c in core_rgb)
        draw.ellipse(
            [center - r, center - r, center + r, center + r],
            fill=color + (alpha,),
        )

    # Fresnel-style edge highlight, the key to the glassy look.
    rim = Image.new("RGBA", (res, res), (0, 0, 0, 0))
    ImageDraw.Draw(rim).ellipse(
        [
            center - radius * 0.96,
            center - radius * 0.96,
            center + radius * 0.96,
            center + radius * 0.96,
        ],
        outline=(255, 255, 255, 150),
        width=max(2, int(res * 0.01)),
    )
    rim = rim.filter(ImageFilter.GaussianBlur(res * 0.02))
    orb = Image.alpha_composite(orb, rim)

    # Glossy specular highlight toward the top-left.
    highlight = Image.new("RGBA", (res, res), (0, 0, 0, 0))
    ImageDraw.Draw(highlight).ellipse(
        [
            center - radius * 0.60,
            center - radius * 0.74,
            center + radius * 0.10,
            center - radius * 0.06,
        ],
        fill=(255, 255, 255, 130),
    )
    highlight = highlight.filter(ImageFilter.GaussianBlur(res * 0.018))
    orb = Image.alpha_composite(orb, highlight)

    # Outer glow beneath the orb.
    glow = orb.filter(ImageFilter.GaussianBlur(res * 0.045))
    glow.putalpha(glow.getchannel("A").point(lambda a: int(a * 0.6)))

    base = Image.new("RGBA", (res, res), (0, 0, 0, 0))
    base = Image.alpha_composite(base, glow)
    base = Image.alpha_composite(base, orb)
    return base


class Orb:
    """A small always-on-top circular overlay that reflects the listening state.

    Audio and speech run on the tkinter main thread: the microphone callback
    only enqueues bytes, and ``_poll`` drains the queue from the event loop.
    Keeping pyttsx3 on a single thread avoids Windows COM threading problems.
    """

    SIZE = 170
    TRANSPARENT = "#000000"
    ORB_COLORS = {
        "listening": (0, 200, 255),
        "speaking": (120, 255, 110),
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

        self.image_item = self.canvas.create_image(
            self.SIZE / 2, self.SIZE / 2, anchor="center"
        )
        self.photo = None
        self.sprites = {
            state: render_orb_image(self.SIZE, color)
            for state, color in self.ORB_COLORS.items()
        }

        self.menu = tk.Menu(self.window, tearoff=0)
        self.menu.add_command(label="Quit", command=self.quit)

        self.canvas.bind("<ButtonPress-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<Button-3>", self._popup)

    def set_state(self, state):
        if state in self.ORB_COLORS:
            self.state = state

    def _draw(self):
        self.phase += 0.35 if self.state == "speaking" else 0.16
        pulse = (math.sin(self.phase) + 1) / 2
        target = max(1, int(self.SIZE * (1.0 + pulse * 0.06)))

        frame = self.sprites[self.state].resize((target, target), Image.LANCZOS)
        canvas_image = Image.new("RGBA", (self.SIZE, self.SIZE), (0, 0, 0, 0))
        offset = (self.SIZE - target) // 2
        canvas_image.paste(frame, (offset, offset), frame)

        self.photo = ImageTk.PhotoImage(canvas_image)
        self.canvas.itemconfig(self.image_item, image=self.photo)

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
