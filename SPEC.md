# Thyme

**Convert Safari Reading List articles to audio.**

**Version:** 0.1.0  
**Date:** January 2026  
**Status:** Planning

---

## 1. Overview

A command-line Python script that converts Safari Reading List articles into MP3 files for listening on the go.

### What It Does

1. Reads the 20 most recent Safari Reading List items
2. Extracts article content (like Reader View)
3. Converts each to MP3 using macOS `say`
4. Saves to an iCloud folder with timestamps
5. Prunes anything beyond 20 episodes

### Design Goals

- **Simple:** Single script, minimal dependencies
- **Portable:** Listen via Files app on iPhone (iCloud sync)
- **Hands-off:** Can run automatically when Reading List changes
- **Low-tech:** No server, no hosting, no podcast feed

---

## 2. Flow

```
┌─────────────────────────────────────────┐
│  python thyme.py                        │
│                                         │
│  1. Parse ~/Library/Safari/Bookmarks.plist
│     → Extract Reading List items        │
│     → Take 20 most recent               │
│                                         │
│  2. For each URL not yet processed:     │
│     → Fetch page                        │
│     → Extract article text (trafilatura)│
│     → Prepend title + source            │
│     → say --file-format=mp3 -o file.mp3 │
│                                         │
│  3. Delete oldest files beyond 20       │
└─────────────────────────────────────────┘
```

---

## 3. Technical Details

### 3.1 Input: Safari Reading List

| Property | Value |
|----------|-------|
| Location | `~/Library/Safari/Bookmarks.plist` |
| Format | Binary plist |
| Structure | Reading List items under child with `Title == "com.apple.ReadingList"` |

Each Reading List item contains:

- `URLString` — the article URL
- `ReadingList.DateAdded` — when it was added
- `URIDictionary.title` — the page title

### 3.2 Article Extraction

| Property | Value |
|----------|-------|
| Library | `trafilatura` |
| Output | Plain text with title prepended as spoken intro |

Example intro: "From The Atlantic: The Future of Work. [article body]"

### 3.3 Text-to-Speech

```bash
say -v "Samantha" -r 190 -f input.txt --file-format=mp3 -o output.mp3
```

| Option | Purpose |
|--------|---------|
| `-v "Samantha"` | Voice selection |
| `-r 190` | Speaking rate (words per minute) |
| `-f input.txt` | Read from file (avoids shell escaping issues) |
| `--file-format=mp3` | Direct MP3 output |
| `-o output.mp3` | Output file path |

### 3.4 Output

| Property | Value |
|----------|-------|
| Location | `~/Library/Mobile Documents/com~apple~CloudDocs/Thyme/` |
| Filename format | `YYYYMMDD-HHMMSS-{sanitized-title}.mp3` |
| Timestamp source | Script processing time |

Filename example: `20260115-143022-the-future-of-work.mp3`

### 3.5 State Tracking

| Property | Value |
|----------|-------|
| File | `processed.json` in output folder |
| Format | `{"processed_urls": ["https://...", ...]}` |
| Purpose | Avoid re-processing articles on subsequent runs |

### 3.6 Cleanup

- List all `.mp3` files in output folder
- Sort by filename (timestamp prefix ensures chronological order)
- Keep newest 20
- Delete the rest

---

## 4. Dependencies

### Python Packages

```
trafilatura    # Article extraction
```

### macOS Built-ins

```
say            # Text-to-speech with MP3 output
plistlib       # Standard library, for reading Safari bookmarks
```

### Installation

```bash
pip install trafilatura
```

---

## 5. Configuration

Constants at top of script:

```python
OUTPUT_DIR = "~/Library/Mobile Documents/com~apple~CloudDocs/Thyme/"
MAX_EPISODES = 20
VOICE = "Samantha"  # run `say -v ?` for options
RATE = 190          # words per minute
```

---

## 6. Usage

### Manual Run

```bash
python thyme.py
```

### Automatic Trigger via launchd

Create `~/Library/LaunchAgents/com.needmore.thyme.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" 
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.needmore.thyme</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/USERNAME/Developer/thyme/thyme.py</string>
    </array>
    <key>WatchPaths</key>
    <array>
        <string>/Users/USERNAME/Library/Safari/Bookmarks.plist</string>
    </array>
    <key>StandardOutPath</key>
    <string>/tmp/thyme.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/thyme.err</string>
</dict>
</plist>
```

Install and load:

```bash
# Replace USERNAME in the plist file first, then:
cp com.needmore.thyme.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.needmore.thyme.plist
```

Useful commands:

```bash
# Check if running
launchctl list | grep thyme

# View logs
cat /tmp/thyme.log
cat /tmp/thyme.err

# Manually trigger
launchctl start com.needmore.thyme

# Reload after editing plist
launchctl unload ~/Library/LaunchAgents/com.needmore.thyme.plist
launchctl load ~/Library/LaunchAgents/com.needmore.thyme.plist
```

---

## 7. Scope

### In MVP

- [x] Parse Safari Reading List
- [x] Extract article text via trafilatura
- [x] Convert to MP3 via `say`
- [x] Save to iCloud folder
- [x] Track processed URLs (avoid duplicates)
- [x] Prune to 20 episodes
- [x] Manual run
- [x] Optional launchd auto-trigger

### Not in MVP

- [ ] RSS feed / podcast subscription
- [ ] Public hosting / FTP sync
- [ ] High-quality TTS (Kokoro, etc.)
- [ ] Error retry logic
- [ ] Removing items from Reading List after processing
- [ ] Multiple voices or audio processing
- [ ] Episode metadata (duration, chapters)

---

## 8. Known Issues & Considerations

### macOS Permissions

macOS may require Full Disk Access to read Safari data. Grant permission in:

System Settings → Privacy & Security → Full Disk Access → Add Terminal (or your Python environment)

### Paywalled Articles

trafilatura extracts what it can access. Paywalled sites will likely fail or return partial content. The script should skip these gracefully.

### Long Articles

`say` handles long text fine, but processing time scales linearly. A 10-minute article might take 10+ minutes to generate.

### Special Characters

Some characters may cause issues with `say`. Write text to a temp file and use `-f` flag rather than passing text directly on command line.

### iCloud Sync Latency

Files may take a few minutes to sync to iPhone. Not instant, but good enough for this use case.

---

## 9. Future Enhancements

If the MVP works well, potential next steps:

1. **Better TTS:** Swap `say` for Kokoro TTS (local, higher quality)
2. **RSS Feed:** Generate podcast feed for use with Overcast/Apple Podcasts
3. **FTP Sync:** For podcast feed hosting on personal server
4. **Smarter Extraction:** Fallback to readability-lxml or newspaper3k
5. **Reading List Cleanup:** Remove items after successful processing
6. **Progress Indication:** Show which article is being processed
7. **Configurable Folder:** Support a "Listen Later" subfolder in bookmarks
