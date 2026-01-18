# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Thyme converts Safari Reading List articles to audio files (.m4a) using text-to-speech. It's a single-file Python script that:
1. Reads Safari's Bookmarks.plist to get Reading List items
2. Extracts article text with trafilatura
3. Converts to m4a/AAC using Piper TTS (open-source) or macOS `say` command (fallback)
4. Saves to `~/Library/Mobile Documents/com~apple~CloudDocs/Reading List/` for sync to iOS devices

## Commands

```bash
# Install Python dependencies
pip install trafilatura lxml_html_clean tqdm piper-tts

# Install system dependencies (for Piper TTS)
brew install ffmpeg

# Download a Piper voice model (see "Piper Voice Models" section below)
# Place the .onnx and .onnx.json files in a directory of your choice

# Configure Piper in thyme.py (edit these constants at the top):
# USE_PIPER = True
# PIPER_MODEL = "~/path/to/en_US-lessac-medium.onnx"

# Run the script
python thyme.py

# Check available macOS voices (for fallback mode)
say -v ?

# View logs (when running via launchd)
cat /tmp/thyme.log
cat /tmp/thyme.err
```

## Architecture

Single script (`thyme.py`) with these main functions:
- `get_reading_list_items()` - Parses `~/Library/Safari/Bookmarks.plist`
- `extract_article_text()` - Uses trafilatura to fetch and extract article content
- `text_to_mp3()` - Uses Piper TTS (if configured) or falls back to macOS `say` command
- `cleanup_old_episodes()` - Maintains MAX_EPISODES limit

State is tracked in `processed.json` (list of already-processed URLs) stored in the output directory.

### TTS Implementation

The script supports two TTS backends:
1. **Piper TTS** (recommended): Open-source, high-quality neural TTS. Generates WAV files, then converts to M4A using ffmpeg.
2. **macOS `say`** (fallback): Built-in macOS TTS. Used when Piper is disabled or fails to load.

## Configuration

Constants at top of `thyme.py`:

### General Configuration
- `OUTPUT_DIR` - Where to save audio files (default: iCloud Drive/Reading List)
- `MAX_EPISODES` - Maximum number of episodes to keep (default: 50)
- `MIN_TEXT_LENGTH` - Minimum article length in characters (default: 500)

### TTS Configuration
- `USE_PIPER` - Whether to use Piper TTS (default: True)
- `PIPER_MODEL` - Path to Piper .onnx model file (default: None, must be set to use Piper)
- `VOICE` - macOS voice for fallback mode (default: "Samantha")
- `RATE` - Speech rate for macOS say command (default: 190)

## Piper Voice Models

To use Piper TTS, you need to download a voice model from the Piper project:

### Recommended Voices for English

1. **en_US-lessac-medium** (Recommended)
   - High quality, clear pronunciation
   - Good for long-form content
   - Model size: ~63MB

2. **en_US-amy-medium**
   - Warm, friendly voice
   - Alternative to lessac
   - Model size: ~63MB

3. **en_US-ryan-high**
   - Male voice option
   - Highest quality (larger model)
   - Model size: ~94MB

### Downloading Models

1. Visit the Piper samples page: https://rhasspy.github.io/piper-samples/
2. Browse voices and listen to samples
3. Download both files for your chosen voice:
   - `[voice_name].onnx` (the model)
   - `[voice_name].onnx.json` (config file)
4. Save them to a directory (e.g., `~/piper-models/`)
5. Update `PIPER_MODEL` in `thyme.py` to point to the .onnx file

### Example Download Commands

```bash
# Create models directory
mkdir -p ~/piper-models
cd ~/piper-models

# Download en_US-lessac-medium (recommended)
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json

# Then edit thyme.py and set:
# PIPER_MODEL = "~/piper-models/en_US-lessac-medium.onnx"
```

### Fallback to macOS `say`

If you prefer to use the built-in macOS TTS:
1. Set `USE_PIPER = False` in `thyme.py`
2. Or don't set `PIPER_MODEL` (leave it as None)
3. The script will automatically use the macOS `say` command

## macOS Permissions

Requires Full Disk Access to read Safari data (System Settings → Privacy & Security → Full Disk Access).
