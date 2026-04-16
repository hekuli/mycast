# KittenTTS Setup Guide

## How This Works

`uv` is your all-in-one Python tool. It replaces pip, virtualenv, pyenv, etc.

| File              | What it is                                    | Commit? |
|-------------------|-----------------------------------------------|---------|
| `pyproject.toml`  | Project manifest (like `package.json`)         | Yes     |
| `uv.lock`         | Pinned dependency versions (like `pnpm-lock`)  | Yes     |
| `.python-version` | Which Python version this project uses         | Yes     |
| `.venv/`          | Installed packages (like `node_modules`)       | No      |

You never activate the virtualenv manually. `uv run` does it for you.


---

## Step 1 — Initialize the project with Python 3.12

KittenTTS supports Python 3.8–3.12. Your system has 3.14 (too new).
Passing `--python` sets both `requires-python` and `.python-version` in one shot:

```bash
uv init --python 3.12
```

Creates `pyproject.toml`, `main.py`, and `.python-version`. `uv` will auto-download
Python 3.12 when you first need it — nothing touches your system Python.


## Step 2 — Install dependencies

```bash
uv add "kittentts @ https://github.com/KittenML/KittenTTS/releases/download/0.8.1/kittentts-0.8.1-py3-none-any.whl"
uv add feedgen
```

- **kittentts** — TTS engine (+ onnxruntime, numpy, soundfile, etc.)
- **feedgen** — RSS/podcast feed generation

Also requires **ffmpeg** on the system (installed via Homebrew) for WAV-to-MP3 conversion.


## Step 3 — Verify it works

```bash
uv run python -c "import kittentts; print('KittenTTS imported successfully')"
```

If this prints the success message, you're good.


