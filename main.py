import os
os.environ.setdefault("HF_HUB_OFFLINE", "1")

import argparse
import contextlib
import io
import re
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from feedgen.feed import FeedGenerator
from lxml import etree

import soundfile as sf
from kittentts import KittenTTS

VOICES = ["Bella", "Jasper", "Luna", "Bruno", "Rosie", "Hugo", "Kiki", "Leo"]
PODCAST_NS = "https://podcastindex.org/namespace/1.0"
BASE_URL = "https://mycast.hekuli.com/"
XML_PARSER = etree.XMLParser(remove_blank_text=True)


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
    fg.podcast.itunes_explicit("no")
    fg.podcast.itunes_type("episodic")

    feed_path.parent.mkdir(parents=True, exist_ok=True)
    fg.rss_file(str(feed_path), pretty=True)

    # Add PodcastIndex namespace to the <rss> element
    tree = etree.parse(str(feed_path), XML_PARSER)
    rss = tree.getroot()
    # lxml won't let you modify nsmap in-place; rebuild the root with the new namespace
    new_rss = etree.Element(rss.tag, rss.attrib, nsmap={**rss.nsmap, "podcast": PODCAST_NS})
    for child in rss:
        new_rss.append(child)
    new_tree = etree.ElementTree(new_rss)
    new_tree.write(str(feed_path), xml_declaration=True, encoding="UTF-8", pretty_print=True)

    print(f"Created podcast feed: {feed_path}")
    print("Edit the file to fill in your podcast details (link, category, image, etc.)")


def cmd_tts(args):
    input_path = Path(args.input)
    text = input_path.read_text()

    # If appending to a feed and using default output, put files next to the feed
    if args.feed and args.output == "output.wav":
        feed_dir = Path(args.feed).parent
        output_path = feed_dir / input_path.stem
    else:
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
        # Copy transcript to feed directory
        feed_dir = Path(args.feed).parent
        transcript_dest = feed_dir / input_path.name
        shutil.copy2(input_path, transcript_dest)

        add_episode_to_feed(args.feed, mp3_path, args.title or mp3_path.stem,
                            text, input_path)


def cmd_add_episode(args):
    feed_path = Path(args.feed)
    mp3_src = Path(args.mp3)
    transcript_src = Path(args.transcript)

    if not feed_path.exists():
        print(f"Error: Feed file {feed_path} not found.")
        raise SystemExit(1)
    if not mp3_src.exists():
        print(f"Error: MP3 file {mp3_src} not found.")
        raise SystemExit(1)
    if not transcript_src.exists():
        print(f"Error: Transcript file {transcript_src} not found.")
        raise SystemExit(1)

    feed_dir = feed_path.parent
    mp3_dest = feed_dir / mp3_src.name
    transcript_dest = feed_dir / transcript_src.name

    # Copy files into feed directory (skip if already there)
    if mp3_src.resolve() != mp3_dest.resolve():
        shutil.copy2(mp3_src, mp3_dest)
        print(f"Copied {mp3_src} -> {mp3_dest}")
    if transcript_src.resolve() != transcript_dest.resolve():
        shutil.copy2(transcript_src, transcript_dest)
        print(f"Copied {transcript_src} -> {transcript_dest}")

    text = transcript_dest.read_text()
    title = args.title or transcript_dest.stem
    add_episode_to_feed(feed_path, mp3_dest, title, text, transcript_dest)


