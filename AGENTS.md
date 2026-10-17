# AGENTS.md

Single-file Windows voice assistant (`assistant.py`). No tests, linter, typechecker, CI, or package config exist — do not invent verification commands.

## Run

```bat
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install vosk sounddevice pyttsx3 rapidfuzz
python assistant.py
```

- `requirements.txt` is referenced by README but **does not exist** in the repo.
- Requires a working microphone; the app blocks on audio input, so it cannot be verified headless. Smoke-check imports instead: `python -c "import assistant"` (this runs `pyttsx3.init()` at module level).
- Stops only via the voice phrase "stop listening" or `Ctrl+C`.
- Python 3.10+; if a dep fails to install (notably on 3.14), use 3.12/3.13.

## Structure

- `assistant.py` — all logic: audio loop (`main`), command routing (`handle_command`), app launching (`open_app`).
- `model/vosk-model-small-en-us-0.15/` — Vosk model, **committed to git**. `MODEL_DIR` in `assistant.py:21` is hardcoded to this exact name; renaming the folder breaks startup.
- `start_assistant.bat` — Windows launcher. Currently hardcodes `cd /d "C:\Path\To\asst"` (a placeholder); the README's correct form is `cd /d "%~dp0"`.
- README's project structure section is partly aspirational (`.venv`, `requirements.txt` are not tracked). Trust the code over the README.

## Conventions (easy to get wrong)

- **Adding an application requires two edits**: the `apps` dict inside `open_app()` (assistant.py:50) *and* the `apps` list inside `handle_command()` (assistant.py:164). Missing the list means fuzzy matching never routes the command to `open_app`.
- Adding a website only needs the `websites` dict in `handle_command()` (assistant.py:152).
- Common misrecognitions/shorthand live in the `aliases` dict in `handle_command()`; alias keys are added to the fuzzy `targets` and their values must be a canonical key already in `websites` or the `apps` list (alias resolution happens before routing).
- Fuzzy-match thresholds are tuned per call site: `75` default, `78` for targets, `85` for exit phrases. Changing them globally affects misrecognition vs. false-positive tradeoffs — change deliberately.
- Command text is normalized (lowercased, filler words/punctuation stripped, `open|launch|start|go to` prefix removed) before matching; match against normalized forms.
- Never execute arbitrary recognized text as a shell command — only launch entries from the allowlisted dicts/lists.
- Windows-only: `sounddevice` mic capture, `pyttsx3` (SAPI) speech, hardcoded Chrome paths under `C:\Program Files`.
