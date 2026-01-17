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
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import trafilatura

# Configuration
OUTPUT_DIR = Path("~/Library/Mobile Documents/com~apple~CloudDocs/Thyme/").expanduser()
BOOKMARKS_PATH = Path("~/Library/Safari/Bookmarks.plist").expanduser()
STATE_FILE = OUTPUT_DIR / "processed.json"
MAX_EPISODES = 40
MIN_TEXT_LENGTH = 500  # Skip articles shorter than this
VOICE = "Samantha"
RATE = 190


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
    
    # Sort by date added (newest first) and take top 20
    reading_list.sort(key=lambda x: x.get("date_added") or datetime.min, reverse=True)
    return reading_list[:MAX_EPISODES]


def extract_article_text(url):
    """Fetch URL and extract article text using trafilatura."""
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        return None
    
    text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
    return text


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
    """Convert text to MP3 using macOS say command."""
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
    for item in items:
        url = item["url"]
        title = item["title"]
        
        if url in processed_urls:
            print(f"Skipping (already processed): {title[:50]}")
            continue
        
        print(f"Processing: {title[:50]}...")
        
        # Extract article text
        text = extract_article_text(url)
        if not text:
            print(f"  Failed to extract text, skipping")
            processed_urls.add(url)  # Mark as processed to avoid retrying
            continue

        if len(text) < MIN_TEXT_LENGTH:
            print(f"  Too short ({len(text)} chars), skipping")
            processed_urls.add(url)
            continue
        
        # Prepare text with spoken intro
        domain = get_domain(url)
        full_text = f"From {domain}: {title}.\n\n{text}"
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_title = sanitize_filename(title)
        filename = f"{timestamp}-{safe_title}.m4a"
        output_path = OUTPUT_DIR / filename
        
        # Convert to audio
        print(f"  Generating audio...")
        try:
            text_to_mp3(full_text, output_path)
            print(f"  Saved: {filename}")
            processed_urls.add(url)
        except subprocess.CalledProcessError as e:
            print(f"  Error generating audio: {e}")
            continue
    
    # Save state
    save_processed_urls(processed_urls)
    
    # Cleanup old episodes
    cleanup_old_episodes()
    
    print("Done!")


if __name__ == "__main__":
    main()
