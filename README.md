# 🎬 ReelCTL — AI-Powered Media Organizer

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**ReelCTL** is a modern, high-performance command-line application that intelligently organizes messy movie and TV show collections into a clean, consistent, and standard media library.

Unlike traditional organizers that rely strictly on fragile filename parsing regex, ReelCTL combines:
- 📁 **Local Filename Parsing** (powered by `guessit`)
- 🤖 **AI Reasoning** (powered by **Groq Llama 3.3 70B**)
- 🔍 **TMDB Metadata Verification** (The Movie Database API)
- 🗄️ **Local SQLite Caching** (30-day TTL, zero unnecessary API calls)

---

## 🌟 Before & After

### Before (Messy Download Directory)
```
Downloads/
├── avatar_new_final_real.mkv
├── Matrix1999Bluray1080.mp4
├── Money.Heist.S01E01.x264.mkv
├── RARBG.txt
├── sample.mkv
└── movie.mp4
```

### After (`reelctl organize .`)
```
Movies/
├── Avatar (2009)/
│   ├── Avatar (2009) [4K BluRay].mkv
│   └── Avatar (2009).en.srt
└── The Matrix (1999)/
    └── The Matrix (1999) [1080p BluRay].mp4

TV Shows/
└── Money Heist/
    └── Season 01/
        └── Money Heist - S01E01 - Episode 1 [1080p WEB-DL].mkv
```

---

## ✨ Core Features

- 🎬 **Smart Media Detection**: Accurately differentiates between Movies, TV Series, and Anime.
- 🏷️ **Strict Naming Standards**: Standardizes titles, release year, season/episode numbers, quality resolution (`4K`, `1080p`), and media source (`BluRay`, `WEB-DL`).
- 🤖 **AI-Powered Disambiguation**: Uses Groq Llama 3.3 70B to resolve obfuscated or poorly named releases.
- 🎯 **TMDB Verification**: Validates all titles and fetches official names and episode titles from TMDB.
- 💬 **Subtitle Preservation**: Auto-detects subtitle language from content (via `chardet` and language signatures) and keeps `.en.srt`, `.si.srt` synchronized with video files.
- 🗑️ **Junk & Duplicate Detection**: Automatically identifies junk tracker text files (`RARBG.txt`, `YTS.txt`), sample clips, and duplicate lower-quality releases.
- 🛡️ **Safety-First Architecture**:
  - **Dry Run by Default**: Previews all planned filesystem changes without modifying anything until confirmed.
  - **Undo Engine**: Every operation writes a JSON transaction log in `.undo/`, allowing full reversal with `reelctl undo`.
  - **Trash Integration**: File deletions use `send2trash` (moves to OS Recycle Bin/Trash, never permanent delete).
- ⚡ **High Performance**: Recursive scanner handles 10,000+ files in under 30 seconds.

---

## 🏗️ High-Level Architecture

```
                       [ Scan Directory ]
                               │
                               ▼
                    [ Local File Analysis ]
                     (Extension & Categories)
                               │
                               ▼
                    [ Filename Intelligence ]
                       (guessit Parsing)
                               │
                               ▼
                   [ AI Understanding (Groq) ]
                     (Llama 3.3 70B Batching)
                               │
                               ▼
                    [ Verify using TMDB ]
                     (SQLite Cache Check)
                               │
                               ▼
                   [ Build Operation Plan ]
                 (Folder creation, Move, Delete)
                               │
                               ▼
                       [ Interactive Preview ]
                     (Rich Terminal UI Table)
                               │
                               ▼
                    [ Execute Operations ]
                     (send2trash for delete)
                               │
                               ▼
                    [ Save Undo Transaction ]
```

---

## 📦 Installation

### Prerequisites
- **Python 3.12+**
- **Groq API Key** (Get one at [console.groq.com](https://console.groq.com/))
- **TMDB API Key / Access Token** (Get one at [themoviedb.org](https://www.themoviedb.org/settings/api))

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/gayan-tharuka/ReelCTL.git
cd ReelCTL

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install in editable mode
pip install -e .
```

### Configure API Keys

Create a `.env` file in your working directory or copy from `.env.example`:

```env
GROQ_API_KEY="gsk_your_groq_api_key_here"
TMDB_API_KEY="your_tmdb_api_key_here"
TMDB_ACCESS_TOKEN="your_tmdb_bearer_token_here"
```

---

## 🚀 Usage & Commands

### 1. Organize Library (`organize`)

```bash
# Preview operations (Dry Run mode)
reelctl organize /path/to/media

# Execute immediately without confirmation prompt
reelctl organize /path/to/media --yes

# Skip AI pipeline and use local parser only
reelctl organize /path/to/media --no-ai
```

### 2. Scan Directory (`scan`)
Inspect file statistics and categories without taking any action:

```bash
reelctl scan /path/to/media
```

### 3. Verify Titles (`verify`)
Identify and verify media titles against TMDB without organizing:

```bash
reelctl verify /path/to/media
```

### 4. Undo Operations (`undo`)
Reverse the last media organization run:

```bash
reelctl undo
```

### 5. Remove Junk (`clean`)
Identify and remove torrent junk files (`.txt`, `.nfo`, sample videos):

```bash
reelctl clean /path/to/media
```

### 6. Library Health Check (`doctor`)
Diagnose library health, unorganized files, and duplicates:

```bash
reelctl doctor /path/to/media
```

### 7. View Configuration (`config`)
Display active configuration settings and API connection statuses:

```bash
reelctl config
```

### 8. Version Information (`version`)
```bash
reelctl version
```

---

## ⚙️ Configuration (`config.toml`)

ReelCTL reads settings from `~/.config/reelctl/config.toml` (XDG standard) or `./config.toml`:

```toml
# Language for TMDB metadata queries
language = "en"

# Automatically delete junk files
delete_junk = true

# Include episode names in TV filenames
include_episode_title = true

# Output folder names
movie_folder = "Movies"
tv_folder = "TV Shows"

# Default dry run behavior
dry_run = true

# AI Settings
groq_model = "llama-3.3-70b-versatile"
ai_confidence_threshold = 0.80
ai_batch_size = 50

# Cache Settings
cache_ttl_days = 30
```

---

## 🧪 Running Tests

ReelCTL includes a comprehensive suite of unit and integration tests:

```bash
# Run pytest
pytest

# Run with coverage report
pytest --cov=reelctl --cov-report=term-missing
```

---

## 🛠️ Technology Stack

- **Language**: Python 3.12+
- **CLI Framework**: [Typer](https://typer.tiangolo.com/)
- **Terminal UI**: [Rich](https://rich.readthedocs.io/)
- **HTTP Client**: [httpx](https://www.python-httpx.org/)
- **Filename Parser**: [guessit](https://guessit.readthedocs.io/)
- **AI Model**: Groq (`llama-3.3-70b-versatile`)
- **Metadata Source**: [TMDB API v3](https://developer.themoviedb.org/)
- **Safe Delete**: [send2trash](https://github.com/hdfgroup/send2trash)
- **Settings & Validation**: [Pydantic v2](https://docs.pydantic.dev/) & [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- **Logging**: [loguru](https://github.com/Delgan/loguru)

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
