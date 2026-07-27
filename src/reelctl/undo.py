"""Undo system for ReelCTL.

Every execution creates a transaction log that records all operations.
The undo command reverses operations in LIFO order.

Logs are stored in .undo/ directory as JSON files.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from loguru import logger

from reelctl.models import OperationType, UndoEntry, UndoLog

# ── Constants ──────────────────────────────────────────────────────────────────

UNDO_DIR = ".undo"


class UndoManager:
    """Manages undo transaction logs."""

    def __init__(self, base_dir: Path | None = None) -> None:
        """Initialize undo manager.

        Args:
            base_dir: Directory to store undo logs. Defaults to .undo/ in cwd.
        """
        self.base_dir = base_dir or Path.cwd() / UNDO_DIR
        self._log = UndoLog()
        self._entries: list[UndoEntry] = []

    def record(self, entry: UndoEntry) -> None:
        """Record an operation for undo.

        Args:
            entry: The undo entry to record.
        """
        self._entries.append(entry)

    def save(self, source_directory: Path | None = None) -> Path:
        """Save the current undo log to disk.

        Args:
            source_directory: The directory that was organized.

        Returns:
            Path to the saved undo log file.
        """
        if not self._entries:
            logger.info("No operations to save in undo log")
            return self.base_dir

        self.base_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_path = self.base_dir / f"{timestamp}.json"

        log = UndoLog(
            entries=self._entries,
            executed_at=datetime.now(),
            source_directory=source_directory,
        )

        log_data = log.model_dump(mode="json")
        log_path.write_text(json.dumps(log_data, indent=2, default=str))

        logger.info("Undo log saved: {} ({} entries)", log_path, len(self._entries))
        return log_path

    @staticmethod
    def get_latest_log(base_dir: Path | None = None) -> Path | None:
        """Find the most recent undo log file.

        Args:
            base_dir: Directory containing undo logs.

        Returns:
            Path to the latest log file, or None if no logs exist.
        """
        undo_dir = base_dir or Path.cwd() / UNDO_DIR
        if not undo_dir.exists():
            return None

        logs = sorted(undo_dir.glob("*.json"), reverse=True)
        return logs[0] if logs else None

    @staticmethod
    def load_log(log_path: Path) -> UndoLog:
        """Load an undo log from disk.

        Args:
            log_path: Path to the JSON undo log file.

        Returns:
            Parsed UndoLog object.
        """
        data = json.loads(log_path.read_text())
        return UndoLog(**data)


def undo_last(base_dir: Path | None = None) -> tuple[int, int]:
    """Undo the most recent organization.

    Reverses operations in LIFO (last-in-first-out) order:
    - Moved/renamed files are moved back
    - Created folders are removed (if empty)
    - Deleted files cannot be restored from trash automatically

    Args:
        base_dir: Directory containing undo logs.

    Returns:
        Tuple of (successful_undos, failed_undos).
    """
    log_path = UndoManager.get_latest_log(base_dir)
    if not log_path:
        logger.warning("No undo log found")
        return 0, 0

    log = UndoManager.load_log(log_path)
    logger.info(
        "Undoing {} operations from {}",
        len(log.entries),
        log.executed_at,
    )

    success = 0
    failed = 0

    # Reverse the operations (LIFO)
    for entry in reversed(log.entries):
        try:
            _undo_entry(entry)
            success += 1
        except Exception as e:
            logger.error("Undo failed for {}: {}", entry.old_path, e)
            failed += 1

    # Remove the undo log after successful undo
    if failed == 0:
        log_path.unlink()
        logger.info("Undo complete — removed log file")
    else:
        logger.warning(
            "Undo partially complete: {} succeeded, {} failed — log preserved",
            success,
            failed,
        )

    return success, failed


def _undo_entry(entry: UndoEntry) -> None:
    """Reverse a single undo entry.

    Args:
        entry: The undo entry to reverse.
    """
    match entry.operation_type:
        case OperationType.MOVE_FILE | OperationType.RENAME_FILE:
            if entry.new_path and entry.new_path.exists():
                # Ensure original directory exists
                entry.old_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(entry.new_path), str(entry.old_path))
                logger.info("Undo: {} → {}", entry.new_path.name, entry.old_path)
            else:
                logger.warning("Cannot undo: file not found at {}", entry.new_path)

        case OperationType.CREATE_FOLDER:
            if entry.old_path.exists() and entry.old_path.is_dir():
                if not any(entry.old_path.iterdir()):
                    entry.old_path.rmdir()
                    logger.info("Undo: removed folder {}", entry.old_path)
                else:
                    logger.warning("Cannot undo: folder not empty {}", entry.old_path)

        case OperationType.COPY_FILE:
            if entry.new_path and entry.new_path.exists():
                entry.new_path.unlink()
                logger.info("Undo: removed copy {}", entry.new_path)

        case OperationType.DELETE_FILE:
            logger.warning(
                "Cannot automatically undo delete for '{}' — check your Trash/Recycle Bin",
                entry.old_path.name,
            )

        case OperationType.REMOVE_FOLDER:
            # Re-create the removed folder
            entry.old_path.mkdir(parents=True, exist_ok=True)
            logger.info("Undo: re-created folder {}", entry.old_path)
