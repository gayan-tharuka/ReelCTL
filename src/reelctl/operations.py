"""Filesystem operation executor for ReelCTL.

Executes operations from a plan sequentially. Every operation is logged
and recorded in the undo log for reversibility.

Uses send2trash for deletions (moves to OS Trash instead of permanent delete).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from loguru import logger
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID
from send2trash import send2trash

from reelctl.models import Operation, OperationPlan, OperationType, UndoEntry
from reelctl.undo import UndoManager


def execute_plan(
    plan: OperationPlan,
    undo_manager: UndoManager,
    progress: Progress | None = None,
) -> tuple[int, int]:
    """Execute all operations in the plan.

    Args:
        plan: The operation plan to execute.
        undo_manager: Undo manager for recording reversible operations.
        progress: Optional Rich progress bar.

    Returns:
        Tuple of (successful_count, failed_count).
    """
    success = 0
    failed = 0
    task_id: TaskID | None = None

    if progress:
        task_id = progress.add_task(
            "Executing operations...",
            total=plan.total_operations,
        )

    for op in plan.operations:
        try:
            _execute_operation(op, undo_manager)
            success += 1
        except Exception as e:
            logger.error("Operation failed: {} — {}", op.describe(), e)
            failed += 1

        if progress and task_id is not None:
            progress.advance(task_id)

    logger.info("Execution complete: {} succeeded, {} failed", success, failed)
    return success, failed


def _execute_operation(op: Operation, undo_manager: UndoManager) -> None:
    """Execute a single filesystem operation.

    Args:
        op: The operation to execute.
        undo_manager: Undo manager for recording the operation.

    Raises:
        OSError: If the filesystem operation fails.
    """
    logger.info("{}", op.describe())

    match op.operation_type:
        case OperationType.CREATE_FOLDER:
            _create_folder(op, undo_manager)

        case OperationType.MOVE_FILE:
            _move_file(op, undo_manager)

        case OperationType.RENAME_FILE:
            _rename_file(op, undo_manager)

        case OperationType.DELETE_FILE:
            _delete_file(op, undo_manager)

        case OperationType.COPY_FILE:
            _copy_file(op, undo_manager)

        case OperationType.REMOVE_FOLDER:
            _remove_folder(op, undo_manager)


def _create_folder(op: Operation, undo_manager: UndoManager) -> None:
    """Create a directory (and parents if needed)."""
    target = op.destination or op.source
    if not target.exists():
        target.mkdir(parents=True, exist_ok=True)
        undo_manager.record(
            UndoEntry(
                operation_type=OperationType.CREATE_FOLDER,
                old_path=target,
            )
        )


def _move_file(op: Operation, undo_manager: UndoManager) -> None:
    """Move a file to a new location."""
    if not op.destination:
        raise ValueError("Move operation requires a destination")

    # Ensure destination directory exists
    op.destination.parent.mkdir(parents=True, exist_ok=True)

    source = op.source
    dest = op.destination

    # Handle destination already exists
    if dest.exists():
        logger.warning("Destination already exists, adding suffix: {}", dest)
        stem = dest.stem
        suffix = dest.suffix
        counter = 1
        while dest.exists():
            dest = dest.parent / f"{stem} ({counter}){suffix}"
            counter += 1

    shutil.move(str(source), str(dest))

    undo_manager.record(
        UndoEntry(
            operation_type=OperationType.MOVE_FILE,
            old_path=source,
            new_path=dest,
        )
    )


def _rename_file(op: Operation, undo_manager: UndoManager) -> None:
    """Rename a file in place."""
    if not op.destination:
        raise ValueError("Rename operation requires a destination")

    op.source.rename(op.destination)

    undo_manager.record(
        UndoEntry(
            operation_type=OperationType.RENAME_FILE,
            old_path=op.source,
            new_path=op.destination,
        )
    )


def _delete_file(op: Operation, undo_manager: UndoManager) -> None:
    """Delete a file by sending to trash (never permanent delete)."""
    if op.source.exists():
        send2trash(str(op.source))

        undo_manager.record(
            UndoEntry(
                operation_type=OperationType.DELETE_FILE,
                old_path=op.source,
            )
        )


def _copy_file(op: Operation, undo_manager: UndoManager) -> None:
    """Copy a file to a new location."""
    if not op.destination:
        raise ValueError("Copy operation requires a destination")

    op.destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(op.source), str(op.destination))

    undo_manager.record(
        UndoEntry(
            operation_type=OperationType.COPY_FILE,
            old_path=op.source,
            new_path=op.destination,
        )
    )


def _remove_folder(op: Operation, undo_manager: UndoManager) -> None:
    """Remove an empty folder."""
    if op.source.exists() and op.source.is_dir():
        # Only remove if empty
        if not any(op.source.iterdir()):
            op.source.rmdir()
            undo_manager.record(
                UndoEntry(
                    operation_type=OperationType.REMOVE_FOLDER,
                    old_path=op.source,
                )
            )
        else:
            logger.warning("Folder not empty, skipping removal: {}", op.source)
