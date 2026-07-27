"""Operation plan builder for ReelCTL.

Takes identified media files and builds a complete plan of filesystem
operations (create folders, move/rename files, delete junk). Nothing
is executed at this stage — the plan is previewed first.
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from reelctl.config import Settings
from reelctl.junk import is_junk_file
from reelctl.models import (
    DuplicateGroup,
    MediaIdentity,
    MediaType,
    Operation,
    OperationPlan,
    OperationType,
    ScannedFile,
)
from reelctl.namer import build_subtitle_filename, build_target_path
from reelctl.subtitles import get_subtitle_language


def build_plan(
    identities: list[MediaIdentity],
    junk_files: list[ScannedFile],
    duplicate_groups: list[DuplicateGroup],
    output_root: Path,
    settings: Settings,
) -> OperationPlan:
    """Build a complete operation plan for organizing media.

    Args:
        identities: List of identified media files.
        junk_files: List of junk files to delete.
        duplicate_groups: List of duplicate groups with recommendations.
        output_root: Root directory for organized output.
        settings: Application settings.

    Returns:
        OperationPlan with all operations to execute.
    """
    operations: list[Operation] = []
    created_folders: set[Path] = set()

    # Track files marked for deletion by duplicate detection
    duplicate_delete_paths: set[Path] = set()
    for group in duplicate_groups:
        for dup in group.recommended_delete:
            duplicate_delete_paths.add(dup.source_file.path)

    # 1. Process identified media files
    for identity in identities:
        if identity.media_type == MediaType.UNKNOWN:
            continue

        # Skip files marked as duplicate deletions
        if identity.source_file.path in duplicate_delete_paths:
            continue

        target_path = build_target_path(identity, output_root, settings)
        target_folder = target_path.parent

        # Create folder if needed
        if target_folder not in created_folders:
            operations.append(
                Operation(
                    operation_type=OperationType.CREATE_FOLDER,
                    source=target_folder,
                    destination=target_folder,
                    reason=f"Create folder for {identity.title}",
                )
            )
            created_folders.add(target_folder)

        # Move/rename the video file
        source_path = identity.source_file.path
        if source_path != target_path:
            operations.append(
                Operation(
                    operation_type=OperationType.MOVE_FILE,
                    source=source_path,
                    destination=target_path,
                    reason=f"Organize: {identity.title}",
                )
            )

        # Handle associated subtitles
        for sub in identity.associated_subtitles:
            lang_code = get_subtitle_language(sub)
            sub_filename = build_subtitle_filename(
                identity, sub.extension, lang_code
            )
            sub_target = target_folder / sub_filename

            if sub.path != sub_target:
                operations.append(
                    Operation(
                        operation_type=OperationType.MOVE_FILE,
                        source=sub.path,
                        destination=sub_target,
                        reason=f"Move subtitle for {identity.title}",
                    )
                )

    # 2. Delete junk files
    if settings.delete_junk:
        for jf in junk_files:
            operations.append(
                Operation(
                    operation_type=OperationType.DELETE_FILE,
                    source=jf.path,
                    reason=f"Junk file: {jf.name}",
                )
            )

    # 3. Delete duplicate lower-quality files
    for group in duplicate_groups:
        for dup in group.recommended_delete:
            operations.append(
                Operation(
                    operation_type=OperationType.DELETE_FILE,
                    source=dup.source_file.path,
                    reason=f"Duplicate (lower quality): {dup.source_file.name}",
                )
            )

    # 4. Deduplicate operations and resolve conflicts
    operations = _deduplicate_operations(operations)
    operations = _resolve_conflicts(operations)

    plan = OperationPlan(
        operations=operations,
        source_directory=output_root,
    )

    logger.info(
        "Plan built: {} total operations ({} creates, {} moves, {} deletes)",
        plan.total_operations,
        len(plan.creates),
        len(plan.moves),
        len(plan.deletes),
    )

    return plan


def _deduplicate_operations(operations: list[Operation]) -> list[Operation]:
    """Remove duplicate operations (e.g., creating the same folder twice)."""
    seen: set[str] = set()
    unique: list[Operation] = []

    for op in operations:
        key = f"{op.operation_type}:{op.source}:{op.destination}"
        if key not in seen:
            seen.add(key)
            unique.append(op)

    return unique


def _resolve_conflicts(operations: list[Operation]) -> list[Operation]:
    """Resolve destination conflicts (multiple files targeting same path).

    If two files would be moved to the same destination, appends a
    numeric suffix to the second one.
    """
    destinations: dict[Path, int] = {}
    resolved: list[Operation] = []

    for op in operations:
        if op.operation_type in (OperationType.MOVE_FILE, OperationType.RENAME_FILE):
            dest = op.destination
            if dest and dest in destinations:
                # Conflict — add numeric suffix
                count = destinations[dest] + 1
                destinations[dest] = count
                stem = dest.stem
                suffix = dest.suffix
                new_dest = dest.parent / f"{stem} ({count}){suffix}"
                op = Operation(
                    operation_type=op.operation_type,
                    source=op.source,
                    destination=new_dest,
                    reason=op.reason + " (conflict resolved)",
                )
            elif dest:
                destinations[dest] = 1

        resolved.append(op)

    return resolved
