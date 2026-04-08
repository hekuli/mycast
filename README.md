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
uv run python main.py tts 2026-04-06.txt -f feed.xml -t "April 6 News"
```

The `-f` flag appends the generated audio as a new episode to the feed file. `-t` sets the episode title (defaults to the output filename).

When using `-f`:
- MP3 and transcript files are placed in the same directory as the feed
- The episode date is extracted from the input filename (`YYYY-MM-DD.txt`)
- The episode description is the text before the first `---` in the input file
- A WebVTT transcript (`.vtt`) is generated next to the mp3 with timestamps distributed proportionally (by sentence length) across the audio duration
- A `<podcast:transcript>` tag (Podcasting 2.0) links to the `.vtt` file with `type="text/vtt"`
- Running again for the same date replaces the existing episode

### Add an existing mp3 + transcript as an episode

If you already have an mp3 and transcript and just want to add it to the feed without re-running TTS:

```bash
uv run python main.py add-episode feed.xml episode.mp3 2026-04-07.txt
uv run python main.py add-episode feed.xml episode.mp3 2026-04-07.txt -t "April 7 News"
```

The mp3 and transcript files are copied into the feed's directory (overwriting if they already exist), and the episode is added/replaced in the feed.

### Manage Files in R2 Bucket

Assumes the `rclone` tool is installed.

List bucket contents:
```
rclone ls mycast:
```

Upload entire output directory contents:
```
rclone 
```

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
