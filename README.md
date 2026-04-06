# mycast

Text-to-speech using [KittenTTS](https://github.com/KittenML/KittenTTS).

## Setup

Requires [uv](https://github.com/astral-sh/uv). No global Python packages needed.

```bash
uv sync
```

This installs Python 3.12 (if needed) and all dependencies into a local `.venv/`.

## Usage

### Generate speech from text

```bash
uv run python main.py tts input.txt
uv run python main.py tts input.txt -o episode1
uv run python main.py tts input.txt -v Luna -o episode1
uv run python main.py tts input.txt -s 1.2              # speak faster
uv run python main.py tts input.txt -s 0.8              # speak slower
```

Output is MP3. Play with `afplay episode1.mp3`.

### Create a podcast feed

```bash
uv run python main.py new-podcast "My Podcast" -d "A podcast about things"
uv run python main.py new-podcast "My Podcast" -o podcasts/feed.xml
uv run python main.py new-podcast "My Podcast" --force   # overwrite existing
```

Creates an RSS 2.0 feed template (`feed.xml` by default). Edit it to fill in your podcast details (link, image, category, etc.).

### Generate speech and add to a podcast feed

```bash
uv run python main.py tts input.txt -o episode1 -f feed.xml -t "Episode 1: Hello World"
```

The `-f` flag appends the generated audio as a new episode to the feed file. `-t` sets the episode title (defaults to the output filename).

## Voices

| Voice    | Gender |
|----------|--------|
| Bella    | Female |
| Jasper   | Male (default) |
| Luna     | Female |
| Bruno    | Male   |
| Rosie    | Female |
| Hugo     | Male   |
| Kiki     | Female |
| Leo      | Male   |

## Notes

- The TTS model (~25MB) is downloaded from HuggingFace on first run and cached at `~/.cache/huggingface/hub/`. Subsequent runs use the cache offline — no network requests.
- MP3 output is encoded at 320kbps CBR via ffmpeg.
