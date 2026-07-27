# PRD.md

# ReelCTL

### AI-Powered Media Organizer

**Version:** 1.0

**Status:** Draft

**Author:** Gayan Tharuka

---

# 1. Overview

ReelCTL is a modern AI-powered command-line application that intelligently organizes messy movie and TV show collections into a consistent library.

Unlike traditional media organizers that rely solely on filename parsing, ReelCTL combines:

* Local media analysis
* AI reasoning (Groq Llama 3.3 70B)
* TMDB metadata verification

to understand poorly named media files and reorganize them safely.

The application is designed to work completely from the command line while providing a modern, beautiful terminal interface.

Example:

```
Downloads/

avatar_new_final_real.mkv
Matrix1999Bluray1080.mp4
Money.Heist.S01E01.x264.mkv
movie.mp4
sample.mkv
RARBG.txt
```

↓

```
Movies/

Avatar (2009)/
    Avatar (2009) [4K BluRay].mkv

The Matrix (1999)/
    The Matrix (1999) [1080p BluRay].mp4

TV Shows/

Money Heist/
    Season 01/
        Money Heist - S01E01 [1080p WEB-DL].mkv
```

---

# 2. Goals

The system should:

* Organize entire media libraries
* Rename files consistently
* Detect Movies vs TV Shows
* Identify Seasons and Episodes
* Detect quality information
* Detect media source
* Preserve subtitles
* Remove junk files
* Create missing folders
* Merge duplicate folders
* Verify every title using TMDB
* Never perform unsafe operations without confirmation

---

# 3. Non Goals

Version 1 will NOT include:

* GUI
* Plex integration
* Jellyfin integration
* Torrent downloading
* Video transcoding
* Metadata editing
* File conversion
* Streaming server

---

# 4. Target Users

* Movie collectors
* TV show collectors
* Plex users
* Jellyfin users
* NAS users
* Home server enthusiasts
* Developers

---

# 5. Tech Stack

Language

Python 3.13+

CLI

Typer

Terminal UI

Rich

HTTP

httpx

Media Parser

guessit

AI

Groq API

Model

llama-3.3-70b-versatile

Movie Metadata

TMDB API

Filesystem

pathlib

File Operations

shutil

Safe Delete

send2trash

Config

TOML

Cache

SQLite

Logging

loguru

---

# 6. High Level Architecture

```
                Scan Folder
                     │
                     ▼
            Local File Analysis
                     │
                     ▼
          Filename Intelligence
                     │
                     ▼
          AI Understanding (Groq)
                     │
                     ▼
          Verify using TMDB
                     │
                     ▼
          Build Operation Plan
                     │
                     ▼
          Preview
                     │
                     ▼
           Execute Operations
                     │
                     ▼
              Save Undo Log
```

---

# 7. Folder Scanner

The scanner recursively scans the current directory.

Collect:

Files

Folders

Extensions

Sizes

Modification dates

Video files

Subtitle files

Images

Text files

Archives

Unknown files

Supported extensions:

Video

```
mkv
mp4
avi
mov
wmv
ts
m2ts
```

Subtitle

```
srt
ass
ssa
sub
idx
```

Images

```
jpg
jpeg
png
webp
```

Junk

```
txt
url
nfo
exe
```

---

# 8. AI Pipeline

The AI never performs filesystem operations.

It only understands media.

Input:

```
Avatar.2009.2160p.BluRay.x265.mkv
```

Output:

```json
{
    "type":"movie",
    "title":"Avatar",
    "year":2009,
    "quality":"4K",
    "source":"BluRay",
    "confidence":0.99
}
```

Another example

```
Money.Heist.S02E04.1080p.WEB-DL.mkv
```

↓

```json
{
    "type":"tv",
    "title":"Money Heist",
    "season":2,
    "episode":4,
    "quality":"1080p",
    "source":"WEB-DL"
}
```

---

# 9. TMDB Verification

Every AI result is verified.

Search movie

Search TV

Validate year

Validate title

Retrieve:

Official title

Year

Episode names

Poster

TMDB ID

Genres

Only verified metadata is used.

---

# 10. Naming Convention

Movies

```
Movie Title (Year) [Quality Source].ext
```

Examples

```
The Matrix (1999) [1080p BluRay].mp4

Dune: Part Two (2024) [4K WEB-DL].mkv

Avatar (2009) [4K BluRay].mkv

Interstellar (2014) [1080p BluRay].mkv
```

---

TV

```
Series/
    Season XX/
        Series - S01E01 [1080p WEB-DL].mkv
```

or

```
Series - S01E01 - Episode Name [1080p WEB-DL].mkv
```

---

Anime

```
One Piece/
    Season 21/
        One Piece - S21E1098 [1080p WEB].mkv
```

---

