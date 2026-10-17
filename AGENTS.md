# AGENTS.md

Single-file Windows voice assistant (`assistant.py`). No tests, linter, typechecker, CI, or package config exist — do not invent verification commands.

## Run

```bat
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install vosk sounddevice pyttsx3 rapidfuzz pillow
python assistant.py
```

- `requirements.txt` is referenced by README but **does not exist** in the repo.
- Requires a working microphone and a desktop session (tkinter overlay), so it cannot be verified headless. Smoke-check the GUI instead: `python -c "import assistant; o=assistant.Orb(); o._draw(); o.quit()"` (import runs `pyttsx3.init()` at module level).
- Runs a floating `Orb` overlay (`tk.Tk`, borderless, always-on-top, chroma-key transparent). Stops via the voice phrase "stop listening" or right-click → Quit — `Ctrl+C` no longer applies because tkinter owns the mainloop.
- Python 3.10+; if a dep fails to install (notably on 3.14), use 3.12/3.13.

## Structure

- `assistant.py` — all logic: GUI + event loop (`Orb`), module entry (`main`), command routing (`handle_command`), app launching (`open_app`).
- The orb sprite is rendered by `render_orb_image()` (assistant.py:432) with Pillow (RGBA, drawn at 2x then downscaled per frame). Pillow is required, not optional — the old tkinter-oval orb was replaced. Sprites are precomputed per state in `Orb.__init__`; `Orb._draw` only resizes/composites them.
- Command vocabulary is **module-level**: `WEBSITES` (assistant.py:74), `APPS` (assistant.py:89), `ALIASES` (assistant.py:110), plus `EXIT_PHRASES`/`SCROLL_COMMANDS`/`OPEN_VERBS`. Both routing and the recognition grammar derive from these.
- Two Vosk recognizers share one model: an open-vocabulary `recognizer` and a grammar-constrained `constrained_recognizer` built by `build_grammar()` (assistant.py:322). `handle_command` tries the free transcript first, then re-runs the buffered PCM through `recognize_constrained()` before falling back to Google search. Search always uses the free transcript.
- `find_model_dir()` (assistant.py:346) prefers a larger model folder under `model/` if one is present; otherwise the committed `model/vosk-model-small-en-us-0.15/`. `MODEL_DIR` (assistant.py:33) is the fallback and is hardcoded to that exact folder name.
- `scroll_window()` (assistant.py:259) sends synthetic mouse-wheel events via `ctypes` (no extra dependency) at the cursor, so scrolling targets whatever window is under the pointer. Negative wheel delta scrolls down.
- `start_assistant.bat` — startup launcher. Uses `cd /d "%~dp0"` and `start "" pythonw assistant.py` (no console window; `pythonw` is why the module redirects `None` stdout/stderr to `os.devnull`).
- README's project structure section is partly aspirational (`.venv`, `requirements.txt` are not tracked). Trust the code over the README.

## Conventions (easy to get wrong)

- **Adding an application requires two edits**: the `apps` dict inside `open_app()` (assistant.py:158) *and* the module-level `APPS` list (assistant.py:89). Missing the `APPS` entry means neither fuzzy matching nor the grammar will route the command.
- Adding a website only needs the module-level `WEBSITES` dict (assistant.py:74); add shorthand/misrecognitions to `ALIASES` (assistant.py:110). Alias values must be a canonical key already in `WEBSITES` or `APPS`. The command grammar is rebuilt from all of these automatically at startup.
- Fuzzy-match thresholds are tuned per call site: `75` default, `78` for targets (`resolve_target`, assistant.py:312), `82` for scroll commands, `85` for exit phrases. Changing them globally affects misrecognition vs. false-positive tradeoffs — change deliberately.
- **Keep audio + TTS on the tkinter main thread.** The mic callback only enqueues bytes; `Orb._poll` drains them from the event loop via `window.after`. Do not move `speak`/`pyttsx3` or `AcceptWaveform` into a worker thread — Windows COM breaks.
- Apps with user-specific install paths (Chrome, Brave, Spotify) are special-cased in `open_app()` with a candidate-path loop plus a URI/default-browser fallback, not added to the `apps` dict.
- Command text is normalized (lowercased, filler words/punctuation stripped, `open|launch|start|go to` prefix removed) before matching; match against normalized forms.
- Set `MIC_DEVICE` (assistant.py:42) to a sounddevice index to force a specific microphone; on stream failure the available inputs are printed to the console.
- Never execute arbitrary recognized text as a shell command — only launch entries from the allowlisted dicts/lists.
- Windows-only: `sounddevice` mic capture, `pyttsx3` (SAPI) speech, `tk` chroma-key transparency (`-transparentcolor`), hardcoded Chrome paths under `C:\Program Files`.
