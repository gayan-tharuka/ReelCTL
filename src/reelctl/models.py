"""Core data models for ReelCTL.

All structured data flows through these Pydantic models, ensuring type safety
and validation across the entire pipeline.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────────────


class MediaType(str, Enum):
    """Classification of a media file."""

    MOVIE = "movie"
    TV = "tv"
    UNKNOWN = "unknown"


class FileCategory(str, Enum):
    """Category of a scanned file based on its extension."""

    VIDEO = "video"
    SUBTITLE = "subtitle"
    IMAGE = "image"
    JUNK = "junk"
    UNKNOWN = "unknown"


class OperationType(str, Enum):
    """Type of filesystem operation."""

    CREATE_FOLDER = "CreateFolder"
    RENAME_FILE = "RenameFile"
    MOVE_FILE = "MoveFile"
    DELETE_FILE = "DeleteFile"
    COPY_FILE = "CopyFile"
    REMOVE_FOLDER = "RemoveFolder"


# ── Extension Maps ─────────────────────────────────────────────────────────────

VIDEO_EXTENSIONS: set[str] = {"mkv", "mp4", "avi", "mov", "wmv", "ts", "m2ts"}

SUBTITLE_EXTENSIONS: set[str] = {"srt", "ass", "ssa", "sub", "idx"}

IMAGE_EXTENSIONS: set[str] = {"jpg", "jpeg", "png", "webp"}

JUNK_EXTENSIONS: set[str] = {"txt", "url", "nfo", "exe"}


def categorize_extension(ext: str) -> FileCategory:
    """Determine file category from its extension (without dot)."""
    ext_lower = ext.lower().lstrip(".")
    if ext_lower in VIDEO_EXTENSIONS:
        return FileCategory.VIDEO
    if ext_lower in SUBTITLE_EXTENSIONS:
        return FileCategory.SUBTITLE
    if ext_lower in IMAGE_EXTENSIONS:
        return FileCategory.IMAGE
    if ext_lower in JUNK_EXTENSIONS:
        return FileCategory.JUNK
    return FileCategory.UNKNOWN


# ── Scanner Models ─────────────────────────────────────────────────────────────


class ScannedFile(BaseModel):
    """A single file discovered during scanning."""

    path: Path
    name: str
    extension: str
    size_bytes: int
    modified_at: datetime
    category: FileCategory

    @property
    def size_mb(self) -> float:
        """File size in megabytes."""
        return self.size_bytes / (1024 * 1024)


class ScanResult(BaseModel):
    """Aggregated result from scanning a directory."""

    root_path: Path
    files: list[ScannedFile] = Field(default_factory=list)
    total_size_bytes: int = 0
    scan_duration_seconds: float = 0.0

    @property
    def video_files(self) -> list[ScannedFile]:
        return [f for f in self.files if f.category == FileCategory.VIDEO]

    @property
    def subtitle_files(self) -> list[ScannedFile]:
        return [f for f in self.files if f.category == FileCategory.SUBTITLE]

    @property
    def image_files(self) -> list[ScannedFile]:
        return [f for f in self.files if f.category == FileCategory.IMAGE]

    @property
    def junk_files(self) -> list[ScannedFile]:
        return [f for f in self.files if f.category == FileCategory.JUNK]

    @property
    def unknown_files(self) -> list[ScannedFile]:
        return [f for f in self.files if f.category == FileCategory.UNKNOWN]


# ── Parser Models ──────────────────────────────────────────────────────────────


class ParsedMedia(BaseModel):
    """Result from local filename parsing via guessit."""

    original_filename: str
    title: str | None = None
    year: int | None = None
    season: int | None = None
    episode: int | None = None
    quality: str | None = None
    source: str | None = None
    codec: str | None = None
    release_group: str | None = None
    media_type: MediaType = MediaType.UNKNOWN


# ── AI Models ──────────────────────────────────────────────────────────────────


class AIResult(BaseModel):
    """Result from Groq AI media identification."""

    filename: str
    media_type: MediaType
    title: str
    year: int | None = None
    season: int | None = None
    episode: int | None = None
    quality: str | None = None
    source: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)


# ── TMDB Models ────────────────────────────────────────────────────────────────


class TMDBResult(BaseModel):
    """Verified metadata from TMDB."""

    tmdb_id: int
    official_title: str
    year: int | None = None
    media_type: MediaType
    genres: list[str] = Field(default_factory=list)
    poster_url: str | None = None
    episode_name: str | None = None
    season: int | None = None
    episode: int | None = None
    verified: bool = True


# ── Merged Identity ────────────────────────────────────────────────────────────


class MediaIdentity(BaseModel):
    """Final merged identity for a media file, combining all sources.

    This is the single source of truth used by the namer and planner.
    """

    source_file: ScannedFile
    media_type: MediaType
    title: str
    year: int | None = None
    season: int | None = None
    episode: int | None = None
    episode_name: str | None = None
    quality: str | None = None
    source: str | None = None
    tmdb_id: int | None = None
    confidence: float = 0.0
    verified: bool = False

    # Related files (subtitles, etc.)
    associated_subtitles: list[ScannedFile] = Field(default_factory=list)


# ── Operation Models ───────────────────────────────────────────────────────────


class Operation(BaseModel):
    """A single filesystem operation to be performed."""

    operation_type: OperationType
    source: Path
    destination: Path | None = None
    reason: str = ""

    def describe(self) -> str:
        """Human-readable description of this operation."""
        match self.operation_type:
            case OperationType.CREATE_FOLDER:
                return f"📁 Create: {self.destination}"
            case OperationType.RENAME_FILE:
                return f"✏️  Rename: {self.source.name} → {self.destination.name}"
            case OperationType.MOVE_FILE:
                return f"📦 Move: {self.source.name} → {self.destination}"
            case OperationType.DELETE_FILE:
                return f"🗑️  Delete: {self.source.name}"
            case OperationType.COPY_FILE:
                return f"📋 Copy: {self.source.name} → {self.destination}"
            case OperationType.REMOVE_FOLDER:
                return f"🗑️  Remove folder: {self.source}"
            case _:
                return f"{self.operation_type}: {self.source}"


class OperationPlan(BaseModel):
    """A complete plan of operations to execute."""

    operations: list[Operation] = Field(default_factory=list)
    source_directory: Path | None = None

    @property
    def total_operations(self) -> int:
        return len(self.operations)

    @property
    def creates(self) -> list[Operation]:
        return [o for o in self.operations if o.operation_type == OperationType.CREATE_FOLDER]

    @property
    def moves(self) -> list[Operation]:
        return [o for o in self.operations if o.operation_type == OperationType.MOVE_FILE]

    @property
    def renames(self) -> list[Operation]:
        return [o for o in self.operations if o.operation_type == OperationType.RENAME_FILE]

    @property
    def deletes(self) -> list[Operation]:
        return [
            o
            for o in self.operations
            if o.operation_type in (OperationType.DELETE_FILE, OperationType.REMOVE_FOLDER)
        ]

    @property
    def copies(self) -> list[Operation]:
        return [o for o in self.operations if o.operation_type == OperationType.COPY_FILE]


# ── Undo Models ────────────────────────────────────────────────────────────────


class UndoEntry(BaseModel):
    """A single reversible operation in the undo log."""

    operation_type: OperationType
    old_path: Path
    new_path: Path | None = None
    timestamp: datetime = Field(default_factory=datetime.now)


class UndoLog(BaseModel):
    """Transaction log for a single execution run."""

    entries: list[UndoEntry] = Field(default_factory=list)
    executed_at: datetime = Field(default_factory=datetime.now)
    source_directory: Path | None = None


# ── Duplicate Models ───────────────────────────────────────────────────────────


class DuplicateGroup(BaseModel):
    """A group of files identified as duplicates of the same media."""

    title: str
    year: int | None = None
    tmdb_id: int | None = None
    files: list[MediaIdentity] = Field(default_factory=list)
    recommended_keep: MediaIdentity | None = None
    recommended_delete: list[MediaIdentity] = Field(default_factory=list)