# 11. Quality Normalization

Normalize releases.

Input

```
2160p
```

↓

```
4K
```

Input

```
BRRip
```

↓

```
BluRay
```

Table

| Found  | Output |
| ------ | ------ |
| 2160p  | 4K     |
| UHD    | 4K     |
| WEBRip | WEB    |
| WEB-DL | WEB-DL |
| BluRay | BluRay |
| BRRip  | BluRay |
| BDRip  | BluRay |
| HDRip  | HDRip  |
| DVDRip | DVD    |

---

# 12. Folder Structure

Movies

```
Movies/

Avatar (2009)/
    Avatar (2009) [4K BluRay].mkv
    Avatar (2009).en.srt
```

TV

```
TV Shows/

Breaking Bad/

    Season 01/

        Breaking Bad - S01E01 [1080p BluRay].mkv
```

---

# 13. Subtitle Handling

Detect

```
.en.srt
.si.srt
.ass
.sub
```

Rename

Move with movie

Keep language code

Example

```
Avatar (2009).en.srt
```

---

# 14. Junk Detection

Detect

```
RARBG.txt

YTS.MX.txt

Torrent Downloaded From...

sample.mkv

desktop.ini

Thumbs.db

.nfo

.url
```

User chooses

Delete

Move

Ignore

---

# 15. Duplicate Detection

Detect duplicate movies

Compare

Resolution

Source

Codec

Bitrate

File size

Suggest

```
Keep

Avatar [4K BluRay]

Delete

Avatar [720p WEBRip]
```

---

# 16. Operations Engine

Every action becomes an operation.

```
CreateFolder

RenameFile

MoveFile

DeleteFile

CopyFile

RemoveFolder
```

Nothing executes immediately.

---

# 17. Dry Run

Default mode.

```
reelctl organize .
```

Shows

```
147 operations ready

Nothing has been changed.
```

User confirms.

```
Proceed?

[Y/N]
```

---

# 18. Undo

Every execution creates a transaction log.

```
.undo/

2026-07-27.json
```

Contains

```
Old path

New path

Deleted files

Created folders
```

Undo

```
reelctl undo
```

---

# 19. CLI Commands

```
reelctl organize .
```

```
reelctl organize Downloads --yes
```

```
reelctl scan .
```

```
reelctl verify .
```

```
reelctl undo
```

```
reelctl clean .
```

```
reelctl doctor .
```

```
reelctl config
```

```
reelctl version
```

---

# 20. Configuration

config.toml

```
tmdb_api=""

groq_api=""

language="en"

delete_junk=true

include_episode_title=true

movie_folder="Movies"

tv_folder="TV Shows"

dry_run=true
```

---

# 21. Caching

Cache every TMDB request.

SQLite

```
Movie ID

TV ID

Episode IDs

Search Results
```

Avoid duplicate API calls.

---

# 22. Logging

Every run creates

```
logs/

2026-07-27.log
```

Contains

Every rename

Every move

API calls

Warnings

Errors

Execution time

---

# 23. Performance Goals

* Scan 10,000 files in under 30 seconds (excluding API calls).
* Support libraries larger than 100 TB.
* Batch AI requests to minimise API usage.
* Cache TMDB responses locally.
* Process filesystem operations concurrently where safe.

---

# 24. Error Handling

If TMDB unavailable

Use cache

If cache unavailable

Ask AI

If AI confidence < 80%

Skip

If destination exists

Ask

Replace

Rename

Skip

---

# 25. Security

Never permanently delete by default.

Use Trash/Recycle Bin.

Never overwrite files silently.

Always support preview mode.

Every action must be reversible through Undo.

---

# 26. Future Roadmap

## v1.1

* Watch mode (monitor download folders)
* Batch parallel processing
* Improved duplicate detection

## v1.2

* Plex integration
* Jellyfin integration
* Kodi metadata generation

## v2.0

* Multi-provider AI support (Groq, OpenAI, Ollama)
* IMDb and TVDB providers
* Plugin system
* User-defined naming templates
* Automatic poster and fanart downloads
* Automatic collection detection (e.g. Marvel, Harry Potter, The Lord of the Rings)
* Smart quality upgrades (replace lower-quality copies automatically)

---

# 27. Success Metrics

* ≥98% correct movie identification.
* ≥97% correct TV episode identification.
* ≥95% successful automatic organisation without user intervention.
* Zero data loss caused by the application.
* Less than 5% of files requiring manual review.
* Average organisation time under 5 minutes for a 1,000-file library.

---

# 28. Design Principles

* **AI for understanding, deterministic code for actions.**
* **Preview first, execute second.**
* **Every operation must be undoable.**
* **Never guess when confidence is low.**
* **Optimise API usage through batching and caching.**
* **Produce a clean, predictable media library every time.**
