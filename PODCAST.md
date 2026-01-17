# Podcast Hosting Setup

This document describes how to turn Thyme into a self-hosted podcast that you can subscribe to in Apple Podcasts.

## How It Works

1. Thyme generates audio files from your Safari Reading List (as it does now)
2. An RSS feed (`feed.xml`) is generated listing all episodes
3. Files are synced to your web server via rsync
4. You subscribe to the RSS feed URL in Apple Podcasts

## Requirements

- A web server that can serve static files over HTTPS
- SSH access for rsync
- A domain or subdomain (e.g., `https://podcast.yourdomain.com/`)

## Configuration

Add these settings to the top of `thyme.py`:

```python
# Podcast hosting (set to None to disable)
PODCAST_BASE_URL = "https://podcast.yourdomain.com/"  # Must end with /
RSYNC_DEST = "user@yourserver:/var/www/podcast/"      # Must end with /
PODCAST_TITLE = "My Reading List"
PODCAST_DESCRIPTION = "Articles from my Safari Reading List, converted to audio"
PODCAST_AUTHOR = "Your Name"
PODCAST_EMAIL = "you@example.com"
PODCAST_COVER = "cover.jpg"  # Place a 3000x3000 jpg in OUTPUT_DIR
```

## Server Setup

### Directory Structure

On your server, you'll have:
```
/var/www/podcast/
├── feed.xml           # RSS feed (generated)
├── cover.jpg          # Podcast artwork (you provide)
├── processed.json     # State file
└── *.m4a              # Audio episodes
```

### Nginx Configuration (example)

```nginx
server {
    listen 443 ssl;
    server_name podcast.yourdomain.com;

    root /var/www/podcast;

    # Serve files with correct MIME types
    types {
        application/rss+xml xml;
        audio/x-m4a m4a;
    }

    location / {
        autoindex off;
    }
}
```

### Apache Configuration (example)

```apache
<VirtualHost *:443>
    ServerName podcast.yourdomain.com
    DocumentRoot /var/www/podcast

    AddType application/rss+xml .xml
    AddType audio/x-m4a .m4a
</VirtualHost>
```

## RSS Feed Format

The generated `feed.xml` will look like:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>My Reading List</title>
    <link>https://podcast.yourdomain.com/</link>
    <description>Articles from my Safari Reading List</description>
    <language>en-us</language>
    <itunes:author>Your Name</itunes:author>
    <itunes:image href="https://podcast.yourdomain.com/cover.jpg"/>
    <itunes:category text="News"/>

    <item>
      <title>Article Title Here</title>
      <enclosure url="https://podcast.yourdomain.com/20250118-article-title.m4a"
                 type="audio/x-m4a"
                 length="1234567"/>
      <guid>https://podcast.yourdomain.com/20250118-article-title.m4a</guid>
      <pubDate>Sat, 18 Jan 2025 12:00:00 +0000</pubDate>
      <itunes:duration>5:32</itunes:duration>
    </item>

    <!-- More items... -->
  </channel>
</rss>
```

## Subscribing in Apple Podcasts

1. Open Apple Podcasts on your iPhone/Mac
2. Go to Library → Shows
3. On Mac: File → Add a Show by URL
   On iPhone: Tap the search icon, scroll down to "Add by URL"
4. Enter: `https://podcast.yourdomain.com/feed.xml`

## Implementation Checklist

- [ ] Set up web server with HTTPS
- [ ] Configure domain/subdomain DNS
- [ ] Set up SSH key for passwordless rsync
- [ ] Create podcast cover image (3000x3000 recommended, JPEG)
- [ ] Update configuration in `thyme.py`
- [ ] Test rsync manually: `rsync -avz ~/Library/Mobile\ Documents/com~apple~CloudDocs/Reading\ List/ user@server:/var/www/podcast/`
- [ ] Run thyme.py to generate feed
- [ ] Subscribe in Apple Podcasts

## Cover Image

Apple Podcasts requires artwork:
- Minimum: 1400x1400 pixels
- Recommended: 3000x3000 pixels
- Format: JPEG or PNG
- RGB color space

Place your cover image in the output directory before running the script.

## Privacy Notes

Since this is hosted on a public URL without authentication:
- Anyone with the URL can access your podcast
- The URL is not easily discoverable (no search engine indexing by default)
- For more privacy, use a long random path: `https://yourdomain.com/podcast-a8f3b2c1d4/`

If you want authentication, consider:
- HTTP Basic Auth (supported by most podcast apps)
- Unique token in the URL path
