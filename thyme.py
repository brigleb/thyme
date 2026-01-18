#!/usr/bin/env python3
"""
Thyme — Convert Safari Reading List articles to audio.
"""

import json
import os
import plistlib
import re
import subprocess
import tempfile
import wave
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urljoin
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

import trafilatura
from tqdm import tqdm
from lxml import html as lxml_html

# Configuration
OUTPUT_DIR = Path("~/Library/Mobile Documents/com~apple~CloudDocs/Reading List/").expanduser()
BOOKMARKS_PATH = Path("~/Library/Safari/Bookmarks.plist").expanduser()
STATE_FILE = OUTPUT_DIR / "processed.json"
MAX_EPISODES = 50
MIN_TEXT_LENGTH = 500  # Skip articles shorter than this

# TTS Configuration
USE_PIPER = True  # Set to False to fall back to macOS 'say'
PIPER_MODEL = "~/piper-models/en_US-lessac-high.onnx"  # Path to Piper voice model
# Download voice models from: https://rhasspy.github.io/piper-samples/
# Using: en_US-lessac-high for highest quality

# Fallback macOS 'say' configuration (used when USE_PIPER=False or if Piper fails to load)
VOICE = "Samantha"
RATE = 190

# Initialize Piper voice
piper_voice = None
if USE_PIPER and PIPER_MODEL:
    try:
        from piper.voice import PiperVoice
        model_path = Path(PIPER_MODEL).expanduser()
        piper_voice = PiperVoice.load(str(model_path))
        print(f"Loaded Piper TTS model: {model_path}")
    except ImportError:
        print("Warning: piper-tts not installed. Install with: pip install piper-tts")
        print("Falling back to macOS 'say' command")
    except Exception as e:
        print(f"Warning: Could not load Piper model: {e}")
        print("Falling back to macOS 'say' command")


