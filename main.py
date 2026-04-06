import os
os.environ.setdefault("HF_HUB_OFFLINE", "1")

import argparse
import contextlib
import io
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from feedgen.feed import FeedGenerator
from lxml import etree

import soundfile as sf
from kittentts import KittenTTS

VOICES = ["Bella", "Jasper", "Luna", "Bruno", "Rosie", "Hugo", "Kiki", "Leo"]


def cmd_new_podcast(args):
    feed_path = Path(args.output)
    if feed_path.exists() and not args.force:
        print(f"Error: {feed_path} already exists. Use --force to overwrite.")
        raise SystemExit(1)

    fg = FeedGenerator()
    fg.load_extension("podcast")

    fg.title(args.title)
    fg.link(href="https://example.com", rel="alternate")
    fg.description(args.description or f"A podcast called {args.title}")
    fg.language("en-us")

    fg.podcast.itunes_category("Technology")
    fg.podcast.itunes_explicit("false")
    fg.podcast.itunes_type("episodic")

    feed_path.parent.mkdir(parents=True, exist_ok=True)
    fg.rss_file(str(feed_path), pretty=True)
    print(f"Created podcast feed: {feed_path}")
    print("Edit the file to fill in your podcast details (link, category, image, etc.)")


def cmd_tts(args):
    text = Path(args.input).read_text()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("Loading model...")
    model = KittenTTS("KittenML/kitten-tts-mini-0.8")

    print(f"Generating audio with voice '{args.voice}' (speed={args.speed})...")
    with contextlib.redirect_stdout(io.StringIO()):
        audio = model.generate(text, voice=args.voice, speed=args.speed)

    wav_path = output_path.with_suffix(".wav")
    mp3_path = output_path.with_suffix(".mp3")

    print("Saving WAV...")
    sf.write(wav_path, audio, 24000)

    print("Converting to MP3...")
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(wav_path), "-b:a", "320k", str(mp3_path)],
        capture_output=True, check=True,
    )
    wav_path.unlink()

    print(f"Saved {mp3_path}")

    if args.feed:
        add_episode_to_feed(args.feed, mp3_path, args.title or mp3_path.stem)


def add_episode_to_feed(feed_path, mp3_path, title):
    feed_path = Path(feed_path)
    if not feed_path.exists():
        print(f"Error: Feed file {feed_path} not found.")
        raise SystemExit(1)

    tree = etree.parse(str(feed_path))
    channel = tree.find("channel")

    nsmap = {
        "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
    }

    item = etree.SubElement(channel, "item")

    etree.SubElement(item, "title").text = title
    etree.SubElement(item, "guid", isPermaLink="false").text = str(uuid.uuid4())

    file_size = str(os.path.getsize(mp3_path))
    etree.SubElement(item, "enclosure", url=str(mp3_path), length=file_size, type="audio/mpeg")

    pub_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    etree.SubElement(item, "pubDate").text = pub_date

    etree.SubElement(item, "description").text = f"Episode: {title}"

    tree.write(str(feed_path), xml_declaration=True, encoding="UTF-8", pretty_print=True)
    print(f"Added episode '{title}' to {feed_path}")


def main():
    parser = argparse.ArgumentParser(description="Text-to-speech podcast tool.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # new-podcast
    np_parser = subparsers.add_parser("new-podcast", help="Create a new podcast feed template")
    np_parser.add_argument("title", help="Podcast title")
    np_parser.add_argument("-d", "--description", help="Podcast description")
    np_parser.add_argument("-o", "--output", default="feed.xml", help="Output feed file (default: feed.xml)")
    np_parser.add_argument("--force", action="store_true", help="Overwrite existing feed file")

    # tts
    tts_parser = subparsers.add_parser("tts", help="Convert a text file to spoken audio")
    tts_parser.add_argument("input", help="Path to a text file")
    tts_parser.add_argument("-o", "--output", default="output.wav", help="Output filepath (default: output.mp3)")
    tts_parser.add_argument("-v", "--voice", default="Leo", choices=VOICES,
                            help="Voice to use (default: Jasper)")
    tts_parser.add_argument("-s", "--speed", type=float, default=1.0,
                            help="Speech speed multiplier (default: 1.0)")
    tts_parser.add_argument("-f", "--feed", help="Podcast feed file to append episode to")
    tts_parser.add_argument("-t", "--title", help="Episode title (default: output filename)")

    args = parser.parse_args()

    if args.command == "new-podcast":
        cmd_new_podcast(args)
    elif args.command == "tts":
        cmd_tts(args)


if __name__ == "__main__":
    main()
