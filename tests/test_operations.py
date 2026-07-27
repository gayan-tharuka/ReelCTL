"""Tests for operations and undo."""

import json
from pathlib import Path

from reelctl.models import Operation, OperationPlan, OperationType, UndoEntry
from reelctl.undo import UndoManager


class TestOperationPlan:
    def test_plan_counts(self):
        plan = OperationPlan(
            operations=[
                Operation(operation_type=OperationType.CREATE_FOLDER, source=Path("/a")),
                Operation(operation_type=OperationType.MOVE_FILE, source=Path("/b"), destination=Path("/c")),
                Operation(operation_type=OperationType.DELETE_FILE, source=Path("/d")),
            ]
        )
        assert plan.total_operations == 3
        assert len(plan.creates) == 1
        assert len(plan.moves) == 1
        assert len(plan.deletes) == 1

    def test_operation_describe(self):
        op = Operation(
            operation_type=OperationType.MOVE_FILE,
            source=Path("/src/movie.mkv"),
            destination=Path("/dst/Movie (2024)/movie.mkv"),
        )
        desc = op.describe()
        assert "Move" in desc


class TestUndoManager:
    def test_save_and_load(self, tmp_path: Path):
        manager = UndoManager(base_dir=tmp_path / ".undo")

        manager.record(
            UndoEntry(
                operation_type=OperationType.MOVE_FILE,
                old_path=Path("/old/movie.mkv"),
                new_path=Path("/new/Movie (2024)/movie.mkv"),
            )
        )

        log_path = manager.save(source_directory=tmp_path)
        assert (tmp_path / ".undo").exists()

        # Find and load the log
        latest = UndoManager.get_latest_log(tmp_path / ".undo")
        assert latest is not None

        loaded = UndoManager.load_log(latest)
        assert len(loaded.entries) == 1
        assert loaded.entries[0].operation_type == OperationType.MOVE_FILE

    def test_empty_save(self, tmp_path: Path):
        manager = UndoManager(base_dir=tmp_path / ".undo")
        manager.save()
        # No entries = no log file created (just returns the dir)

    def test_no_log_returns_none(self, tmp_path: Path):
        result = UndoManager.get_latest_log(tmp_path / ".undo")
        assert result is None
