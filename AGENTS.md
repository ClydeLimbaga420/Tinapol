# AGENTS.md

Single-file Windows voice assistant (`assistant.py`). No tests, linter, typechecker, CI, or package config exist — do not invent verification commands.

## Run

```bat
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python assistant.py
```

- Requires a working microphone and a desktop session (tkinter overlay), so it cannot be verified headless. Smoke-check the GUI instead: `python -c "import assistant; o=assistant.Orb(); o._draw(); o.quit()"` (import runs `pyttsx3.init()` at module level).
- Runs a floating `Orb` overlay (`tk.Tk`, borderless, always-on-top, chroma-key transparent). Stops via the voice phrase "stop listening" or right-click → Quit — `Ctrl+C` no longer applies because tkinter owns the mainloop.
- Python 3.10+; if a dep fails to install (notably on 3.14), use 3.12/3.13.

## Structure

- `assistant.py` — all logic: GUI + event loop (`Orb`), module entry (`main`), command routing (`handle_command`), app launching (`open_app`), named app closing (`close_app`).
- The orb sprite is rendered by `render_orb_image()` (assistant.py:725) with Pillow (RGBA, drawn at 2x then downscaled per frame). Pillow is required, not optional — the old tkinter-oval orb was replaced. Sprites are precomputed per state in `Orb.__init__`; `Orb._draw` only resizes/composites them.
- Command vocabulary is **module-level**: `WEBSITES` (assistant.py:75), `APPS` (assistant.py:92), `CLOSEABLE_APPS` (assistant.py:119), `ALIASES` (assistant.py:148), plus `EXIT_PHRASES`/`SCROLL_COMMANDS`/`CLOSE_TAB_COMMANDS`/`CLOSE_WINDOW_COMMANDS`/`CLOSE_BLOCKED`/`OPEN_VERBS`. Both routing and the recognition grammar derive from these.
- Two Vosk recognizers share one model: an open-vocabulary `recognizer` and a grammar-constrained `constrained_recognizer` built by `build_grammar()` (assistant.py:584). `handle_command` tries the free transcript first, then re-runs the buffered PCM through `recognize_constrained()` before falling back to Google search. Search always uses the free transcript.
- `find_model_dir()` (assistant.py:615) prefers a larger model folder under `model/` if one is present; otherwise the committed `model/vosk-model-small-en-us-0.15/`. `MODEL_DIR` (assistant.py:34) is the fallback and is hardcoded to that exact folder name.
- `scroll_window()` (assistant.py:382) sends synthetic mouse-wheel events via `ctypes` (no extra dependency) at the cursor, so scrolling targets whatever window is under the pointer. Negative wheel delta scrolls down.
- `close_focused()` (assistant.py:423) sends Ctrl+W (tab) or Alt+F4 (window) via `send_key_chord()` (assistant.py:411) using `ctypes` `keybd_event` — keys land on the **focused** window, unlike scrolling which uses the cursor. A bare "close" means tab.
- "close \<app\>" by name is handled before that: `resolve_close_app()` (assistant.py:556) strips `close [the|app|program] <name>`, resolves aliases/fuzzy against `CLOSE_APP_TARGETS`, and returns `None` for tab/window phrases (so `CLOSE_BLOCKED` keeps them on `close_focused()`). `close_app()` (assistant.py:473) then runs `taskkill /F /IM` on the executables in `CLOSEABLE_APPS` — never on raw recognized text. File Explorer is special-cased: `close_explorer_windows()` (assistant.py:445) posts `WM_CLOSE` to visible `CabinetWClass`/`ExploreWClass` windows via `ctypes.EnumWindows`, because killing `explorer.exe` would also take down the taskbar/desktop shell.
- `requirements.txt` — the five third-party deps (`vosk`, `sounddevice`, `pyttsx3`, `rapidfuzz`, `pillow`), unpinned so any supported Python can resolve wheels. Both README install steps and the Run block above install from it.
- `start_assistant.bat` — startup launcher. Uses `cd /d "%~dp0"` and `start "" pythonw assistant.py` (no console window; `pythonw` is why the module redirects `None` stdout/stderr to `os.devnull`).
- Committed tree: `assistant.py`, `requirements.txt`, `start_assistant.bat`, `README.md`, `AGENTS.md`, `model/`. `.venv/` is created during setup and not tracked. Trust the code over the README.

## Conventions (easy to get wrong)

- **Adding an application requires two edits**: the `apps` dict inside `open_app()` (assistant.py:246) *and* the module-level `APPS` list (assistant.py:92). Missing the `APPS` entry means neither fuzzy matching nor the grammar will route the command. To also allow "close \<app\>" by name, add a third entry to the module-level `CLOSEABLE_APPS` dict (assistant.py:119) mapping the name to the `taskkill` executable name(s).
- Microsoft Office apps (word/excel/powerpoint/outlook/onenote/access/publisher) are launched via a lookup of the exe in the Windows `App Paths` registry (`winreg`) using the `office` dict inside `open_app()` (assistant.py:342) — no hardcoded path, and a missing Office install speaks "not installed" instead of raising. The same canonical names live in `APPS` and `CLOSEABLE_APPS`, so they open and close like everything else.
- Adding a website only needs the module-level `WEBSITES` dict (assistant.py:75); add shorthand/misrecognitions to `ALIASES` (assistant.py:148). Alias values must be a canonical key already in `WEBSITES` or `APPS`. The command grammar is rebuilt from all of these automatically at startup.
- Fuzzy-match thresholds are tuned per call site: `75` default, `78` for targets (`resolve_target` and `resolve_close_app`, assistant.py:546), `82` for scroll and close commands, `85` for exit phrases. Changing them globally affects misrecognition vs. false-positive tradeoffs — change deliberately.
- **Keep audio + TTS on the tkinter main thread.** The mic callback only enqueues bytes; `Orb._poll` drains them from the event loop via `window.after`. Do not move `speak`/`pyttsx3` or `AcceptWaveform` into a worker thread — Windows COM breaks.
- Apps with user-specific install paths (Chrome, Brave, Spotify, VS Code) are special-cased in `open_app()` with a candidate-path loop plus a URI/default-browser fallback, not added to the `apps` dict.
- Command text is normalized (lowercased, filler words/punctuation stripped, `open|launch|start|go to` prefix removed) before matching; match against normalized forms.
- Set `MIC_DEVICE` (assistant.py:43) to a sounddevice index to force a specific microphone; on stream failure the available inputs are printed to the console.
- Never execute arbitrary recognized text as a shell command — only launch entries from the allowlisted dicts/lists, and only pass executables from `CLOSEABLE_APPS` to `taskkill`.
- Windows-only: `sounddevice` mic capture, `pyttsx3` (SAPI) speech, `tk` chroma-key transparency (`-transparentcolor`), hardcoded Chrome paths under `C:\Program Files`.