def parse_date_from_filename(input_path):
    """Extract YYYY-MM-DD from filename like 2026-04-06.txt."""
    match = re.search(r"(\d{4}-\d{2}-\d{2})", input_path.stem)
    if match:
        return datetime.strptime(match.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def extract_description(text):
    """Extract description from text: everything before the first line starting with '---'."""
    parts = re.split(r"^---", text, maxsplit=1, flags=re.MULTILINE)
    return parts[0].strip()


def get_audio_duration(mp3_path):
    """Return duration in seconds via ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(mp3_path)],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def format_vtt_timestamp(seconds):
    """Format seconds as HH:MM:SS.mmm for WebVTT."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def txt_to_vtt(text, duration_seconds):
    """Convert plain text transcript to WebVTT, distributing cues across the audio duration."""
    # Drop delimiter/separator lines and empty lines
    lines = [
        line.strip() for line in text.splitlines()
        if line.strip() and not line.strip().startswith("---")
    ]
    joined = " ".join(lines)

    # Split by sentence boundary
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", joined) if s.strip()]

    # Fall back to line-based splitting if no sentence terminators
    if not sentences:
        sentences = lines or [joined]

    # Distribute time proportional to character length
    total_chars = sum(len(s) for s in sentences) or 1
    cues = []
    current = 0.0
    for sentence in sentences:
        share = (len(sentence) / total_chars) * duration_seconds
        start = current
        end = min(current + share, duration_seconds)
        cues.append((start, end, sentence))
        current = end

    # Build VTT content
    parts = ["WEBVTT", ""]
    for start, end, sentence in cues:
        parts.append(f"{format_vtt_timestamp(start)} --> {format_vtt_timestamp(end)}")
        parts.append(sentence)
        parts.append("")
    return "\n".join(parts)


def add_episode_to_feed(feed_path, mp3_path, title, text, input_path):
    feed_path = Path(feed_path)
    mp3_path = Path(mp3_path)
    if not feed_path.exists():
        print(f"Error: Feed file {feed_path} not found.")
        raise SystemExit(1)

    tree = etree.parse(str(feed_path), XML_PARSER)
    channel = tree.find("channel")

    pub_dt = parse_date_from_filename(input_path)
    pub_date_str = pub_dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
    episode_date = pub_dt.date()

    # Remove existing episode for the same date
    for item in channel.findall("item"):
        pub_date_el = item.find("pubDate")
        if pub_date_el is not None and pub_date_el.text:
            existing_date = parsedate_to_datetime(pub_date_el.text).date()
            if existing_date == episode_date:
                channel.remove(item)
                print(f"Replacing existing episode for {episode_date}")

    item = etree.SubElement(channel, "item")

    etree.SubElement(item, "title").text = title
    etree.SubElement(item, "guid", isPermaLink="false").text = str(uuid.uuid4())

    file_size = str(os.path.getsize(mp3_path))
    etree.SubElement(item, "enclosure", url=BASE_URL + mp3_path.name,
                     length=file_size, type="audio/mpeg")

    etree.SubElement(item, "pubDate").text = pub_date_str
    etree.SubElement(item, "description").text = extract_description(text)

    # Generate WebVTT transcript with timestamps distributed across the audio duration
    duration = get_audio_duration(mp3_path)
    vtt_path = mp3_path.with_suffix(".vtt")
    vtt_path.write_text(txt_to_vtt(text, duration))
    print(f"Generated transcript: {vtt_path}")

    # Podcasting 2.0 transcript tag (points to WebVTT file)
    etree.SubElement(item, f"{{{PODCAST_NS}}}transcript",
                     url=BASE_URL + vtt_path.name, type="text/vtt", language="en")

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
    tts_parser.add_argument("-v", "--voice", default="Bella", choices=VOICES,
                            help="Voice to use (default: Bella)")
    tts_parser.add_argument("-s", "--speed", type=float, default=1.3,
                            help="Speech speed multiplier (default: 1.2)")
    tts_parser.add_argument("-f", "--feed", help="Podcast feed file to append episode to")
    tts_parser.add_argument("-t", "--title", help="Episode title (default: output filename)")

    # add-episode
    ae_parser = subparsers.add_parser("add-episode",
                                      help="Add an existing mp3 + transcript as an episode")
    ae_parser.add_argument("feed", help="Podcast feed file")
    ae_parser.add_argument("mp3", help="MP3 audio file")
    ae_parser.add_argument("transcript", help="Text transcript file (date parsed from filename)")
    ae_parser.add_argument("-t", "--title", help="Episode title (default: transcript filename)")

    args = parser.parse_args()

    if args.command == "new-podcast":
        cmd_new_podcast(args)
    elif args.command == "tts":
        cmd_tts(args)
    elif args.command == "add-episode":
        cmd_add_episode(args)


if __name__ == "__main__":
    main()
