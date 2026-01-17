# Thyme 🌿

Convert Safari Reading List articles to audio files.

## Quick Start

```bash
# Install dependencies
pip install trafilatura lxml_html_clean

# Run manually
python thyme.py
```

Audio files (.m4a) appear in `~/Library/Mobile Documents/com~apple~CloudDocs/Thyme/` (syncs to Files app on iPhone).

## Auto-Run on Reading List Changes

```bash
# Edit the plist: replace USERNAME and path/to with your values
sed -i '' "s|USERNAME|$(whoami)|g; s|path/to|$(pwd)|" com.needmore.thyme.plist

# Install
cp com.needmore.thyme.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.needmore.thyme.plist
```

## Configuration

Edit the constants at the top of `thyme.py`:

```python
OUTPUT_DIR = "~/Library/Mobile Documents/com~apple~CloudDocs/Thyme/"
MAX_EPISODES = 20
VOICE = "Samantha"  # run `say -v ?` for options
RATE = 190          # words per minute
```

## Permissions

macOS requires Full Disk Access to read Safari data:

System Settings → Privacy & Security → Full Disk Access → Add Terminal

## Logs

```bash
cat /tmp/thyme.log
cat /tmp/thyme.err
```

## See Also

- [SPEC.md](SPEC.md) — Full specification