def load_processed_urls():
    """Load list of already-processed URLs."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            data = json.load(f)
            return set(data.get("processed_urls", []))
    return set()


def save_processed_urls(urls):
    """Save list of processed URLs."""
    with open(STATE_FILE, "w") as f:
        json.dump({"processed_urls": list(urls)}, f, indent=2)


def get_reading_list_items():
    """Parse Safari bookmarks and extract Reading List items."""
    with open(BOOKMARKS_PATH, "rb") as f:
        bookmarks = plistlib.load(f)
    
    def find_reading_list(node):
        """Recursively find the Reading List folder."""
        if node.get("Title") == "com.apple.ReadingList":
            return node.get("Children", [])
        for child in node.get("Children", []):
            result = find_reading_list(child)
            if result is not None:
                return result
        return None
    
    items = find_reading_list(bookmarks)
    if not items:
        return []
    
    # Extract URL, title, and date for each item
    reading_list = []
    for item in items:
        url = item.get("URLString")
        title = item.get("URIDictionary", {}).get("title", "Untitled")
        reading_list_data = item.get("ReadingList", {})
        date_added = reading_list_data.get("DateAdded")
        
        if url:
            reading_list.append({
                "url": url,
                "title": title,
                "date_added": date_added,
            })
    
    # Sort by date added (oldest first) and take top MAX_EPISODES
    reading_list.sort(key=lambda x: x.get("date_added") or datetime.min, reverse=False)
    return reading_list[:MAX_EPISODES]


def extract_article_text(url):
    """Fetch URL and extract article text using trafilatura."""
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        return None

    text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
    return text


def get_article_image_url(url):
    """
    Extract feature image URL from article.
    Tries Open Graph image, Twitter Card image, then falls back to favicon.
    """
    try:
        # Fetch the HTML
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=10) as response:
            html_content = response.read()

        # Parse HTML
        tree = lxml_html.fromstring(html_content)

        # Try Open Graph image (og:image)
        og_image = tree.xpath('//meta[@property="og:image"]/@content')
        if og_image:
            image_url = og_image[0]
            # Make absolute URL if relative
            return urljoin(url, image_url)

        # Try Twitter Card image
        twitter_image = tree.xpath('//meta[@name="twitter:image"]/@content')
        if twitter_image:
            image_url = twitter_image[0]
            return urljoin(url, image_url)

        # Fallback to favicon
        favicon = tree.xpath('//link[@rel="icon"]/@href | //link[@rel="shortcut icon"]/@href')
        if favicon:
            return urljoin(url, favicon[0])

        # Last resort: /favicon.ico
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/favicon.ico"

    except Exception as e:
        # If all else fails, return a default favicon path
        try:
            parsed = urlparse(url)
            return f"{parsed.scheme}://{parsed.netloc}/favicon.ico"
        except:
            return None


def download_image(image_url, output_path):
    """Download image from URL to local path."""
    try:
        req = Request(image_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=10) as response:
            image_data = response.read()

        with open(output_path, 'wb') as f:
            f.write(image_data)
        return True
    except (URLError, HTTPError, Exception):
        return False


def set_file_icon(file_path, image_path):
    """Set custom icon for a file using the fileicon utility."""
    try:
        subprocess.run(
            ['fileicon', 'set', file_path, image_path],
            check=True,
            capture_output=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def sanitize_filename(title):
    """Convert title to safe filename."""
    # Remove or replace problematic characters
    title = re.sub(r'[^\w\s-]', '', title.lower())
    title = re.sub(r'[\s_]+', '-', title)
    title = re.sub(r'-+', '-', title)
    return title[:50].strip('-')


def get_domain(url):
    """Extract domain name from URL for spoken intro."""
    parsed = urlparse(url)
    domain = parsed.netloc
    # Remove www. prefix
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def text_to_mp3(text, output_path):
    """Convert text to audio using Piper TTS or macOS say command."""
    if piper_voice is not None:
        # Use Piper TTS
        # Save as WAV first
        temp_wav = str(output_path).replace('.m4a', '.wav')

        # Collect audio chunks
        audio_data = b''
        for audio_chunk in piper_voice.synthesize(text):
            audio_data += audio_chunk.audio_int16_bytes

        # Write to WAV file
        with wave.open(temp_wav, "w") as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(piper_voice.config.sample_rate)
            wav_file.writeframes(audio_data)

        # Convert WAV to M4A using ffmpeg
        subprocess.run([
            "ffmpeg", "-y", "-i", temp_wav,
            "-c:a", "aac", "-b:a", "64k",
            str(output_path)
        ], check=True, capture_output=True)

        # Clean up temp WAV
        os.unlink(temp_wav)
    else:
        # Fall back to macOS say command
        # Write text to temp file to avoid shell escaping issues
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(text)
            temp_path = f.name

        try:
            subprocess.run([
                "say",
                "-v", VOICE,
                "-r", str(RATE),
                "-f", temp_path,
                "--file-format=m4af",
                "--data-format=aac",
                "-o", str(output_path),
            ], check=True)
        finally:
            os.unlink(temp_path)


def cleanup_old_episodes():
    """Delete episodes beyond MAX_EPISODES limit."""
    mp3_files = sorted(OUTPUT_DIR.glob("*.m4a"), reverse=True)
    
    for old_file in mp3_files[MAX_EPISODES:]:
        print(f"Removing old episode: {old_file.name}")
        old_file.unlink()


def main():
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load state
    processed_urls = load_processed_urls()
    
    # Get reading list
    print("Reading Safari Reading List...")
    items = get_reading_list_items()
    print(f"Found {len(items)} items in Reading List")
    
    # Process each unprocessed item
    for item in tqdm(items, desc="Processing articles", unit="article"):
        url = item["url"]
        title = item["title"]

        if url in processed_urls:
            tqdm.write(f"  Skipping (already processed): {title[:50]}")
            continue

        tqdm.write(f"  Processing: {title[:50]}...")

        # Extract article text
        text = extract_article_text(url)
        if not text:
            tqdm.write(f"    Failed to extract text, skipping")
            processed_urls.add(url)  # Mark as processed to avoid retrying
            continue

        if len(text) < MIN_TEXT_LENGTH:
            tqdm.write(f"    Too short ({len(text)} chars), skipping")
            processed_urls.add(url)
            continue

        # Prepare text with spoken intro
        domain = get_domain(url)
        full_text = f"From {domain}: {title}.\n\n{text}"

        # Generate filename from title
        safe_title = sanitize_filename(title)
        filename = f"{safe_title}.m4a"
        output_path = OUTPUT_DIR / filename

        # Convert to audio
        tqdm.write(f"    Generating audio...")
        try:
            text_to_mp3(full_text, output_path)
            tqdm.write(f"    Saved: {filename}")

            # Set custom icon from article image or favicon
            tqdm.write(f"    Setting icon...")
            image_url = get_article_image_url(url)
            if image_url:
                # Download image to temp file
                temp_image = OUTPUT_DIR / f".temp_icon_{safe_title}.png"
                if download_image(image_url, temp_image):
                    # Set the icon
                    if set_file_icon(str(output_path), str(temp_image)):
                        tqdm.write(f"    Icon set from: {image_url}")
                    # Clean up temp image
                    try:
                        temp_image.unlink()
                    except:
                        pass

            processed_urls.add(url)
        except subprocess.CalledProcessError as e:
            tqdm.write(f"    Error generating audio: {e}")
            continue
    
    # Save state
    save_processed_urls(processed_urls)
    
    # Cleanup old episodes
    cleanup_old_episodes()
    
    print("Done!")


if __name__ == "__main__":
    main()
