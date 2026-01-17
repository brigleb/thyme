# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Thyme converts Safari Reading List articles to audio files (.m4a) using macOS text-to-speech. It's a single-file Python script that:
1. Reads Safari's Bookmarks.plist to get Reading List items
2. Extracts article text with trafilatura
3. Converts to m4a/AAC using the macOS `say` command
4. Saves to `~/Library/Mobile Documents/com~apple~CloudDocs/Reading List/` for sync to iOS devices

## Commands

```bash
# Install dependencies
pip install trafilatura lxml_html_clean tqdm

# Run the script
python thyme.py

# Check available voices
say -v ?

# View logs (when running via launchd)
cat /tmp/thyme.log
cat /tmp/thyme.err
```

## Architecture

Single script (`thyme.py`) with these main functions:
- `get_reading_list_items()` - Parses `~/Library/Safari/Bookmarks.plist`
- `extract_article_text()` - Uses trafilatura to fetch and extract article content
- `text_to_mp3()` - Shells out to macOS `say` command
- `cleanup_old_episodes()` - Maintains MAX_EPISODES limit

State is tracked in `processed.json` (list of already-processed URLs) stored in the output directory.

## Configuration

Constants at top of `thyme.py`: `OUTPUT_DIR`, `MAX_EPISODES`, `VOICE`, `RATE`

## macOS Permissions

Requires Full Disk Access to read Safari data (System Settings → Privacy & Security → Full Disk Access).
